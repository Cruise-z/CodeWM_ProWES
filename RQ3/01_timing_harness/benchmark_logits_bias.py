#!/usr/bin/env python3
"""Measure RQ3 costs with the non-intrusive v2 paired-generation protocol.

Generation contains no per-token timer, CUDA synchronization, or detector
cache. Extraction runs separately from final text through a fresh processor.
Every raw paired observation is retained for independent recomputation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
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
        prompt_path = (root / item["prompt_file"]).resolve()
        prompt = prompt_path.read_text(encoding="utf-8")
        workloads.append(
            {
                "name": item["name"],
                "project": item["project"],
                "language": item["language"],
                "target_file": item["target_file"],
                "prompt_file": str(prompt_path),
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
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method_params = dict(METHOD_PARAMS[method])
    if method in {"stone", "codeip"}:
        method_params["language"] = workload["language"]
    payload = {
        "messages": [{"role": "user", "content": workload["rendered_prompt"]}],
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": max_tokens,
        "stream": False,
        "rng_seed": seed,
        "internal_processor_names": [],
        "external_processor_names": [method],
        "external_processor_params": {method: method_params},
        "watermark_detect": False,
        "force_max_tokens": True,
        "instrument_processor_timing": False,
        "capture_detection_state": False,
    }
    client_start = time.perf_counter()
    response = json_request(f"{endpoint}/v1/chat/completions", payload, timeout)
    client_elapsed = time.perf_counter() - client_start
    usage = response["usage"]
    choice = response["choices"][0]
    generation_metrics = choice.get("generation_metrics") or {}
    processor_metrics = choice.get("processor_metrics") or {}
    completion_tokens = int(usage["completion_tokens"])
    if completion_tokens != max_tokens or choice.get("finish_reason") != "length":
        raise RuntimeError(
            f"{method} did not produce the fixed {max_tokens}-token timing output: "
            f"tokens={completion_tokens}, finish={choice.get('finish_reason')}"
        )
    generated_text = str(choice.get("message", {}).get("content", ""))
    generation_seconds = float(generation_metrics.get("generation_elapsed_s", 0.0))
    if not generated_text or generation_seconds <= 0.0:
        raise RuntimeError(f"{method} returned empty text or invalid generation timing")
    if generation_metrics.get("watermark_detection_elapsed_s") is not None:
        raise RuntimeError(f"{method} unexpectedly ran detection during generation")
    if generation_metrics.get("processor_timing_enabled") is not False:
        raise RuntimeError(f"{method} did not disable generation-time processor timing")
    if generation_metrics.get("detection_state_enabled") is not False:
        raise RuntimeError(f"{method} did not disable generation-time detector state")
    if generation_metrics.get("force_max_tokens") is not True:
        raise RuntimeError(f"{method} did not acknowledge fixed-length generation")
    if any(int(metrics.get("lp_calls", 0)) != 0 for metrics in processor_metrics.values()):
        raise RuntimeError(f"{method} recorded per-token timing calls in v2 mode")

    detect_payload = {
        "method": method,
        "text": generated_text,
        "method_params": method_params,
        "rng_seed": seed,
        "temperature": 0.7,
        "top_p": 1.0,
    }
    detector_client_start = time.perf_counter()
    detection_response = json_request(
        f"{endpoint}/v1/watermark/detect", detect_payload, timeout
    )
    detector_client_seconds = time.perf_counter() - detector_client_start
    extraction_seconds = float(detection_response["extraction_elapsed_s"])
    extraction_tokens = int(detection_response["input_tokens"])
    detection = detection_response.get("wm_detection") or {}
    if extraction_seconds <= 0.0 or extraction_tokens <= 0:
        raise RuntimeError(f"{method} returned invalid standalone extraction metrics")
    validate_detection(method, detection, extraction_tokens)
    detector_contract = detection_response.get("measurement_contract") or {}
    if detector_contract.get("generation_state_reused") is not False:
        raise RuntimeError(f"{method} standalone detector reused generation state")

    row = {
        "phase": phase,
        "method": method,
        "workload": workload["name"],
        "project": workload["project"],
        "language": workload["language"],
        "repeat": repeat,
        "rng_seed": seed,
        "prompt_sha256": workload["rendered_prompt_sha256"],
        "prompt_tokens": int(usage["prompt_tokens"]),
        "completion_tokens": completion_tokens,
        "extraction_reference_tokens": extraction_tokens,
        "total_tokens": int(usage["total_tokens"]),
        "finish_reason": choice.get("finish_reason"),
        "extraction_seconds": float(extraction_seconds),
        "generation_seconds": generation_seconds,
        "client_seconds": client_elapsed,
        "detector_client_seconds": detector_client_seconds,
        "extraction_ms_per_1k_tokens": float(extraction_seconds)
        * 1_000_000.0
        / extraction_tokens,
        "watermarked_generation_ms_per_1k_tokens": generation_seconds * 1_000_000.0 / completion_tokens,
        "processor_components": processor_metrics,
        "wm_detection": detection,
        "standalone_detection_contract": detector_contract,
        "method_params": method_params,
        "generated_text": generated_text,
        "generated_text_sha256": sha256_bytes(generated_text.encode("utf-8")),
    }
    return pair_with_baseline(row, baseline) if baseline is not None else row


def pair_with_baseline(
    method_row: dict[str, Any],
    baseline: dict[str, Any],
    *,
    pair_order: str = "baseline_then_watermark",
) -> dict[str, Any]:
    """Attach one adjacent, same-seed WM-OFF measurement to a method row."""
    baseline_tokens = int(baseline["completion_tokens"])
    completion_tokens = int(method_row["completion_tokens"])
    if baseline_tokens != completion_tokens:
        raise RuntimeError(
            f"{method_row['method']} paired baseline token mismatch: "
            f"{baseline_tokens} != {completion_tokens}"
        )
    if baseline["workload"] != method_row["workload"]:
        raise RuntimeError("paired baseline workload mismatch")
    if int(baseline["rng_seed"]) != int(method_row["rng_seed"]):
        raise RuntimeError("paired baseline seed mismatch")
    baseline_seconds = float(baseline["generation_seconds"])
    delta_seconds = float(method_row["generation_seconds"]) - baseline_seconds
    method_row.update(
        {
            "pair_order": pair_order,
            "baseline_generation_seconds": baseline_seconds,
            "paired_generation_delta_seconds": delta_seconds,
            "baseline_generated_text_sha256": baseline["generated_text_sha256"],
            "baseline_generation_ms_per_1k_tokens": baseline_seconds
            * 1_000_000.0
            / completion_tokens,
            "paired_generation_delta_ms_per_1k_tokens": delta_seconds
            * 1_000_000.0
            / completion_tokens,
        }
    )
    return method_row

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
        "force_max_tokens": True,
        "instrument_processor_timing": False,
        "capture_detection_state": False,
    }
    client_start = time.perf_counter()
    response = json_request(f"{endpoint}/v1/chat/completions", payload, timeout)
    client_elapsed = time.perf_counter() - client_start
    usage = response["usage"]
    choice = response["choices"][0]
    generation_metrics = choice.get("generation_metrics") or {}
    completion_tokens = int(usage["completion_tokens"])
    if completion_tokens != max_tokens or choice.get("finish_reason") != "length":
        raise RuntimeError(
            f"WM-OFF did not produce the fixed {max_tokens}-token timing output: "
            f"tokens={completion_tokens}, finish={choice.get('finish_reason')}"
        )
    generation_seconds = generation_metrics.get("generation_elapsed_s")
    if generation_metrics.get("processor_timing_enabled") is not False:
        raise RuntimeError("WM-OFF baseline did not disable processor timing")
    if generation_metrics.get("detection_state_enabled") is not False:
        raise RuntimeError("WM-OFF baseline did not disable detector state")
    if generation_metrics.get("force_max_tokens") is not True:
        raise RuntimeError("WM-OFF baseline did not acknowledge fixed-length generation")
    if choice.get("processor_metrics"):
        raise RuntimeError("WM-OFF baseline unexpectedly returned processor metrics")
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


def ratio(
    rows: list[dict[str, Any]],
    field: str,
    token_field: str = "completion_tokens",
) -> float:
    seconds = sum(float(row[field]) for row in rows)
    tokens = sum(int(row[token_field]) for row in rows)
    return seconds * 1_000_000.0 / tokens


def hierarchical_sample(
    rows: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    """Resample workload clusters, then observations within each cluster."""

    clusters: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        clusters.setdefault(str(row["workload"]), []).append(row)
    names = sorted(clusters)
    sample = []
    for _ in names:
        cluster = clusters[names[rng.randrange(len(names))]]
        sample.extend(cluster[rng.randrange(len(cluster))] for _ in cluster)
    return sample


def summarize(rows: list[dict[str, Any]], bootstrap: int, seed: int) -> dict[str, Any]:
    delta = [float(row["paired_generation_delta_ms_per_1k_tokens"]) for row in rows]
    extraction = [float(row["extraction_ms_per_1k_tokens"]) for row in rows]
    rng = random.Random(seed)
    extract_bootstrap = []
    delta_bootstrap = []
    for _ in range(bootstrap):
        sample = hierarchical_sample(rows, rng)
        extract_bootstrap.append(
            ratio(sample, "extraction_seconds", "extraction_reference_tokens")
        )
        delta_bootstrap.append(ratio(sample, "paired_generation_delta_seconds"))
    order_counts = {
        order: sum(row["pair_order"] == order for row in rows)
        for order in ("baseline_then_watermark", "watermark_then_baseline")
    }
    return {
        "runs": len(rows),
        "workload_clusters": len({row["workload"] for row in rows}),
        "completion_tokens": sum(int(row["completion_tokens"]) for row in rows),
        "extraction_reference_tokens": sum(
            int(row["extraction_reference_tokens"]) for row in rows
        ),
        "pair_order_counts": order_counts,
        "baseline_generation_ms_per_1k_tokens": ratio(rows, "baseline_generation_seconds"),
        "watermarked_generation_ms_per_1k_tokens": ratio(rows, "generation_seconds"),
        "paired_generation_delta_ms_per_1k_tokens": ratio(rows, "paired_generation_delta_seconds"),
        "paired_generation_delta_median_ms_per_1k_tokens": statistics.median(delta),
        "paired_generation_delta_sd_ms_per_1k_tokens": statistics.stdev(delta)
        if len(delta) > 1
        else 0.0,
        "paired_generation_delta_95ci_ms_per_1k_tokens": [
            percentile(delta_bootstrap, 0.025),
            percentile(delta_bootstrap, 0.975),
        ],
        "table_x_embedding_ms_per_1k_tokens": ratio(
            rows, "paired_generation_delta_seconds"
        ),
        "table_x_embedding_95ci_ms_per_1k_tokens": [
            percentile(delta_bootstrap, 0.025),
            percentile(delta_bootstrap, 0.975),
        ],
        "extraction_ms_per_1k_tokens": ratio(
            rows,
            "extraction_seconds",
            "extraction_reference_tokens",
        ),
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
    warmup_cases = []
    seen_languages = set()
    for workload in workloads:
        if workload["language"] not in seen_languages:
            seen_languages.add(workload["language"])
            warmup_cases.append(workload)
    for warmup in range(args.warmups):
        for workload_index, workload in enumerate(warmup_cases):
            warmup_seed = args.seed - 10_000 + warmup * len(warmup_cases) + workload_index
            baseline_warmup_rows.append(
                run_baseline_once(
                    endpoint,
                    workload,
                    max_tokens=args.max_tokens,
                    seed=warmup_seed,
                    timeout=args.timeout,
                    phase="warmup",
                    repeat=warmup,
                )
            )
            for method in methods:
                print(
                    f"warmup {warmup + 1}/{args.warmups}: {workload['language']}: {method}",
                    file=sys.stderr,
                    flush=True,
                )
                warmup_rows.append(
                    run_once(
                        endpoint,
                        method,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=warmup_seed,
                        timeout=args.timeout,
                        phase="warmup",
                        repeat=warmup,
                    )
                )

    rows_by_method = {method: [] for method in methods}
    baseline_rows = []
    schedule = []
    benchmark_start = time.perf_counter()
    for repeat in range(args.repeats):
        for workload_index, workload in enumerate(workloads):
            run_seed = args.seed + repeat * len(workloads) + workload_index
            block_methods = list(methods)
            random.Random(args.seed + repeat * 10_000 + workload_index).shuffle(block_methods)
            for method_index, method in enumerate(block_methods):
                pair_index = (
                    (repeat * len(workloads) + workload_index) * len(methods)
                    + method_index
                )
                # Six workloads per repeat yield three pairs in each order for
                # every method; five repeats therefore yield exactly 15/15.
                baseline_first = (repeat + workload_index) % 2 == 0
                pair_order = (
                    "baseline_then_watermark"
                    if baseline_first
                    else "watermark_then_baseline"
                )
                print(
                    f"measured {repeat + 1}/{args.repeats}: {workload['name']}: "
                    f"{method}: {pair_order}",
                    file=sys.stderr,
                    flush=True,
                )
                schedule.append(
                    {
                        "pair_index": pair_index,
                        "repeat": repeat,
                        "workload": workload["name"],
                        "method": method,
                        "block_method_order": block_methods,
                        "pair_order": pair_order,
                    }
                )
                if baseline_first:
                    baseline = run_baseline_once(
                        endpoint,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=run_seed,
                        timeout=args.timeout,
                        phase="measured",
                        repeat=repeat,
                    )
                    method_row = run_once(
                        endpoint,
                        method,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=run_seed,
                        timeout=args.timeout,
                        phase="measured",
                        repeat=repeat,
                    )
                else:
                    method_row = run_once(
                        endpoint,
                        method,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=run_seed,
                        timeout=args.timeout,
                        phase="measured",
                        repeat=repeat,
                    )
                    baseline = run_baseline_once(
                        endpoint,
                        workload,
                        max_tokens=args.max_tokens,
                        seed=run_seed,
                        timeout=args.timeout,
                        phase="measured",
                        repeat=repeat,
                    )
                baseline["paired_method"] = method
                baseline["pair_order"] = pair_order
                baseline["pair_index"] = pair_index
                baseline_rows.append(baseline)
                rows_by_method[method].append(
                    pair_with_baseline(
                        method_row,
                        baseline,
                        pair_order=pair_order,
                    )
                )

    for method, rows in rows_by_method.items():
        order_counts = {
            order: sum(row["pair_order"] == order for row in rows)
            for order in ("baseline_then_watermark", "watermark_then_baseline")
        }
        if abs(order_counts["baseline_then_watermark"] - order_counts["watermark_then_baseline"]) > 1:
            raise RuntimeError(
                f"{method} pair order is not counterbalanced: {order_counts}"
            )

    result = {
        "schema_version": 7,
        "protocol_version": "unintrusive-v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "measurement_contract": {
            "embedding": "outer-boundary synchronized watermarked generation minus an adjacent same-workload, same-seed, same-length WM-OFF generation; no per-token timing or detection-only cache is active in either member",
            "pairing": "pair order is exactly balanced within every method and method order is independently shuffled in each workload-repeat block",
            "output_length": "both pair members are forced to the exact max_tokens cap so EOS cannot create unequal work or an incomplete CodeIP message block",
            "extraction": "fresh processor over final generated text; timed region includes final-text tokenization, detector transfers, and complete detect_last(), with no generation state reuse",
            "normalization": "embedding uses completion_tokens; extraction uses independently tokenized final-text tokens; both compute elapsed_seconds * 1,000,000 / reference_tokens",
            "aggregation": "ratio of summed seconds to summed reference tokens; 95% intervals use 10,000 hierarchical bootstrap resamples over workload clusters and runs within clusters",
            "cuda_synchronization": "all CUDA devices visible to the process are synchronized only at outer measurement boundaries",
            "shared_model_forward_removed_by_pairing": True,
            "codeip_variant": "released random-message branch without PDA/type predictor",
            "strength": "arithmetic midpoint of each method's RQ1 EEI",
            "sweet_admission": "every measured run must score at least one token and report detector_model_forward entropy provenance",
            "detector_scope": "final generated text only; previous-token detectors consume one seed token and score the remaining tokens",
        },
        "workload": {
            "manifest": str(args.workloads.resolve()),
            "manifest_sha256": sha256_bytes(args.workloads.read_bytes()),
            "cases": workloads,
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": args.max_tokens,
            "base_seed": args.seed,
            "warmups_per_language_method": args.warmups,
            "measured_repeats": args.repeats,
            "method_order": "seeded random permutation per workload-repeat block",
            "eei_bounds": EEI_BOUNDS,
            "eei_midpoints": EEI_MIDPOINTS,
            "base_method_params": METHOD_PARAMS,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
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
        "schedule": schedule,
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
            f"| {method.upper()} | {row['table_x_embedding_ms_per_1k_tokens']:.2f} | "
            f"{row['extraction_ms_per_1k_tokens']:.2f} | {row['runs']} | "
            f"{row['completion_tokens']} |"
        )
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
