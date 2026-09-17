#!/usr/bin/env python3
"""Recompute the RQ3 Table X values from released raw records."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
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
    if tuple(payload["workload"]["method_order"]) != LOGITS_ORDER:
        raise ValueError("logits method order does not match the Table X contract")
    for case in payload["workload"]["cases"]:
        if sha256_text(case["rendered_prompt"]) != case["rendered_prompt_sha256"]:
            raise ValueError(f"{case['name']}: rendered-prompt digest mismatch")
    sweet_params = payload["workload"]["method_params"]["sweet"]
    if float(sweet_params["entropy_threshold"]) != 0.5:
        raise ValueError("SWEET Table X campaign must use the paper's ET=0.5 setting")
    for method in LOGITS_ORDER:
        records = payload["runs"][method]
        if len(records) != int(payload["summary"][method]["runs"]):
            raise ValueError(f"{method}: raw-run count disagrees with summary")
        for index, row in enumerate(records):
            tokens = int(row["completion_tokens"])
            if tokens <= 0:
                raise ValueError(f"{method} run {index}: non-positive token count")
            assert_close(
                float(row["embedding_seconds"]) * 1_000_000.0 / tokens,
                float(row["embedding_ms_per_1k_tokens"]),
                f"{method} run {index} embedding",
            )
            assert_close(
                float(row["extraction_seconds"]) * 1_000_000.0 / tokens,
                float(row["extraction_ms_per_1k_tokens"]),
                f"{method} run {index} extraction",
            )
            if sha256_text(row["generated_text"]) != row["generated_text_sha256"]:
                raise ValueError(f"{method} run {index}: generated-text digest mismatch")
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
    for index, row in enumerate(records):
        input_tokens = int(row["input_tokens"])
        watermarked_tokens = int(row["watermarked_tokens"])
        if input_tokens <= 0 or watermarked_tokens <= 0:
            raise ValueError(f"{method} run {index}: non-positive token count")
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
        "extraction_seconds",
        "embedding_reference_tokens",
        "extraction_reference_tokens",
        "embedding_ms_per_1k_tokens",
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
        "input_sha256",
        "output_sha256",
        "tokenizer_identifier",
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
                        "embedding_seconds": f"{float(row['embedding_seconds']):.12f}",
                        "extraction_seconds": f"{float(row['extraction_seconds']):.12f}",
                        "embedding_reference_tokens": row["completion_tokens"],
                        "extraction_reference_tokens": row["completion_tokens"],
                        "embedding_ms_per_1k_tokens": f"{float(row['embedding_ms_per_1k_tokens']):.9f}",
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
                        "input_sha256": row["prompt_sha256"],
                        "output_sha256": row["generated_text_sha256"],
                        "tokenizer_identifier": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
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
                        "extraction_seconds": f"{float(row['extraction_seconds']):.12f}",
                        "embedding_reference_tokens": row["input_tokens"],
                        "extraction_reference_tokens": row["watermarked_tokens"],
                        "embedding_ms_per_1k_tokens": f"{float(row['embedding_ms_per_1k_tokens']):.9f}",
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
                        "input_sha256": row["input_source_sha256"],
                        "output_sha256": row["watermarked_source_sha256"],
                        "tokenizer_identifier": tokenizer,
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
    output = (args.output_dir or root / "paper_reproduction/tables/rq3").resolve()
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
        embedding = normalized(records, "embedding_seconds", "completion_tokens")
        extraction = normalized(records, "extraction_seconds", "completion_tokens")
        embedded = logits["summary"][method]
        assert_close(embedding, float(embedded["embedding_ms_per_1k_tokens"]), f"{method} embedding")
        assert_close(extraction, float(embedded["extraction_ms_per_1k_tokens"]), f"{method} extraction")
        rows.append(
            {
                "paradigm": "Logits-bias",
                "method": DISPLAY[method],
                "training_seconds": None,
                "embedding_ms_per_1k_tokens": embedding,
                "embedding_95ci_lower": embedded["embedding_95ci_ms_per_1k_tokens"][0],
                "embedding_95ci_upper": embedded["embedding_95ci_ms_per_1k_tokens"][1],
                "extraction_ms_per_1k_tokens": extraction,
                "extraction_95ci_lower": embedded["extraction_95ci_ms_per_1k_tokens"][0],
                "extraction_95ci_upper": embedded["extraction_95ci_ms_per_1k_tokens"][1],
                "measured_runs": len(records),
                "embedding_reference_tokens": sum(int(row["completion_tokens"]) for row in records),
                "extraction_reference_tokens": sum(int(row["completion_tokens"]) for row in records),
            }
        )

    for method in ("codemark", "srcmarker"):
        payload = semantics[method]
        records = payload["runs"]
        embedding = normalized(records, "embedding_seconds", "input_tokens")
        extraction = normalized(records, "extraction_seconds", "watermarked_tokens")
        embedded = payload["summary"]
        assert_close(embedding, float(embedded["embedding_ms_per_1k_tokens"]), f"{method} embedding")
        assert_close(extraction, float(embedded["extraction_ms_per_1k_tokens"]), f"{method} extraction")
        rows.append(
            {
                "paradigm": "Semantic-preserving",
                "method": DISPLAY[method],
                "training_seconds": training_seconds(training_logs[method]),
                "embedding_ms_per_1k_tokens": embedding,
                "embedding_95ci_lower": embedded["embedding_95ci_ms_per_1k_tokens"][0],
                "embedding_95ci_upper": embedded["embedding_95ci_ms_per_1k_tokens"][1],
                "extraction_ms_per_1k_tokens": extraction,
                "extraction_95ci_lower": embedded["extraction_95ci_ms_per_1k_tokens"][0],
                "extraction_95ci_upper": embedded["extraction_95ci_ms_per_1k_tokens"][1],
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
                "schema_version": 1,
                "normalization": "sum(seconds) * 1,000,000 / sum(reference tokens)",
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
