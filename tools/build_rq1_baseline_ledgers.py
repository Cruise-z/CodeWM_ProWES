#!/usr/bin/env python3
"""Build reviewer-friendly indexes over the immutable RQ1 baseline evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "results" / "RQ1" / "05_baseline_qualification"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build_ledgers(root: Path) -> dict[str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []

    for evidence_path in sorted(root.glob("units/*/*/attempts/*/evidence.json")):
        evidence = load_json(evidence_path)
        unit_root = evidence_path.parents[2]
        attempts.append(
            {
                "unit_id": evidence["unit_id"],
                "project": unit_root.parent.name,
                "language": unit_root.name,
                "attempt": evidence["attempt"],
                "rng_seed": evidence["rng_seed"],
                "generation_complete": evidence["generation_complete"],
                "evaluator_return_code": evidence["evaluator_return_code"],
                "passed": evidence["passed"],
                "failure_stage": evidence.get("failure_stage") or "",
                "architecture_team_sha256": evidence["architecture_team_sha256"],
                "initial_repository_tree_sha256": evidence[
                    "initial_repository_tree_sha256"
                ],
                "generated_repository_tree_sha256": evidence[
                    "generated_repository_tree_sha256"
                ],
                "evidence_path": relative(evidence_path, root),
                "generation_report_path": relative(
                    evidence_path.with_name("generation_report.json"), root
                ),
                "evaluator_log_path": relative(
                    evidence_path.with_name("evaluator.log"), root
                ),
            }
        )

    for evidence_path in sorted(root.glob("units/*/*/accepted/evidence.json")):
        evidence = load_json(evidence_path)
        unit_root = evidence_path.parents[1]
        accepted.append(
            {
                "unit_id": evidence["unit_id"],
                "project": unit_root.parent.name,
                "language": unit_root.name,
                "attempt": evidence["attempt"],
                "rng_seed": evidence["rng_seed"],
                "evaluator_return_code": evidence["evaluator_return_code"],
                "passed": evidence["passed"],
                "accepted_repository_tree_sha256": evidence[
                    "accepted_repository_tree_sha256"
                ],
                "evidence_path": relative(evidence_path, root),
                "seed_path": relative(evidence_path.with_name("seed.json"), root),
                "repository_path": relative(evidence_path.parent / "repository", root),
                "selected_attempt_evidence_path": evidence["attempt_evidence"],
                "selected_attempt_generation_report_path": evidence[
                    "attempt_generation_report"
                ],
                "selected_attempt_evaluator_log_path": evidence[
                    "attempt_evaluator_log"
                ],
            }
        )

    for evidence_path in sorted(root.glob("units/*/*/replays/*/evidence.json")):
        evidence = load_json(evidence_path)
        unit_root = evidence_path.parents[2]
        replays.append(
            {
                "unit_id": evidence["unit_id"],
                "project": unit_root.parent.name,
                "language": unit_root.name,
                "replay": evidence["replay"],
                "rng_seed": evidence["rng_seed"],
                "generation_complete": evidence["generation_complete"],
                "evaluator_return_code": evidence["evaluator_return_code"],
                "passed": evidence["passed"],
                "content_identical_to_accepted": evidence[
                    "content_identical_to_accepted"
                ],
                "accepted_repository_tree_sha256": evidence[
                    "accepted_repository_tree_sha256"
                ],
                "replay_repository_tree_sha256": evidence[
                    "replay_repository_tree_sha256"
                ],
                "evidence_path": relative(evidence_path, root),
                "generation_report_path": relative(
                    evidence_path.with_name("generation_report.json"), root
                ),
                "evaluator_log_path": relative(
                    evidence_path.with_name("evaluator.log"), root
                ),
                "repository_path": relative(evidence_path.parent / "repository", root),
            }
        )

    return {
        "attempt_ledger.csv": attempts,
        "accepted_ledger.csv": accepted,
        "replay_ledger.csv": replays,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty ledger: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    output = arguments.output or arguments.evidence_root / "indexes"

    ledgers = build_ledgers(arguments.evidence_root)
    for name, rows in ledgers.items():
        write_csv(output / name, rows)
        print(f"wrote {len(rows):>2} rows to {output / name}")


if __name__ == "__main__":
    main()
