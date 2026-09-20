#!/usr/bin/env python3
"""Measure RQ3 online costs for the six logits-bias watermark methods.

The server exposes method-owned logits-processor time and the complete detector
invocation time. This client preserves every measured invocation, normalizes by
the authoritative completion-token count, and computes run-level uncertainty.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


METHODS = ("wllm", "ewd", "sweet", "stone", "codeip", "waterfall")
EEI_BOUNDS = {
    "wllm": (0.11, 4.48),
    "ewd": (0.16, 4.29),
    "sweet": (0.13, 3.44),
    "stone": (0.19, 4.24),
    "codeip": (0.10, 4.60),
    "waterfall": (0.23, 11.00),
}
EEI_MIDPOINTS = {
    method: (lower + upper) / 2.0
    for method, (lower, upper) in EEI_BOUNDS.items()
}
METHOD_PARAMS: dict[str, dict[str, Any]] = {
    "wllm": {
        "gamma": 0.5,
        "delta": EEI_MIDPOINTS["wllm"],
        "z_threshold": 4.0,
        "ignore_repeated_bigrams": False,
        "detector_scope": "continuation",
    },
    "ewd": {
        "gamma": 0.5,
        "delta": EEI_MIDPOINTS["ewd"],
        "hash_key": 15485863,
        "z_threshold": 4.0,
        "prefix_length": 1,
        "detector_scope": "continuation",
    },
    "sweet": {
        "gamma": 0.5,
        "delta": EEI_MIDPOINTS["sweet"],
        "entropy_threshold": 0.5,
        "z_threshold": 4.0,
        "ignore_repeated_bigrams": False,
        "detector_scope": "continuation",
    },
    "stone": {
        "gamma": 0.5,
        "delta": EEI_MIDPOINTS["stone"],
        "hash_key": 15485863,
        "z_threshold": 4.0,
        "prefix_length": 1,
        "language": "java",
        "watermark_on_pl": "False",
        "skipping_rule": "all_pl",
        "detector_scope": "continuation",
    },
    # Table X uses the released CodeIP random-message branch without the
    # optional PDA/type predictor.
    "codeip": {
        "mode": "random",
        "language": "java",
        "delta": EEI_MIDPOINTS["codeip"],
        "gamma": 3.0,
        "message_code_len": 20,
        "encode_ratio": 10.0,
        "top_k": 1000,
        "message": [2024],
    },
    "waterfall": {
        "id_mu": 42,
        "k_p": 1,
        "kappa": EEI_MIDPOINTS["waterfall"],
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_workloads(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    workloads = []
    for item in payload["workloads"]:
        context_path = root / item["context_file"]
        context = context_path.read_text(encoding="utf-8")
        prompt = (
            f"You are implementing {item['target_file']} in the existing repository "
            f"{item['repository']}.\n\n"
            f"===== {item['context_file']} =====\n{context}\n\n"
            f"===== TASK =====\n{item['instruction']}"
        )
        workloads.append(
            {
                "name": item["name"],
                "repository": item["repository"],
                "target_file": item["target_file"],
                "context_file": item["context_file"],
                "context_sha256": sha256_bytes(context.encode("utf-8")),
                "rendered_prompt": prompt,
                "rendered_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            }
        )
    if not workloads:
        raise ValueError(f"workload manifest is empty: {path}")
    return workloads


def json_request(url: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"cannot reach {url}: {error}") from error


def detection_errors(value: Any, path: str = "wm_detection") -> list[str]:
    errors = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key == "error":
                errors.append(f"{nested_path}: {nested}")
            else:
                errors.extend(detection_errors(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(detection_errors(nested, f"{path}[{index}]"))
    return errors


def mappings_with_field(value: Any, field: str) -> list[dict[str, Any]]:
    matches = []
    if isinstance(value, dict):
        if field in value:
            matches.append(value)
        for nested in value.values():
            matches.extend(mappings_with_field(nested, field))
    elif isinstance(value, list):
        for nested in value:
            matches.extend(mappings_with_field(nested, field))
    return matches


def validate_detection(method: str, detection: Any, completion_tokens: int) -> None:
    """Reject successful-looking responses that did no detector work."""
    errors = detection_errors(detection or {})
    if errors:
        raise RuntimeError(f"{method} detector failed: {'; '.join(errors)}")
    if method in ("wllm", "ewd", "sweet", "stone"):
        input_rows = mappings_with_field(detection, "detector_input_tokens")
        if len(input_rows) != 1:
            raise RuntimeError(
                f"{method} detector must return exactly one input-token record"
            )
        detector_row = input_rows[0]
        if detector_row.get("detector_scope") != "continuation":
            raise RuntimeError(f"{method} detector did not use continuation-only scope")
        if int(detector_row["detector_input_tokens"]) != completion_tokens:
            raise RuntimeError(
                f"{method} detector input/completion mismatch: "
                f"{detector_row['detector_input_tokens']} != {completion_tokens}"
            )

    if method in ("wllm", "ewd", "stone"):
        score_rows = mappings_with_field(detection, "num_tokens_scored")
        if len(score_rows) != 1 or int(score_rows[0]["num_tokens_scored"]) != completion_tokens - 1:
            raise RuntimeError(
                f"{method} detector must score completion_tokens - 1 positions"
            )
        return

    if method == "codeip":
        available_rows = mappings_with_field(detection, "available_message_num")
        if len(available_rows) != 1 or int(available_rows[0]["available_message_num"]) <= 0:
            raise RuntimeError("CodeIP detector decoded no complete message block")
        return

    if method == "waterfall":
        score_rows = mappings_with_field(detection, "q_score")
        if len(score_rows) != 1 or not math.isfinite(float(score_rows[0]["q_score"])):
            raise RuntimeError("Waterfall detector returned no finite q_score")
        return

    if method != "sweet":
        return

    score_rows = mappings_with_field(detection, "num_tokens_scored")
    if len(score_rows) != 1:
        raise RuntimeError(
            "SWEET detector must return exactly one num_tokens_scored record, "
            f"got {len(score_rows)}"
        )
    score = score_rows[0]
    scored = int(score["num_tokens_scored"])
    if scored <= 0:
        raise RuntimeError("SWEET detector scored zero tokens; timing would be a no-op")
    entropy = score.get("entropy")
    if not isinstance(entropy, dict):
        raise RuntimeError("SWEET detector omitted entropy provenance")
    if entropy.get("source") != "detector_model_forward":
        raise RuntimeError(
            "SWEET detector did not use an independent detector model forward"
        )
    if int(entropy.get("continuation_tokens", -1)) != completion_tokens - 1:
        raise RuntimeError(
            "SWEET detector entropy/token mismatch: "
            f"entropy={entropy.get('continuation_tokens')}, expected={completion_tokens - 1}"
        )
    if int(entropy.get("qualified_tokens", -1)) != scored:
        raise RuntimeError(
            "SWEET detector qualified/scored-token mismatch: "
            f"qualified={entropy.get('qualified_tokens')}, scored={scored}"
        )


def run_once(
    endpoint: str,
    method: str,
    workload: dict[str, Any],
    *,
    max_tokens: int,
    seed: int,
    timeout: float,
    phase: str,
    repeat: int,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "messages": [{"role": "user", "content": workload["rendered_prompt"]}],
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": max_tokens,
        "stream": False,
        "rng_seed": seed,
        "internal_processor_names": [],
        "external_processor_names": [method],
        "external_processor_params": {method: METHOD_PARAMS[method]},
        "watermark_detect": True,
    }
    client_start = time.perf_counter()
    response = json_request(f"{endpoint}/v1/chat/completions", payload, timeout)
    client_elapsed = time.perf_counter() - client_start
    usage = response["usage"]
    choice = response["choices"][0]
    generation_metrics = choice.get("generation_metrics") or {}
    processor_metrics = choice.get("processor_metrics") or {}
    completion_tokens = int(usage["completion_tokens"])
    if completion_tokens <= 0:
        raise RuntimeError(f"{method} returned no completion tokens")
    extraction_seconds = generation_metrics.get("watermark_detection_elapsed_s")
    if extraction_seconds is None:
        raise RuntimeError(f"{method} response omitted detector timing")
    validate_detection(method, choice.get("wm_detection") or {}, completion_tokens)
    components = {
        name: metrics
        for name, metrics in processor_metrics.items()
        if isinstance(metrics, dict) and "lp_total_time_s" in metrics
    }
    if not components:
        raise RuntimeError(f"{method} response omitted logits-processor timing")
    embedding_seconds = sum(float(row["lp_total_time_s"]) for row in components.values())
    generated_text = str(choice.get("message", {}).get("content", ""))
    baseline_tokens = int(baseline["completion_tokens"])
    if baseline_tokens != completion_tokens:
        raise RuntimeError(
            f"{method} paired baseline token mismatch: {baseline_tokens} != {completion_tokens}"
        )
    generation_seconds = float(generation_metrics.get("generation_elapsed_s", 0.0))
    paired_delta_seconds = generation_seconds - float(baseline["generation_seconds"])
    return {
        "phase": phase,
        "method": method,
        "workload": workload["name"],
        "repeat": repeat,
        "rng_seed": seed,
        "prompt_sha256": workload["rendered_prompt_sha256"],
        "prompt_tokens": int(usage["prompt_tokens"]),
        "completion_tokens": completion_tokens,
        "total_tokens": int(usage["total_tokens"]),
        "finish_reason": choice.get("finish_reason"),
        "embedding_seconds": embedding_seconds,
        "extraction_seconds": float(extraction_seconds),
        "generation_seconds": generation_seconds,
        "baseline_generation_seconds": float(baseline["generation_seconds"]),
        "paired_generation_delta_seconds": paired_delta_seconds,
        "baseline_generated_text_sha256": baseline["generated_text_sha256"],
        "client_seconds": client_elapsed,
        "embedding_ms_per_1k_tokens": embedding_seconds * 1_000_000.0 / completion_tokens,
        "extraction_ms_per_1k_tokens": float(extraction_seconds) * 1_000_000.0 / completion_tokens,
        "baseline_generation_ms_per_1k_tokens": float(baseline["generation_seconds"]) * 1_000_000.0 / completion_tokens,
        "watermarked_generation_ms_per_1k_tokens": generation_seconds * 1_000_000.0 / completion_tokens,
        "paired_generation_delta_ms_per_1k_tokens": paired_delta_seconds * 1_000_000.0 / completion_tokens,
        "processor_calls": sum(int(row.get("lp_calls", 0)) for row in components.values()),
        "processor_components": components,
        "wm_detection": choice.get("wm_detection"),
        "generated_text": generated_text,
        "generated_text_sha256": sha256_bytes(generated_text.encode("utf-8")),
    }


def run_baseline_once(
    endpoint: str,
    workload: dict[str, Any],
    *,
    max_tokens: int,
    seed: int,
    timeout: float,
    phase: str,
    repeat: int,
) -> dict[str, Any]:
    """Run the synchronized WM-OFF member of a paired generation trial."""
    payload = {
        "messages": [{"role": "user", "content": workload["rendered_prompt"]}],
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": max_tokens,
        "stream": False,
        "rng_seed": seed,
        "internal_processor_names": [],
        "external_processor_names": [],
        "watermark_detect": False,
    }
    client_start = time.perf_counter()
    response = json_request(f"{endpoint}/v1/chat/completions", payload, timeout)
    client_elapsed = time.perf_counter() - client_start
    usage = response["usage"]
    choice = response["choices"][0]
    generation_metrics = choice.get("generation_metrics") or {}
    completion_tokens = int(usage["completion_tokens"])
    if completion_tokens <= 0:
        raise RuntimeError("WM-OFF baseline returned no completion tokens")
    generation_seconds = generation_metrics.get("generation_elapsed_s")
    if generation_seconds is None or float(generation_seconds) <= 0.0:
        raise RuntimeError("WM-OFF baseline omitted synchronized generation timing")
    generated_text = str(choice.get("message", {}).get("content", ""))
    return {
        "phase": phase,
        "method": "wm_off",
        "workload": workload["name"],
        "repeat": repeat,
        "rng_seed": seed,
        "prompt_sha256": workload["rendered_prompt_sha256"],
        "prompt_tokens": int(usage["prompt_tokens"]),
        "completion_tokens": completion_tokens,
        "total_tokens": int(usage["total_tokens"]),
        "finish_reason": choice.get("finish_reason"),
        "generation_seconds": float(generation_seconds),
        "client_seconds": client_elapsed,
        "generation_ms_per_1k_tokens": float(generation_seconds) * 1_000_000.0 / completion_tokens,
        "generated_text": generated_text,
        "generated_text_sha256": sha256_bytes(generated_text.encode("utf-8")),
    }


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def ratio(rows: list[dict[str, Any]], field: str) -> float:
    seconds = sum(float(row[field]) for row in rows)
    tokens = sum(int(row["completion_tokens"]) for row in rows)
    return seconds * 1_000_000.0 / tokens


def summarize(rows: list[dict[str, Any]], bootstrap: int, seed: int) -> dict[str, Any]:
    embedding = [float(row["embedding_ms_per_1k_tokens"]) for row in rows]
    extraction = [float(row["extraction_ms_per_1k_tokens"]) for row in rows]
    rng = random.Random(seed)
    embed_bootstrap = []
    extract_bootstrap = []
    delta_bootstrap = []
    for _ in range(bootstrap):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        embed_bootstrap.append(ratio(sample, "embedding_seconds"))
        extract_bootstrap.append(ratio(sample, "extraction_seconds"))
        delta_bootstrap.append(ratio(sample, "paired_generation_delta_seconds"))
    return {
        "runs": len(rows),
        "completion_tokens": sum(int(row["completion_tokens"]) for row in rows),
        "embedding_ms_per_1k_tokens": ratio(rows, "embedding_seconds"),
        "embedding_median_ms_per_1k_tokens": statistics.median(embedding),
        "embedding_sd_ms_per_1k_tokens": statistics.stdev(embedding) if len(embedding) > 1 else 0.0,
        "embedding_95ci_ms_per_1k_tokens": [
            percentile(embed_bootstrap, 0.025),
            percentile(embed_bootstrap, 0.975),
        ],
        "baseline_generation_ms_per_1k_tokens": ratio(rows, "baseline_generation_seconds"),
        "watermarked_generation_ms_per_1k_tokens": ratio(rows, "generation_seconds"),
        "paired_generation_delta_ms_per_1k_tokens": ratio(rows, "paired_generation_delta_seconds"),
        "paired_generation_delta_95ci_ms_per_1k_tokens": [
            percentile(delta_bootstrap, 0.025),
            percentile(delta_bootstrap, 0.975),
        ],
        "extraction_ms_per_1k_tokens": ratio(rows, "extraction_seconds"),
        "extraction_median_ms_per_1k_tokens": statistics.median(extraction),
        "extraction_sd_ms_per_1k_tokens": statistics.stdev(extraction) if len(extraction) > 1 else 0.0,
        "extraction_95ci_ms_per_1k_tokens": [
            percentile(extract_bootstrap, 0.025),
            percentile(extract_bootstrap, 0.975),
        ],
    }


def command_output(command: list[str]) -> str | None:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True).stdout.strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--workloads", type=Path, default=Path(__file__).with_name("workloads.json"))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    methods = tuple(item.strip().lower() for item in args.methods.split(",") if item.strip())
    unknown = sorted(set(methods) - set(METHODS))
    if unknown or not methods:
        parser.error(f"unknown or empty method selection: {unknown}")
    if args.repeats < 1 or args.warmups < 0 or args.max_tokens < 1 or args.bootstrap < 1:
        parser.error("repeats/max-tokens/bootstrap must be positive and warmups non-negative")

    endpoint = args.endpoint.rstrip("/")
    server_catalog = json_request(f"{endpoint}/v1/_processors", None, args.timeout)
    workloads = load_workloads(args.workloads.resolve())
    warmup_rows = []
    baseline_warmup_rows = []
    for warmup in range(args.warmups):
        baseline = run_baseline_once(
            endpoint,
            workloads[0],
            max_tokens=args.max_tokens,
            seed=args.seed - args.warmups + warmup,
            timeout=args.timeout,
            phase="warmup",
            repeat=warmup,
        )
        baseline_warmup_rows.append(baseline)
        for method in methods:
            print(f"warmup {warmup + 1}/{args.warmups}: {method}", file=sys.stderr, flush=True)
            warmup_rows.append(
                run_once(
                    endpoint,
                    method,
                    workloads[0],
                    max_tokens=args.max_tokens,
                    seed=args.seed - args.warmups + warmup,
                    timeout=args.timeout,
                    phase="warmup",
                    repeat=warmup,
                    baseline=baseline,
                )
            )

    rows_by_method = {method: [] for method in methods}
    baseline_rows = []
    benchmark_start = time.perf_counter()
    for repeat in range(args.repeats):
        for workload_index, workload in enumerate(workloads):
            run_seed = args.seed + repeat * len(workloads) + workload_index
            baseline = run_baseline_once(
                endpoint,
                workload,
                max_tokens=args.max_tokens,
                seed=run_seed,
                timeout=args.timeout,
                phase="measured",
                repeat=repeat,
            )
            baseline_rows.append(baseline)
            for method in methods:
                print(
                    f"measured {repeat + 1}/{args.repeats}: {workload['name']}: {method}",
                    file=sys.stderr,
                    flush=True,
                )
                rows_by_method[method].append(
                    run_once(
                        endpoint,
                        method,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=run_seed,
                        timeout=args.timeout,
                        phase="measured",
                        repeat=repeat,
                        baseline=baseline,
                    )
                )

    result = {
        "schema_version": 5,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "measurement_contract": {
            "embedding": "primary Table X estimator: method-owned logits-processor wall time with CUDA synchronized before and after each invocation",
            "paired_generation_delta": "secondary diagnostic: synchronized watermarked generation minus a same-workload, same-seed WM-OFF generation; retained because the difference also contains token-dependent model-path and system noise",
            "extraction": "complete continuation-only detect_last() invocation with CUDA synchronized before and after; SWEET includes an independent model forward over the generated continuation",
            "normalization": "elapsed_seconds * 1,000,000 / authoritative completion_tokens",
            "aggregation": "sum elapsed seconds / sum reference tokens",
            "model_forward_in_embedding": False,
            "codeip_variant": "released random-message branch without PDA/type predictor",
            "strength": "arithmetic midpoint of each method's RQ1 EEI",
            "sweet_admission": "every measured run must score at least one token and report detector_model_forward entropy provenance",
            "detector_scope": "generated continuation only; a one-token prefix is consumed by previous-token seeding and the remaining completion tokens are scored",
        },
        "workload": {
            "manifest": str(args.workloads.resolve()),
            "manifest_sha256": sha256_bytes(args.workloads.read_bytes()),
            "cases": workloads,
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": args.max_tokens,
            "base_seed": args.seed,
            "warmups_per_method": args.warmups,
            "measured_repeats": args.repeats,
            "method_order": list(methods),
            "eei_bounds": EEI_BOUNDS,
            "eei_midpoints": EEI_MIDPOINTS,
            "method_params": METHOD_PARAMS,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "nvidia_smi": command_output([
                "nvidia-smi",
                "--query-gpu=index,name,uuid,driver_version,memory.total",
                "--format=csv,noheader",
            ]),
            "source_commit": command_output(["git", "rev-parse", "HEAD"]),
            "benchmark_wall_seconds": time.perf_counter() - benchmark_start,
        },
        "server_catalog": server_catalog,
        "summary": {
            method: summarize(rows, args.bootstrap, args.seed + index)
            for index, (method, rows) in enumerate(rows_by_method.items())
        },
        "warmups": warmup_rows,
        "baseline_warmups": baseline_warmup_rows,
        "baseline_runs": baseline_rows,
        "runs": rows_by_method,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("| Method | Embedding ms/1K | Extraction ms/1K | Runs | Tokens |")
    print("|---|---:|---:|---:|---:|")
    for method in methods:
        row = result["summary"][method]
        print(
            f"| {method.upper()} | {row['embedding_ms_per_1k_tokens']:.2f} | "
            f"{row['extraction_ms_per_1k_tokens']:.2f} | {row['runs']} | "
            f"{row['completion_tokens']} |"
        )
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
