#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


REQUIRED_COLUMNS = (
    "watermark_method",
    "project",
    "language",
    "seed_group",
    "method_config",
    "strength",
    "log_category",
    "category",
    "classification_source",
    "embedded",
    "evaluation_log",
)
OUTCOMES = {"Pass", "BE", "TE", "RE"}
VALID_CATEGORIES = OUTCOMES | {"Excluded", "Unknown"}
VALID_SOURCES = {
    "log_and_batch_summary",
    "batch_summary_calibrated",
    "excluded_by_batch_summary",
    "no_batch_summary",
}
RNG_SEED_RE = re.compile(r"(?:^|_)rngS=([^_]+)")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate the released master watermark table.")
    parser.add_argument("--input", type=Path, default=package_root / "data" / "watermark_points.csv")
    parser.add_argument("--metadata", type=Path, default=package_root / "metadata.json")
    args = parser.parse_args()

    input_path = args.input.resolve()
    metadata = json.loads(args.metadata.resolve().read_text(encoding="utf-8"))
    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        rows = list(reader)

    errors = []
    if columns != REQUIRED_COLUMNS:
        errors.append(f"columns differ: {columns}")
    if len(rows) != metadata["row_count"]:
        errors.append(f"row count {len(rows)} != {metadata['row_count']}")
    if sha256(input_path) != metadata["master_table_sha256"]:
        errors.append("master table SHA-256 differs from metadata")

    category_counts = Counter(row["category"] for row in rows)
    source_counts = Counter(row["classification_source"] for row in rows)
    if dict(category_counts) != metadata["category_counts"]:
        errors.append(f"category counts differ: {dict(category_counts)}")
    if dict(source_counts) != metadata["classification_source_counts"]:
        errors.append(f"classification source counts differ: {dict(source_counts)}")
    if sorted({row["watermark_method"] for row in rows}) != metadata["watermark_methods"]:
        errors.append("watermark methods differ from metadata")
    if sorted({row["project"] for row in rows}) != metadata["projects"]:
        errors.append("projects differ from metadata")
    if sorted({row["language"] for row in rows}) != metadata["languages"]:
        errors.append("languages differ from metadata")

    seen = set()
    for line_number, row in enumerate(rows, start=2):
        key = (
            row["watermark_method"], row["project"], row["language"], row["seed_group"],
            row["method_config"], row["strength"],
        )
        if key in seen:
            errors.append(f"duplicate point at CSV line {line_number}: {key}")
        seen.add(key)
        if row["category"] not in VALID_CATEGORIES:
            errors.append(f"invalid category at CSV line {line_number}: {row['category']}")
        if row["log_category"] not in VALID_CATEGORIES:
            errors.append(f"invalid log category at CSV line {line_number}: {row['log_category']}")
        try:
            if not math.isfinite(float(row["strength"])):
                raise ValueError
        except ValueError:
            errors.append(f"invalid strength at CSV line {line_number}: {row['strength']}")
        if row["embedded"] != "yes":
            errors.append(f"non-embedded row at CSV line {line_number}")
        if not RNG_SEED_RE.search(row["method_config"]):
            errors.append(f"missing rngS in method_config at CSV line {line_number}")
        source = row["classification_source"]
        if source == "log_and_batch_summary" and row["category"] != row["log_category"]:
            errors.append(f"log/summary mismatch at CSV line {line_number}")
        if source == "batch_summary_calibrated" and row["category"] == row["log_category"]:
            errors.append(f"unnecessary calibrated label at CSV line {line_number}")
        if source in {"excluded_by_batch_summary", "no_batch_summary"} and row["category"] != "Excluded":
            errors.append(f"invalid excluded source at CSV line {line_number}")
        if source not in VALID_SOURCES:
            errors.append(f"invalid classification source at CSV line {line_number}: {source}")

    evaluated = sum(category_counts[category] for category in OUTCOMES)
    if evaluated != metadata["evaluated_row_count"]:
        errors.append(f"evaluated row count {evaluated} != {metadata['evaluated_row_count']}")
    if errors:
        print("Dataset validation failed:")
        for error in errors[:50]:
            print(f"- {error}")
        if len(errors) > 50:
            print(f"- ... and {len(errors) - 50} more")
        raise SystemExit(1)
    print(
        f"Validation passed: {len(rows)} rows, {evaluated} evaluated outcomes, "
        f"{category_counts['Excluded']} excluded points."
    )


if __name__ == "__main__":
    main()
