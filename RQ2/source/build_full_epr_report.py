#!/usr/bin/env python3
"""Validate and archive the full three-language, four-channel rule EPR run."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "fresh" / "epr_rule"
FINAL = OUT / "final"
DATASETS = {
    "mbcpp": ("C++", "training/SrcMarker_fresh/datasets/mbcpp/test.jsonl"),
    "mbjp": ("Java", "training/SrcMarker_fresh/datasets/mbjp/test.jsonl"),
    "mbjsp": ("JavaScript", "training/SrcMarker_fresh/datasets/mbjsp/test.jsonl"),
}
CHANNELS = ("id", "expr", "block", "all")
STATUS_NAMES = (
    "baseline_fail", "no_op", "syntax_invalid", "execution_invalid",
    "valid_attack", "error",
)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def version(command):
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, check=True)
    return completed.stdout.strip().splitlines()[0]


def main():
    rows = []
    artifacts = []
    failure_stages = {}
    for dataset, (language, relative_dataset_path) in DATASETS.items():
        dataset_path = ROOT / relative_dataset_path
        artifacts.append({"role": "dataset", "path": relative_dataset_path, "sha256": sha256(dataset_path)})
        for channel in CHANNELS:
            result_path = OUT / f"{dataset}_rule_{channel}.jsonl"
            summary_path = OUT / f"{dataset}_rule_{channel}_summary.json"
            if not result_path.is_file() or not summary_path.is_file():
                raise FileNotFoundError(f"missing full EPR output for {dataset}/{channel}")
            records = load_jsonl(result_path)
            summary = load_json(summary_path)
            if len(records) != summary["n_total"]:
                raise ValueError(f"row count mismatch for {dataset}/{channel}")
            observed_statuses = {
                status: sum(record.get("status") == status for record in records)
                for status in STATUS_NAMES
            }
            if observed_statuses != summary["status_counts"]:
                raise ValueError(f"status count mismatch for {dataset}/{channel}")
            stages = {}
            for record in records:
                if record.get("status") == "execution_invalid":
                    stage = record.get("post_stage", "unknown")
                    stages[stage] = stages.get(stage, 0) + 1
            failure_stages[f"{dataset}/{channel}"] = stages
            rows.append({
                "dataset": dataset,
                "language": language,
                "channel": channel,
                "n_total": summary["n_total"],
                "n_baseline_pass": summary["n_baseline_pass"],
                "n_changed": summary["n_changed"],
                "n_syntax_valid_changed": summary["n_syntax_valid_changed"],
                "n_post_pass": summary["n_post_pass"],
                "attack_coverage": summary["attack_coverage"],
                "syntax_validity_given_changed": summary["syntax_validity_given_changed"],
                "EPR_given_valid_changed": summary["EPR_given_valid_changed"],
                "status_counts": summary["status_counts"],
                "result_sha256": sha256(result_path),
                "summary_sha256": sha256(summary_path),
            })
            artifacts.extend([
                {"role": "per_sample_results", "path": str(result_path.relative_to(ROOT)),
                 "sha256": sha256(result_path)},
                {"role": "summary", "path": str(summary_path.relative_to(ROOT)),
                 "sha256": sha256(summary_path)},
            ])

    total_valid = sum(row["n_syntax_valid_changed"] for row in rows)
    total_passed = sum(row["n_post_pass"] for row in rows)
    weighted_epr = total_passed / total_valid
    code_paths = [
        ROOT / "project/srcMarker/SrcMarker/validate_mbxp_rq2.py",
        ROOT / "merge_mbxp_epr_chunks.py",
        ROOT / "rq2_revision/rule_attack.py",
        ROOT / "rq2_revision/common.py",
        ROOT / "rq2_revision/node_shims/lodash/index.js",
        ROOT / "training/SrcMarker_fresh/parser/languages.so",
    ]
    artifacts.extend({"role": "implementation", "path": str(path.relative_to(ROOT)),
                      "sha256": sha256(path)} for path in code_paths)

    java_root = Path("/home/zhaorz/software/jdks/jdk-21.0.12.1+1/bin")
    node = Path("/home/zhaorz/software/anaconda3/envs/baseMetagpt/lib/python3.9/site-packages/playwright/driver/node")
    archive = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "attack": "deterministic rule transformation",
            "seed": 42,
            "scope": "all available rows in MBCPP, MBJP, and MBJSP",
            "channels": list(CHANNELS),
            "EPR_definition": "post_pass / syntax_valid_changed among baseline-pass tasks",
            "main_dataset_mapping": {
                "GitHub-C": "MBCPP",
                "GitHub-Java": "MBJP",
                "CSN-JavaScript": "MBJSP",
                "CSN-Java": "MBJP",
            },
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpp_compiler": version(["g++", "--version"]),
            "java_compiler": version([str(java_root / "javac"), "-version"]),
            "java_runtime": version([str(java_root / "java"), "-version"]),
            "node_runtime": version([str(node), "--version"]),
        },
        "results": rows,
        "aggregate": {
            "n_cells": len(rows),
            "n_attempted_across_cells": sum(row["n_total"] for row in rows),
            "n_syntax_valid_changed_across_cells": total_valid,
            "n_post_pass_across_cells": total_passed,
            "weighted_EPR": weighted_epr,
        },
        "execution_invalid_stage_counts": failure_stages,
        "artifacts": artifacts,
    }

    FINAL.mkdir(parents=True, exist_ok=True)
    json_path = FINAL / "rq2_full_rule_epr.json"
    json_path.write_text(json.dumps(archive, indent=2), encoding="utf-8")

    csv_path = FINAL / "rq2_full_rule_epr.csv"
    csv_fields = (
        "dataset", "language", "channel", "n_total", "n_baseline_pass", "n_changed",
        "n_syntax_valid_changed", "n_post_pass", "attack_coverage",
        "syntax_validity_given_changed", "EPR_given_valid_changed", "result_sha256",
        "summary_sha256",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows({field: row[field] for field in csv_fields} for row in rows)

    table = []
    for row in rows:
        table.append(
            f"| {row['dataset'].upper()} | {row['language']} | {row['channel']} | "
            f"{row['n_total']} | {row['n_baseline_pass']} | {row['n_changed']} | "
            f"{row['n_syntax_valid_changed']} | {row['n_post_pass']} | "
            f"{row['EPR_given_valid_changed']:.2%} |"
        )
    report = f"""# RQ2 full rule-attack EPR validation

EPR is computed over samples that pass the baseline tests and are both changed and syntax-valid after attack: `post_pass / syntax_valid_changed`. Every sample in the three executable benchmarks is tested separately under each of the four attack channels with seed 42.

| Dataset | Language | Channel | Total | Baseline pass | Changed | Syntax-valid changed | Post-pass | EPR |
|---|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

The weighted EPR across the 12 experiment cells is **{weighted_epr:.2%}** ({total_passed}/{total_valid}). See `rq2_full_rule_epr.json` for per-sample outputs, failure stages, runtime environment, and SHA-256 values.

Execution-validity evidence is matched by language: GitHub-C to MBCPP, GitHub-Java and CSN-Java to MBJP, and CSN-JavaScript to MBJSP. GitHub and CSN do not include executable test suites, so Tree-sitter syntax validity is not described as per-sample functional correctness.
"""
    (FINAL / "RQ2_FULL_RULE_EPR.md").write_text(report, encoding="utf-8")
    print(json.dumps(archive["aggregate"], indent=2))
    print(f"wrote EPR archive metadata to {FINAL}")


if __name__ == "__main__":
    main()
