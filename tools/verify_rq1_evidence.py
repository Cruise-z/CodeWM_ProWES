#!/usr/bin/env python3
"""Verify the released RQ1 baseline, applicability, and detectability evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from build_rq1_baseline_ledgers import build_ledgers


ROOT = Path(__file__).resolve().parents[1]
RQ1_RESULTS = ROOT / "results" / "RQ1"
BASELINE = RQ1_RESULTS / "05_baseline_qualification"
IGNORED_TREE_PARTS = {
    ".git",
    # Nested repositories are renamed on artifact import so Git does not treat
    # them as submodules. The original campaign hash ignored the same metadata
    # while it was still named .git.
    ".git-local-metadata",
    "DTResults",
    "__pycache__",
    ".pytest_cache",
    "build",
    "target",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    """Reproduce the campaign's canonical repository-tree hash."""
    entries = []
    for path in sorted(
        candidate for candidate in root.rglob("*") if candidate.is_file()
    ):
        relative = path.relative_to(root)
        if any(part in IGNORED_TREE_PARTS for part in relative.parts):
            continue
        entries.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    encoded = json.dumps(
        entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_baseline() -> dict[str, object]:
    provenance = json.loads(
        (BASELINE / "PROVENANCE.json").read_text(encoding="utf-8")
    )
    audit = json.loads((BASELINE / "ledger" / "audit.json").read_text(encoding="utf-8"))
    state = json.loads(
        (BASELINE / "ledger" / "campaign_state.json").read_text(encoding="utf-8")
    )
    results = csv_rows(BASELINE / "ledger" / "results.csv")
    results_json = json.loads(
        (BASELINE / "ledger" / "results.json").read_text(encoding="utf-8")
    )

    assert provenance["source_commit"] == "9c647f9a8d4e9bd519aefac7c0a8b6dc501cafaa"
    assert audit["complete"] is True
    assert audit["issues"] == []
    assert audit["expected_units"] == audit["accepted_count"] == 42
    assert audit["verified_replay_count"] == 42
    assert state["unit_count"] == state["accepted_count"] == 42
    assert state["attempt_count"] == 88
    assert state["replay_verified_count"] == 42
    assert len(results) == len(results_json["rows"]) == 42
    assert Counter(row["language"] for row in results) == {
        "cpp": 14,
        "java": 14,
        "python": 14,
    }
    assert sum(int(row["attempt_count"]) for row in results) == 88
    assert sum(int(row["verified_replay_count"]) for row in results) == 42

    original_reports = provenance["original_report_sha256"]
    for source_path, expected in original_reports.items():
        assert sha256(BASELINE / "ledger" / Path(source_path).name) == expected
    worker_logs = provenance["worker_log_sha256"]
    for source_path, expected in worker_logs.items():
        assert sha256(BASELINE / "logs" / Path(source_path).name) == expected

    manifest = BASELINE / "ledger" / "manifest.json"
    preflight = ROOT / "00_common" / "environment" / "preflight.json"
    model_weights = json.loads(
        (BASELINE / "evidence" / "model_weights.json").read_text(encoding="utf-8")
    )
    assert sha256(manifest) == audit["manifest_sha256"]
    assert sha256(preflight) == audit["preflight_sha256"]
    assert model_weights["manifest_sha256"] == audit["model_weight_manifest_sha256"]
    assert (
        provenance["implementation_traceability"][
            "campaign_runner_sha256_recorded_by_audit"
        ]
        == audit["campaign_runner_sha256"]
    )
    assert (
        sha256(ROOT / "RQ1" / "source" / "reproduct" / "campaign.py")
        == provenance["implementation_traceability"][
            "reviewer_facing_english_campaign_sha256"
        ]
    )

    all_attempts = list(BASELINE.glob("units/*/*/attempts/*/evidence.json"))
    all_accepted = list(BASELINE.glob("units/*/*/accepted/evidence.json"))
    all_replays = list(BASELINE.glob("units/*/*/replays/*/evidence.json"))
    assert len(all_attempts) == 88
    assert len(all_accepted) == len(all_replays) == 42

    passed_attempts = 0
    failed_attempts = 0
    checked_logs = 0
    checked_repository_hashes = 0
    checked_architecture_links = 0
    unit_ids: set[str] = set()
    for row in results:
        unit_id = row["unit_id"]
        assert unit_id not in unit_ids
        unit_ids.add(unit_id)

        accepted_path = BASELINE / row["accepted_evidence"]
        assert accepted_path.is_file()
        unit_root = accepted_path.parents[1]
        checkpoint_root = (
            ROOT
            / "RQ1"
            / "03_architecture_checkpoints"
            / unit_root.parent.name
            / unit_root.name
        )
        architecture = json.loads(
            (checkpoint_root / "architecture" / "evidence.json").read_text(
                encoding="utf-8"
            )
        )
        assert architecture["valid"] is True
        assert architecture["unit_id"] == unit_id
        assert architecture["team_json_sha256"] == row["architecture_team_sha256"]
        assert (
            sha256(checkpoint_root / "architecture" / "team" / "team.json")
            == row["architecture_team_sha256"]
        )
        assert (
            sha256(checkpoint_root / "architecture" / "prompt.txt")
            == architecture["prompt_sha256"]
        )
        assert (
            architecture["initial_repository_tree_sha256"]
            == row["initial_repository_tree_sha256"]
        )
        assert (
            tree_hash(checkpoint_root / "initial_repository" / unit_id)
            == row["initial_repository_tree_sha256"]
        )
        checked_architecture_links += 1

        attempt_paths = sorted((unit_root / "attempts").glob("*/evidence.json"))
        replay_paths = sorted((unit_root / "replays").glob("*/evidence.json"))
        assert len(attempt_paths) == int(row["attempt_count"])
        assert len(replay_paths) == int(row["verified_replay_count"]) == 1

        attempt_evidence = []
        for attempt_path in attempt_paths:
            evidence = json.loads(attempt_path.read_text(encoding="utf-8"))
            attempt_evidence.append(evidence)
            assert evidence["unit_id"] == unit_id
            assert evidence["architecture_team_sha256"] == row[
                "architecture_team_sha256"
            ]
            assert evidence["initial_repository_tree_sha256"] == row[
                "initial_repository_tree_sha256"
            ]
            assert evidence["generation_complete"] is True
            assert evidence["truncated_files"] == []
            assert evidence["generation_args"]["rng_seed"] == evidence["rng_seed"]
            assert sha256(attempt_path.with_name("generation_report.json")) == evidence[
                "generation_report_sha256"
            ]
            assert sha256(attempt_path.with_name("evaluator.log")) == evidence[
                "evaluator_log_sha256"
            ]
            checked_logs += 1
            generated_repository = (
                attempt_path.parent / evidence["unit_id"] / evidence["unit_id"]
            )
            assert generated_repository.is_dir()
            assert tree_hash(generated_repository) == evidence[
                "generated_repository_tree_sha256"
            ]
            checked_repository_hashes += 1
            if evidence["passed"]:
                passed_attempts += 1
                assert evidence["evaluator_return_code"] == 0
            else:
                failed_attempts += 1
                assert evidence["evaluator_return_code"] != 0

        assert [item["attempt"] for item in attempt_evidence] == list(
            range(1, len(attempt_evidence) + 1)
        )
        selected = attempt_evidence[-1]
        assert selected["attempt"] == int(row["selected_attempt"])
        assert selected["rng_seed"] == int(row["rng_seed"])
        assert selected["passed"] is True

        accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
        seed = json.loads(
            (accepted_path.parent / "seed.json").read_text(encoding="utf-8")
        )
        assert accepted["unit_id"] == seed["unit_id"] == unit_id
        assert accepted["attempt"] == seed["attempt"] == selected["attempt"]
        assert accepted["rng_seed"] == seed["rng_seed"] == selected["rng_seed"]
        assert accepted["architecture_team_sha256"] == row[
            "architecture_team_sha256"
        ]
        assert accepted["initial_repository_tree_sha256"] == row[
            "initial_repository_tree_sha256"
        ]
        assert accepted["passed"] is True
        assert accepted["evaluator_return_code"] == 0
        assert (
            BASELINE / accepted["attempt_evidence"]
        ).resolve() == attempt_paths[-1].resolve()
        assert sha256(BASELINE / accepted["attempt_generation_report"]) == accepted[
            "generation_report_sha256"
        ]
        assert sha256(BASELINE / accepted["attempt_evaluator_log"]) == accepted[
            "evaluator_log_sha256"
        ]
        accepted_hash = tree_hash(accepted_path.parent / "repository")
        assert accepted_hash == accepted["accepted_repository_tree_sha256"]
        assert accepted_hash == row["accepted_repository_tree_sha256"]
        checked_repository_hashes += 1

        replay_path = replay_paths[0]
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        assert replay["unit_id"] == unit_id
        assert replay["rng_seed"] == accepted["rng_seed"]
        assert replay["architecture_team_sha256"] == row[
            "architecture_team_sha256"
        ]
        assert replay["initial_repository_tree_sha256"] == row[
            "initial_repository_tree_sha256"
        ]
        assert replay["passed"] is True
        assert replay["generation_complete"] is True
        assert replay["evaluator_return_code"] == 0
        assert replay["content_identical_to_accepted"] is True
        assert replay["accepted_repository_tree_sha256"] == accepted_hash
        assert replay["replay_repository_tree_sha256"] == accepted_hash
        assert sha256(replay_path.with_name("generation_report.json")) == replay[
            "generation_report_sha256"
        ]
        assert sha256(replay_path.with_name("evaluator.log")) == replay[
            "evaluator_log_sha256"
        ]
        assert tree_hash(replay_path.parent / "repository") == accepted_hash
        checked_logs += 1
        checked_repository_hashes += 1

    assert passed_attempts == 42
    assert failed_attempts == 46
    assert audit["accepted_repository_hashes"] == {
        row["unit_id"]: row["accepted_repository_tree_sha256"] for row in results
    }
    assert audit["accepted_seeds"] == {
        row["unit_id"]: int(row["rng_seed"]) for row in results
    }

    generated_ledgers = build_ledgers(BASELINE)
    for name, expected_rows in generated_ledgers.items():
        observed = csv_rows(BASELINE / "indexes" / name)
        normalized = [
            {key: str(value) for key, value in row.items()} for row in expected_rows
        ]
        assert observed == normalized

    return {
        "campaign_complete": audit["complete"],
        "units": len(results),
        "attempts": len(all_attempts),
        "passed_attempts": passed_attempts,
        "failed_attempts": failed_attempts,
        "accepted_repositories": len(all_accepted),
        "verified_replays": len(all_replays),
        "checked_architecture_links": checked_architecture_links,
        "checked_generation_and_evaluator_logs": checked_logs,
        "checked_repository_tree_hashes": checked_repository_hashes,
        "derived_indexes": "PASS",
    }


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
        "baseline_qualification": verify_baseline(),
        "applicability": verify_applicability(),
        "detectability": verify_detectability(),
        "archive_digests": "PASS",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
