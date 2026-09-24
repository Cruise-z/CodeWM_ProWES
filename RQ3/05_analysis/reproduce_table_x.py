#!/usr/bin/env python3
"""Recompute the RQ3 Table X values from released raw records."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import random
import re
from typing import Any


LOGITS_ORDER = ("wllm", "ewd", "sweet", "stone", "codeip", "waterfall")
DISPLAY = {
    "wllm": "WLLM",
    "ewd": "EWD",
    "sweet": "SWEET",
    "stone": "STONE",
    "codeip": "CodeIP",
    "waterfall": "Waterfall",
    "codemark": "CodeMark",
    "srcmarker": "SrcMarker",
}
TIMESTAMP = re.compile(r"^\[INFO (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+)\]")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized(rows: list[dict[str, Any]], seconds: str, tokens: str) -> float:
    token_total = sum(int(row[tokens]) for row in rows)
    if token_total <= 0:
        raise ValueError(f"non-positive token total for {seconds}/{tokens}")
    return sum(float(row[seconds]) for row in rows) * 1_000_000.0 / token_total


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_ratio(
    rows: list[dict[str, Any]],
    seconds_field: str,
    tokens_field: str,
    *,
    seed: int,
    replicates: int = 10_000,
    cluster_field: str | None = None,
) -> list[float]:
    """Recompute an interval from raw rows; never consume embedded CI values."""

    rng = random.Random(seed)
    estimates = []
    if cluster_field is None:
        for _ in range(replicates):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            estimates.append(normalized(sample, seconds_field, tokens_field))
    else:
        clusters: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            clusters.setdefault(str(row[cluster_field]), []).append(row)
        names = sorted(clusters)
        for _ in range(replicates):
            sample = []
            for _ in names:
                cluster = clusters[names[rng.randrange(len(names))]]
                sample.extend(cluster[rng.randrange(len(cluster))] for _ in cluster)
            estimates.append(normalized(sample, seconds_field, tokens_field))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def training_seconds(path: Path) -> float:
    timestamps = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TIMESTAMP.match(line)
        if match:
            timestamps.append(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f"))
    if len(timestamps) < 2:
        raise ValueError(f"training log has fewer than two timestamps: {path}")
    return (timestamps[-1] - timestamps[0]).total_seconds()


def assert_close(actual: float, recorded: float, label: str) -> None:
    tolerance = max(1e-9, abs(recorded) * 1e-10)
    if abs(actual - recorded) > tolerance:
        raise ValueError(f"{label}: recomputed {actual} != recorded {recorded}")


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


def verify_logits_records(payload: dict[str, Any]) -> None:
    if int(payload.get("schema_version", 0)) != 7:
        raise ValueError("logits timing evidence is not the final schema v7 contract")
    if payload.get("protocol_version") != "unintrusive-v2":
        raise ValueError("logits timing evidence is not the non-intrusive v2 protocol")
    if len(payload["workload"]["cases"]) != 6:
        raise ValueError("v2 requires six RQ1 prompt workloads")
    for case in payload["workload"]["cases"]:
        if sha256_text(case["rendered_prompt"]) != case["rendered_prompt_sha256"]:
            raise ValueError(f"{case['name']}: rendered-prompt digest mismatch")
    sweet_params = payload["workload"]["base_method_params"]["sweet"]
    if float(sweet_params["entropy_threshold"]) != 0.5:
        raise ValueError("SWEET Table X campaign must use the paper's ET=0.5 setting")
    baselines = payload.get("baseline_runs") or []
    expected_baselines = sum(len(payload["runs"][method]) for method in LOGITS_ORDER)
    if len(baselines) != expected_baselines:
        raise ValueError(
            f"expected one WM-OFF baseline per method row: {len(baselines)} != {expected_baselines}"
        )
    baseline_index = {
        (
            row["paired_method"],
            row["workload"],
            int(row["repeat"]),
            int(row["rng_seed"]),
            row["pair_order"],
        ): row
        for row in baselines
    }
    if len(baseline_index) != len(baselines):
        raise ValueError("WM-OFF pair manifest contains duplicate pair keys")
    for method in LOGITS_ORDER:
        records = payload["runs"][method]
        if len(records) != int(payload["summary"][method]["runs"]):
            raise ValueError(f"{method}: raw-run count disagrees with summary")
        order_counts = Counter(row.get("pair_order") for row in records)
        if order_counts != Counter(
            {"baseline_then_watermark": 15, "watermark_then_baseline": 15}
        ):
            raise ValueError(f"{method}: pair order is not 15/15 counterbalanced")
        for index, row in enumerate(records):
            tokens = int(row["completion_tokens"])
            extraction_tokens = int(row["extraction_reference_tokens"])
            if tokens != int(payload["workload"]["max_tokens"]):
                raise ValueError(f"{method} run {index}: output is not fixed length")
            if extraction_tokens <= 0:
                raise ValueError(f"{method} run {index}: non-positive extraction tokens")
            assert_close(
                float(row["extraction_seconds"]) * 1_000_000.0 / extraction_tokens,
                float(row["extraction_ms_per_1k_tokens"]),
                f"{method} run {index} extraction",
            )
            assert_close(
                float(row["baseline_generation_seconds"]) * 1_000_000.0 / tokens,
                float(row["baseline_generation_ms_per_1k_tokens"]),
                f"{method} run {index} baseline generation",
            )
            if any(
                int(component.get("lp_calls", 0)) != 0
                for component in row.get("processor_components", {}).values()
            ):
                raise ValueError(f"{method} run {index}: intrusive processor timing was active")
            if (
                row.get("standalone_detection_contract", {}).get("generation_state_reused") is not False
            ):
                raise ValueError(f"{method} run {index}: extraction reused generation state")
            assert_close(
                float(row["generation_seconds"]) * 1_000_000.0 / tokens,
                float(row["watermarked_generation_ms_per_1k_tokens"]),
                f"{method} run {index} watermarked generation",
            )
            assert_close(
                float(row["paired_generation_delta_seconds"]) * 1_000_000.0 / tokens,
                float(row["paired_generation_delta_ms_per_1k_tokens"]),
                f"{method} run {index} paired generation delta",
            )
            baseline_key = (
                method,
                row["workload"],
                int(row["repeat"]),
                int(row["rng_seed"]),
                row["pair_order"],
            )
            baseline = baseline_index.get(baseline_key)
            if baseline is None:
                raise ValueError(f"{method} run {index}: paired WM-OFF row is missing")
            if int(baseline["completion_tokens"]) != tokens:
                raise ValueError(f"{method} run {index}: paired token counts differ")
            if baseline["generated_text_sha256"] != row["baseline_generated_text_sha256"]:
                raise ValueError(f"{method} run {index}: baseline output digest mismatch")
            assert_close(
                float(row["generation_seconds"])
                - float(baseline["generation_seconds"]),
                float(row["paired_generation_delta_seconds"]),
                f"{method} run {index} paired subtraction",
            )
            if sha256_text(row["generated_text"]) != row["generated_text_sha256"]:
                raise ValueError(f"{method} run {index}: generated-text digest mismatch")
            if method in ("wllm", "ewd", "sweet", "stone"):
                detector_inputs = mappings_with_field(
                    row.get("wm_detection"), "detector_input_tokens"
                )
                if len(detector_inputs) != 1:
                    raise ValueError(
                        f"{method} run {index}: missing detector input evidence"
                    )
                detector = detector_inputs[0]
                if detector.get("detector_scope") != "continuation":
                    raise ValueError(
                        f"{method} run {index}: detector scope is not continuation"
                    )
                if int(detector["detector_input_tokens"]) != extraction_tokens:
                    raise ValueError(
                        f"{method} run {index}: detector/extraction token mismatch"
                    )
            if method == "sweet":
                scores = mappings_with_field(row.get("wm_detection"), "num_tokens_scored")
                if len(scores) != 1 or int(scores[0]["num_tokens_scored"]) <= 0:
                    raise ValueError(
                        f"sweet run {index}: detector did not score a positive token count"
                    )
                entropy = scores[0].get("entropy")
                if not isinstance(entropy, dict) or entropy.get("source") != "detector_model_forward":
                    raise ValueError(
                        f"sweet run {index}: missing independent detector entropy provenance"
                    )
                if int(entropy.get("qualified_tokens", -1)) != int(scores[0]["num_tokens_scored"]):
                    raise ValueError(
                        f"sweet run {index}: entropy-qualified/scored-token mismatch"
                    )


def verify_semantic_records(
    root: Path, method: str, payload: dict[str, Any]
) -> None:
    if int(payload.get("schema_version", 0)) != 2:
        raise ValueError(f"{method}: semantic timing evidence is not schema v2")
    if payload.get("protocol_version") != "unintrusive-v2":
        raise ValueError(f"{method}: semantic timing evidence is not v2")
    records = payload["runs"]
    if len(records) != int(payload["configuration"]["measured_samples"]):
        raise ValueError(f"{method}: measured-sample count disagrees with raw rows")
    checkpoint = (
        root
        / "results/RQ2/02_training/checkpoints"
        / f"fresh_rq2_{method}_42_csn_js/models_best.pt"
    )
    recorded_checkpoint = payload["configuration"]["checkpoint_sha256"]
    if sha256_file(checkpoint) != recorded_checkpoint:
        raise ValueError(f"{method}: released checkpoint digest mismatch")
    released_parser = root / "RQ2/source/cStyleLang/parser/languages.so"
    if sha256_file(released_parser) != payload["configuration"]["parser_library_sha256"]:
        raise ValueError(f"{method}: released parser-library digest mismatch")
    metadata = payload.get("transformation_metadata") or {}
    expected_metadata = {
        "feasible_transform",
        "transforms_per_file",
        "variable_names",
    }
    if set(metadata) != expected_metadata:
        raise ValueError(f"{method}: incomplete transformation-metadata manifest")
    if any(not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))) for item in metadata.values()):
        raise ValueError(f"{method}: invalid transformation-metadata digest")
    for index, row in enumerate(records):
        input_tokens = int(row["input_tokens"])
        watermarked_tokens = int(row["watermarked_tokens"])
        if input_tokens <= 0 or watermarked_tokens <= 0:
            raise ValueError(f"{method} run {index}: non-positive token count")
        for prefix in ("input", "watermarked"):
            internal = int(row[f"{prefix}_internal_tokens"])
            model_tokens = int(row[f"{prefix}_model_tokens"])
            if internal <= 0 or model_tokens <= 0 or model_tokens > 512:
                raise ValueError(f"{method} run {index}: invalid {prefix} model-token evidence")
            if bool(row[f"{prefix}_truncated"]) != (internal > model_tokens):
                raise ValueError(
                    f"{method} run {index}: inconsistent {prefix} truncation flag"
                )
        assert_close(
            float(row["embedding_seconds"]) * 1_000_000.0 / input_tokens,
            float(row["embedding_ms_per_1k_tokens"]),
            f"{method} run {index} embedding",
        )
        assert_close(
            float(row["extraction_seconds"]) * 1_000_000.0 / watermarked_tokens,
            float(row["extraction_ms_per_1k_tokens"]),
            f"{method} run {index} extraction",
        )


def flatten_records(
    artifact_root: Path,
    logits: dict[str, Any],
    semantics: dict[str, dict[str, Any]],
) -> None:
    timing_path = artifact_root / "RQ3/02_raw_timings/raw_timings.csv"
    token_path = artifact_root / "RQ3/04_token_counts/token_counts.csv"
    timing_fields = [
        "paradigm",
        "method",
        "dataset_or_workload",
        "sample_or_seed",
        "repeat",
        "embedding_seconds",
        "baseline_generation_seconds",
        "watermarked_generation_seconds",
        "paired_generation_delta_seconds",
        "extraction_seconds",
        "embedding_reference_tokens",
        "extraction_reference_tokens",
        "embedding_ms_per_1k_tokens",
        "baseline_generation_ms_per_1k_tokens",
        "watermarked_generation_ms_per_1k_tokens",
        "paired_generation_delta_ms_per_1k_tokens",
        "extraction_ms_per_1k_tokens",
    ]
    token_fields = [
        "paradigm",
        "method",
        "dataset_or_workload",
        "sample_or_seed",
        "repeat",
        "input_or_prompt_tokens",
        "generated_or_watermarked_tokens",
        "extraction_reference_tokens",
        "baseline_generated_tokens",
        "input_internal_tokens",
        "watermarked_internal_tokens",
        "input_model_tokens",
        "watermarked_model_tokens",
        "input_truncated",
        "watermarked_truncated",
        "input_sha256",
        "output_sha256",
        "baseline_output_sha256",
        "tokenizer_identifier",
        "pair_order",
    ]
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with timing_path.open("w", encoding="utf-8", newline="") as timing_stream, token_path.open(
        "w", encoding="utf-8", newline=""
    ) as token_stream:
        timing_writer = csv.DictWriter(timing_stream, fieldnames=timing_fields)
        token_writer = csv.DictWriter(token_stream, fieldnames=token_fields)
        timing_writer.writeheader()
        token_writer.writeheader()
        for method in LOGITS_ORDER:
            for row in logits["runs"][method]:
                timing_writer.writerow(
                    {
                        "paradigm": "logits-bias",
                        "method": DISPLAY[method],
                        "dataset_or_workload": row["workload"],
                        "sample_or_seed": row["rng_seed"],
                        "repeat": row["repeat"],
                        "embedding_seconds": f"{float(row['paired_generation_delta_seconds']):.12f}",
                        "baseline_generation_seconds": f"{float(row['baseline_generation_seconds']):.12f}",
                        "watermarked_generation_seconds": f"{float(row['generation_seconds']):.12f}",
                        "paired_generation_delta_seconds": f"{float(row['paired_generation_delta_seconds']):.12f}",
                        "extraction_seconds": f"{float(row['extraction_seconds']):.12f}",
                        "embedding_reference_tokens": row["completion_tokens"],
                        "extraction_reference_tokens": row["extraction_reference_tokens"],
                        "embedding_ms_per_1k_tokens": f"{float(row['paired_generation_delta_ms_per_1k_tokens']):.9f}",
                        "baseline_generation_ms_per_1k_tokens": f"{float(row['baseline_generation_ms_per_1k_tokens']):.9f}",
                        "watermarked_generation_ms_per_1k_tokens": f"{float(row['watermarked_generation_ms_per_1k_tokens']):.9f}",
                        "paired_generation_delta_ms_per_1k_tokens": f"{float(row['paired_generation_delta_ms_per_1k_tokens']):.9f}",
                        "extraction_ms_per_1k_tokens": f"{float(row['extraction_ms_per_1k_tokens']):.9f}",
                    }
                )
                token_writer.writerow(
                    {
                        "paradigm": "logits-bias",
                        "method": DISPLAY[method],
                        "dataset_or_workload": row["workload"],
                        "sample_or_seed": row["rng_seed"],
                        "repeat": row["repeat"],
                        "input_or_prompt_tokens": row["prompt_tokens"],
                        "generated_or_watermarked_tokens": row["completion_tokens"],
                        "extraction_reference_tokens": row["extraction_reference_tokens"],
                        "input_internal_tokens": "",
                        "watermarked_internal_tokens": "",
                        "input_model_tokens": "",
                        "watermarked_model_tokens": "",
                        "input_truncated": "",
                        "watermarked_truncated": "",
                        "baseline_generated_tokens": row["completion_tokens"],
                        "input_sha256": row["prompt_sha256"],
                        "output_sha256": row["generated_text_sha256"],
                        "baseline_output_sha256": row["baseline_generated_text_sha256"],
                        "tokenizer_identifier": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
                        "pair_order": row["pair_order"],
                    }
                )
        for method in ("codemark", "srcmarker"):
            payload = semantics[method]
            tokenizer = payload["reference_tokenizer"]["identifier"]
            for row in payload["runs"]:
                timing_writer.writerow(
                    {
                        "paradigm": "semantic-preserving",
                        "method": DISPLAY[method],
                        "dataset_or_workload": row["dataset"],
                        "sample_or_seed": row["sample_uid"],
                        "repeat": row["repeat"],
                        "embedding_seconds": f"{float(row['embedding_seconds']):.12f}",
                        "baseline_generation_seconds": "",
                        "watermarked_generation_seconds": "",
                        "paired_generation_delta_seconds": "",
                        "extraction_seconds": f"{float(row['extraction_seconds']):.12f}",
                        "embedding_reference_tokens": row["input_tokens"],
                        "extraction_reference_tokens": row["watermarked_tokens"],
                        "embedding_ms_per_1k_tokens": f"{float(row['embedding_ms_per_1k_tokens']):.9f}",
                        "baseline_generation_ms_per_1k_tokens": "",
                        "watermarked_generation_ms_per_1k_tokens": "",
                        "paired_generation_delta_ms_per_1k_tokens": "",
                        "extraction_ms_per_1k_tokens": f"{float(row['extraction_ms_per_1k_tokens']):.9f}",
                    }
                )
                token_writer.writerow(
                    {
                        "paradigm": "semantic-preserving",
                        "method": DISPLAY[method],
                        "dataset_or_workload": row["dataset"],
                        "sample_or_seed": row["sample_uid"],
                        "repeat": row["repeat"],
                        "input_or_prompt_tokens": row["input_tokens"],
                        "generated_or_watermarked_tokens": row["watermarked_tokens"],
                        "extraction_reference_tokens": row["watermarked_tokens"],
                        "input_internal_tokens": row["input_internal_tokens"],
                        "watermarked_internal_tokens": row["watermarked_internal_tokens"],
                        "input_model_tokens": row["input_model_tokens"],
                        "watermarked_model_tokens": row["watermarked_model_tokens"],
                        "input_truncated": row["input_truncated"],
                        "watermarked_truncated": row["watermarked_truncated"],
                        "baseline_generated_tokens": "",
                        "input_sha256": row["input_source_sha256"],
                        "output_sha256": row["watermarked_source_sha256"],
                        "baseline_output_sha256": "",
                        "tokenizer_identifier": tokenizer,
                        "pair_order": "",
                    }
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = args.artifact_root.resolve()
    output = (args.output_dir or root / "paper_reproduction/tables/RQ3").resolve()
    raw = root / "RQ3/02_raw_timings"
    logits = load(raw / "logits_bias_raw.json")
    semantics = {
        "codemark": load(raw / "codemark_csn_js_raw.json"),
        "srcmarker": load(raw / "srcmarker_csn_js_raw.json"),
    }
    verify_logits_records(logits)
    for method, payload in semantics.items():
        verify_semantic_records(root, method, payload)
    training_logs = {
        "codemark": root / "RQ3/03_training_logs/codemark_csn_js_training.log",
        "srcmarker": root / "RQ3/03_training_logs/srcmarker_csn_js_training.log",
    }
    tokenizer_manifest = semantics["codemark"]["reference_tokenizer"]
    if tokenizer_manifest != semantics["srcmarker"]["reference_tokenizer"]:
        raise ValueError("semantic methods did not use the same reference tokenizer")
    tokenizer_output = root / "RQ3/04_token_counts/tokenizer_manifest.json"
    tokenizer_output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer_output.write_text(
        json.dumps(tokenizer_manifest, indent=2) + "\n", encoding="utf-8"
    )

    rows = []
    for method in LOGITS_ORDER:
        records = logits["runs"][method]
        embedding = normalized(
            records, "paired_generation_delta_seconds", "completion_tokens"
        )
        extraction = normalized(
            records, "extraction_seconds", "extraction_reference_tokens"
        )
        baseline_generation = normalized(
            records, "baseline_generation_seconds", "completion_tokens"
        )
        watermarked_generation = normalized(
            records, "generation_seconds", "completion_tokens"
        )
        embedding_ci = bootstrap_ratio(
            records,
            "paired_generation_delta_seconds",
            "completion_tokens",
            seed=20260917 + LOGITS_ORDER.index(method),
            cluster_field="workload",
        )
        extraction_ci = bootstrap_ratio(
            records,
            "extraction_seconds",
            "extraction_reference_tokens",
            seed=20261017 + LOGITS_ORDER.index(method),
            cluster_field="workload",
        )
        embedded = logits["summary"][method]
        assert_close(
            embedding,
            float(embedded["table_x_embedding_ms_per_1k_tokens"]),
            f"{method} Table X paired embedding",
        )
        assert_close(extraction, float(embedded["extraction_ms_per_1k_tokens"]), f"{method} extraction")
        rows.append(
            {
                "paradigm": "Logits-bias",
                "method": DISPLAY[method],
                "training_seconds": None,
                "embedding_ms_per_1k_tokens": embedding,
                "embedding_95ci_lower": embedding_ci[0],
                "embedding_95ci_upper": embedding_ci[1],
                "baseline_generation_ms_per_1k_tokens": baseline_generation,
                "watermarked_generation_ms_per_1k_tokens": watermarked_generation,
                "paired_generation_delta_ms_per_1k_tokens": embedding,
                "paired_generation_delta_95ci_lower": embedding_ci[0],
                "paired_generation_delta_95ci_upper": embedding_ci[1],
                "extraction_ms_per_1k_tokens": extraction,
                "extraction_95ci_lower": extraction_ci[0],
                "extraction_95ci_upper": extraction_ci[1],
                "measured_runs": len(records),
                "embedding_reference_tokens": sum(int(row["completion_tokens"]) for row in records),
                "extraction_reference_tokens": sum(
                    int(row["extraction_reference_tokens"]) for row in records
                ),
            }
        )

    for method in ("codemark", "srcmarker"):
        payload = semantics[method]
        records = payload["runs"]
        embedding = normalized(records, "embedding_seconds", "input_tokens")
        extraction = normalized(records, "extraction_seconds", "watermarked_tokens")
        method_offset = 0 if method == "codemark" else 1
        embedding_ci = bootstrap_ratio(
            records,
            "embedding_seconds",
            "input_tokens",
            seed=20261117 + method_offset,
        )
        extraction_ci = bootstrap_ratio(
            records,
            "extraction_seconds",
            "watermarked_tokens",
            seed=20261217 + method_offset,
        )
        embedded = payload["summary"]
        assert_close(embedding, float(embedded["embedding_ms_per_1k_tokens"]), f"{method} embedding")
        assert_close(extraction, float(embedded["extraction_ms_per_1k_tokens"]), f"{method} extraction")
        rows.append(
            {
                "paradigm": "Semantic-preserving",
                "method": DISPLAY[method],
                "training_seconds": training_seconds(training_logs[method]),
                "embedding_ms_per_1k_tokens": embedding,
                "embedding_95ci_lower": embedding_ci[0],
                "embedding_95ci_upper": embedding_ci[1],
                "baseline_generation_ms_per_1k_tokens": None,
                "watermarked_generation_ms_per_1k_tokens": None,
                "paired_generation_delta_ms_per_1k_tokens": None,
                "paired_generation_delta_95ci_lower": None,
                "paired_generation_delta_95ci_upper": None,
                "extraction_ms_per_1k_tokens": extraction,
                "extraction_95ci_lower": extraction_ci[0],
                "extraction_95ci_upper": extraction_ci[1],
                "measured_runs": len(records),
                "embedding_reference_tokens": sum(int(row["input_tokens"]) for row in records),
                "extraction_reference_tokens": sum(int(row["watermarked_tokens"]) for row in records),
            }
        )

    training_output = root / "RQ3/03_training_logs/training_times.csv"
    with training_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["method", "dataset", "training_seconds", "source_log"],
        )
        writer.writeheader()
        for method in ("codemark", "srcmarker"):
            row = next(item for item in rows if item["method"] == DISPLAY[method])
            writer.writerow(
                {
                    "method": DISPLAY[method],
                    "dataset": "csn_js",
                    "training_seconds": f"{row['training_seconds']:.3f}",
                    "source_log": training_logs[method].name,
                }
            )

    flatten_records(root, logits, semantics)
    output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (output / "table_x.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output / "table_x.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "protocol_version": "unintrusive-v2",
                "normalization": "sum(seconds) * 1,000,000 / sum(reference tokens)",
                "logits_embedding_estimator": "fixed-length paired synchronized generation delta: watermarked minus adjacent WM-OFF, with exactly balanced order and no generation-time observation",
                "logits_extraction_estimator": "fresh processor over final text, including tokenization and detector execution without generation-state reuse",
                "confidence_intervals": "recomputed here from raw rows: workload-cluster hierarchical bootstrap for logits methods and sample bootstrap for semantic methods; 10,000 replicates",
                "rows": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    latex = [
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Paradigm & Method & Training (s) & Embedding (ms/1K tok.) & Extraction (ms/1K tok.) \\",
        r"\midrule",
    ]
    last_paradigm = None
    for row in rows:
        paradigm = row["paradigm"] if row["paradigm"] != last_paradigm else ""
        training = "--" if row["training_seconds"] is None else f"{row['training_seconds']:.0f}"
        latex.append(
            f"{paradigm} & {row['method']} & {training} & "
            f"{row['embedding_ms_per_1k_tokens']:.2f} & "
            f"{row['extraction_ms_per_1k_tokens']:.2f} \\\\"
        )
        last_paradigm = row["paradigm"]
    latex.extend([r"\bottomrule", r"\end{tabular}"])
    (output / "table_x.tex").write_text("\n".join(latex) + "\n", encoding="utf-8")

    print("Method,Training(s),Embedding(ms/1K),Extraction(ms/1K)")
    for row in rows:
        training = "-" if row["training_seconds"] is None else f"{row['training_seconds']:.0f}"
        print(
            f"{row['method']},{training},{row['embedding_ms_per_1k_tokens']:.2f},"
            f"{row['extraction_ms_per_1k_tokens']:.2f}"
        )
    print(f"wrote {output / 'table_x.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
