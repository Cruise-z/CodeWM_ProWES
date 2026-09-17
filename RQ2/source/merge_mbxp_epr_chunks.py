#!/usr/bin/env python3
"""Merge ordered MBXP EPR chunks and recompute the canonical summary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


STATUSES = (
    "baseline_fail", "no_op", "syntax_invalid", "execution_invalid",
    "valid_attack", "error",
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--attack", default="rule")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = parse_args()
    input_paths = [Path(value) for value in args.input]
    rows = []
    chunk_records = []
    for path in input_paths:
        chunk_rows = read_jsonl(path)
        rows.extend(chunk_rows)
        chunk_records.append({"path": str(path), "rows": len(chunk_rows), "sha256": sha256_file(path)})

    task_ids = [row.get("task_id") for row in rows]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("duplicate task_id found while merging EPR chunks")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    baseline = [row for row in rows if row.get("baseline_pass")]
    changed = [row for row in baseline if row.get("changed")]
    valid = [row for row in changed if row.get("syntax_valid")]
    passed = [row for row in valid if row.get("post_pass")]
    summary = {
        "n_total": len(rows),
        "n_baseline_pass": len(baseline),
        "n_changed": len(changed),
        "n_syntax_valid_changed": len(valid),
        "n_post_pass": len(passed),
        "attack_coverage": len(changed) / len(baseline) if baseline else None,
        "syntax_validity_given_changed": len(valid) / len(changed) if changed else None,
        "EPR_given_valid_changed": len(passed) / len(valid) if valid else None,
        "language": args.language,
        "channel": args.channel,
        "attack": args.attack,
        "seed": args.seed,
        "status_counts": {
            status: sum(row.get("status") == status for row in rows)
            for status in STATUSES
        },
        "merged_chunks": chunk_records,
        "output_sha256": sha256_file(output),
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
