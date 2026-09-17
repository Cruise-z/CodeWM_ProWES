#!/usr/bin/env python3
"""Verify the released RQ1 applicability and detectability evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RQ1_RESULTS = ROOT / "results" / "RQ1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_ledger(root: Path, ledger_name: str) -> int:
    checked = 0
    for line_number, line in enumerate(
        (root / ledger_name).read_text(encoding="utf-8").splitlines(), 1
    ):
        expected, separator, relative = line.partition("  ")
        if not separator:
            raise AssertionError(f"{ledger_name}:{line_number}: malformed line")
        target = root / relative.removeprefix("./")
        if not target.is_file():
            raise AssertionError(f"{ledger_name}: missing {relative}")
        actual = sha256(target)
        if actual != expected:
            raise AssertionError(f"{ledger_name}: checksum mismatch for {relative}")
        checked += 1
    return checked


def verify_applicability() -> dict[str, object]:
    package = RQ1_RESULTS / "Applicability"
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    with (package / "data" / "watermark_points.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    categories = Counter(row["category"] for row in rows)
    runs = {
        (
            row["watermark_method"],
            row["project"],
            row["language"],
            row["seed_group"],
            row["method_config"],
        )
        for row in rows
    }
    assert len(rows) == metadata["row_count"] == 9141
    assert categories == Counter(metadata["category_counts"])
    assert len(runs) == metadata["parameter_run_count"] == 302
    assert sum(value for key, value in categories.items() if key != "Excluded") == 9068
    assert categories["Excluded"] == 73
    assert len(list((package / "data").rglob("*batch_summary*.json"))) == 298

    completed = subprocess.run(
        [sys.executable, str(package / "scripts" / "validate_dataset.py")],
        cwd=package,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "rows": len(rows),
        "evaluated_rows": len(rows) - categories["Excluded"],
        "excluded_rows": categories["Excluded"],
        "parameter_runs": len(runs),
        "batch_summaries": 298,
        "checksums": verify_ledger(package, "SHA256SUMS"),
        "validator": completed.stdout.strip(),
    }


def verify_detectability() -> dict[str, object]:
    package = RQ1_RESULTS / "Detectability"
    summary = json.loads(
        (package / "derived" / "audit_summary.json").read_text(encoding="utf-8")
    )
    table_check = json.loads(
        (package / "audit" / "table_verification.json").read_text(encoding="utf-8")
    )
    assert summary["status"] == "PASS"
    assert summary["n_runs"] == 20
    assert len(summary["repositories"]) == 4
    assert len(summary["methods"]) == 5
    assert summary["strengths"] == [0.5, 1.0, 2.0, 3.0]
    assert table_check["status"] == "PASS"
    assert table_check["checked_numeric_cells"] == 120
    assert table_check["mismatches"] == []
    assert len(list((package / "raw_logs").glob("*.txt"))) == 4
    return {
        "runs": summary["n_runs"],
        "repositories": len(summary["repositories"]),
        "methods": len(summary["methods"]),
        "checked_table_cells": table_check["checked_numeric_cells"],
        "checksums": verify_ledger(package, "SHA256SUMS.txt"),
    }


def main() -> None:
    provenance = json.loads(
        (RQ1_RESULTS / "ARCHIVE_PROVENANCE.json").read_text(encoding="utf-8")
    )
    for archive in provenance["archives"]:
        assert sha256(ROOT / archive["path"]) == archive["sha256"]

    report = {
        "status": "PASS",
        "applicability": verify_applicability(),
        "detectability": verify_detectability(),
        "archive_digests": "PASS",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
