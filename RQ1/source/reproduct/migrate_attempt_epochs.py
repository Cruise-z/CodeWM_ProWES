#!/usr/bin/env python3
"""Migrate seed-attempt statistics to the current architecture epoch.

Obsolete attempts remain available under the matching architecture failure
directory.  Attempts matching the current architecture are renumbered from
one, and accepted metadata is updated without changing the accepted seed or
repository content.
"""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

import campaign


def synchronize_accepted_epochs() -> List[Dict[str, Any]]:
    synchronized: List[Dict[str, Any]] = []
    for unit in campaign.all_units():
        if not campaign.accepted_is_valid(unit):
            continue
        architecture = campaign.load_json(
            campaign.architecture_dir(unit) / "evidence.json"
        )
        accepted_root = campaign.accepted_dir(unit)
        seed_path = accepted_root / "seed.json"
        evidence_path = accepted_root / "evidence.json"
        seed_record = campaign.load_json(seed_path)
        accepted_evidence = campaign.load_json(evidence_path)
        epoch = {
            "architecture_attempt": architecture.get("architecture_attempt"),
            "architecture_team_sha256": architecture.get("team_json_sha256"),
            "initial_repository_tree_sha256": architecture.get(
                "initial_repository_tree_sha256"
            ),
            "prompt_sha256": architecture.get("prompt_sha256"),
        }
        seed_record["architecture_epoch"] = epoch
        accepted_evidence["architecture_epoch"] = epoch
        campaign.atomic_json(seed_path, seed_record)
        campaign.atomic_json(evidence_path, accepted_evidence)
        synchronized.append(
            {
                "unit_id": unit["unit_id"],
                "rng_seed": seed_record["rng_seed"],
                "attempt": seed_record["attempt"],
                **epoch,
            }
        )
    return synchronized


def replace_paths(value: Any, replacements: List[Tuple[str, str]]) -> Any:
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [replace_paths(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_paths(item, replacements) for key, item in value.items()
        }
    return value


def unique_destination(root: Path, name: str) -> Path:
    candidate = root / name
    suffix = 1
    while candidate.exists():
        candidate = root / "{}_{}".format(name, suffix)
        suffix += 1
    return candidate


def matching_failure_root(
    unit: Dict[str, Any], team_sha256: str, initial_sha256: str
) -> Path:
    failures_root = campaign.unit_dir(unit) / "architecture_failures"
    if failures_root.exists():
        for candidate in sorted(path for path in failures_root.iterdir() if path.is_dir()):
            evidence_path = candidate / "evidence.json"
            if not evidence_path.exists():
                continue
            try:
                evidence = campaign.load_json(evidence_path)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if (
                evidence.get("team_json_sha256") == team_sha256
                and evidence.get("initial_repository_tree_sha256") == initial_sha256
            ):
                return candidate
    fallback = campaign.unit_dir(unit) / "obsolete_attempts" / "{}_{}".format(
        team_sha256[:12] or "unknownteam",
        initial_sha256[:12] or "unknowninitial",
    )
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def migrate_unit(unit: Dict[str, Any]) -> Dict[str, Any]:
    architecture_path = campaign.architecture_dir(unit) / "evidence.json"
    if not architecture_path.exists():
        return {"unit_id": unit["unit_id"], "skipped": "missing architecture evidence"}
    architecture = campaign.load_json(architecture_path)
    current_team = str(architecture.get("team_json_sha256") or "")
    current_initial = str(architecture.get("initial_repository_tree_sha256") or "")
    if not current_team or not current_initial:
        return {"unit_id": unit["unit_id"], "skipped": "incomplete architecture identity"}

    raw_attempts = campaign.raw_attempt_dirs(unit)
    current: List[Tuple[Path, Dict[str, Any]]] = []
    interrupted: List[Tuple[Path, Dict[str, Any]]] = []
    obsolete: List[Tuple[Path, Dict[str, Any]]] = []
    for path in raw_attempts:
        evidence_path = path / "evidence.json"
        try:
            evidence = campaign.load_json(evidence_path)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            evidence = {
                "unit_id": unit["unit_id"],
                "migration_note": "missing or unreadable attempt evidence",
            }
        matches = bool(
            evidence.get("architecture_team_sha256") == current_team
            and evidence.get("initial_repository_tree_sha256") == current_initial
        )
        if matches and evidence.get("migration_interrupted_in_flight_attempt") is True:
            interrupted.append((path, evidence))
        elif matches:
            current.append((path, evidence))
        else:
            obsolete.append((path, evidence))

    archived: List[Dict[str, Any]] = []
    for path, evidence in obsolete:
        old_team = str(evidence.get("architecture_team_sha256") or "unknownteam")
        old_initial = str(
            evidence.get("initial_repository_tree_sha256") or "unknowninitial"
        )
        archive_root = matching_failure_root(unit, old_team, old_initial) / "attempts"
        archive_root.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(archive_root, path.name)
        evidence.update(
            {
                "valid_for_current_architecture": False,
                "invalidated_at": campaign.utc_now(),
                "invalidated_by_architecture_team_sha256": current_team,
                "invalidated_by_initial_repository_tree_sha256": current_initial,
            }
        )
        campaign.atomic_json(path / "evidence.json", evidence)
        old_relative = str(path.relative_to(campaign.REPRO_ROOT))
        shutil.move(str(path), str(destination))
        archived.append(
            {
                "from": old_relative,
                "to": str(destination.relative_to(campaign.REPRO_ROOT)),
                "rng_seed": evidence.get("rng_seed"),
            }
        )

    excluded_interrupted: List[Dict[str, Any]] = []
    for path, evidence in interrupted:
        interrupted_root = (
            campaign.unit_dir(unit)
            / "interrupted_attempts"
            / "{}_{}".format(current_team[:12], current_initial[:12])
        )
        interrupted_root.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(interrupted_root, path.name)
        evidence.update(
            {
                "valid_for_current_architecture": True,
                "count_as_seed_test_attempt": False,
                "excluded_from_attempt_statistics": True,
                "exclusion_reason": "generation interrupted for attempt-epoch migration",
                "excluded_at": campaign.utc_now(),
            }
        )
        campaign.atomic_json(path / "evidence.json", evidence)
        old_relative = str(path.relative_to(campaign.REPRO_ROOT))
        shutil.move(str(path), str(destination))
        excluded_interrupted.append(
            {
                "from": old_relative,
                "to": str(destination.relative_to(campaign.REPRO_ROOT)),
                "rng_seed": evidence.get("rng_seed"),
            }
        )

    attempts_root = campaign.unit_dir(unit) / "attempts"
    attempts_root.mkdir(parents=True, exist_ok=True)
    staged: List[Tuple[Path, Path, Path, Dict[str, Any], int]] = []
    for ordinal, (old_path, evidence) in enumerate(current, start=1):
        seed = int(evidence.get("rng_seed") or old_path.name.rsplit("_", 1)[-1])
        final_path = attempts_root / "{:04d}_seed_{}".format(ordinal, seed)
        temporary = attempts_root / ".epoch_migration_{}_{}".format(
            uuid.uuid4().hex, old_path.name
        )
        old_path.rename(temporary)
        staged.append((old_path, temporary, final_path, evidence, ordinal))

    renumbered: List[Dict[str, Any]] = []
    replacements: List[Tuple[str, str]] = []
    seed_to_final: Dict[int, Tuple[Path, int]] = {}
    for old_path, temporary, final_path, evidence, ordinal in staged:
        if final_path.exists():
            raise RuntimeError("renumber destination exists: {}".format(final_path))
        temporary.rename(final_path)
        old_relative = str(old_path.relative_to(campaign.REPRO_ROOT))
        final_relative = str(final_path.relative_to(campaign.REPRO_ROOT))
        replacements.extend(
            [
                (str(old_path), str(final_path)),
                (old_relative, final_relative),
            ]
        )
        old_attempt = evidence.get("attempt")
        evidence = replace_paths(evidence, replacements[-2:])
        evidence.update(
            {
                "attempt": ordinal,
                "valid_for_current_architecture": True,
                "architecture_epoch": {
                    "architecture_attempt": architecture.get("architecture_attempt"),
                    "architecture_team_sha256": current_team,
                    "initial_repository_tree_sha256": current_initial,
                    "prompt_sha256": architecture.get("prompt_sha256"),
                },
            }
        )
        if old_attempt != ordinal:
            evidence["original_global_attempt"] = old_attempt
        interrupted = not bool(evidence.get("completed_at"))
        if interrupted:
            evidence.update(
                {
                    "completed_at": campaign.utc_now(),
                    "failure_stage": "interrupted_for_attempt_epoch_migration",
                    "migration_interrupted_in_flight_attempt": True,
                    "passed": False,
                }
            )
        campaign.atomic_json(final_path / "evidence.json", evidence)
        seed = int(evidence["rng_seed"])
        seed_to_final[seed] = (final_path, ordinal)
        renumbered.append(
            {
                "from": old_relative,
                "to": final_relative,
                "rng_seed": seed,
                "attempt": ordinal,
                "interrupted": interrupted,
            }
        )

    accepted_root = campaign.accepted_dir(unit)
    accepted_updated = False
    if (accepted_root / "seed.json").exists() and (accepted_root / "evidence.json").exists():
        seed_record = campaign.load_json(accepted_root / "seed.json")
        accepted_evidence = campaign.load_json(accepted_root / "evidence.json")
        accepted_seed = int(seed_record["rng_seed"])
        if accepted_seed not in seed_to_final:
            raise RuntimeError(
                "accepted seed {} for {} does not belong to current architecture".format(
                    accepted_seed, unit["unit_id"]
                )
            )
        final_path, ordinal = seed_to_final[accepted_seed]
        accepted_evidence = replace_paths(accepted_evidence, replacements)
        evaluator_name = Path(
            str(accepted_evidence.get("attempt_evaluator_log") or "evaluator.log")
        ).name
        seed_record["attempt"] = ordinal
        seed_record["architecture_epoch"] = {
            "architecture_attempt": architecture.get("architecture_attempt"),
            "architecture_team_sha256": current_team,
            "initial_repository_tree_sha256": current_initial,
            "prompt_sha256": architecture.get("prompt_sha256"),
        }
        accepted_evidence.update(
            {
                "attempt": ordinal,
                "valid_for_current_architecture": True,
                "architecture_epoch": {
                    "architecture_attempt": architecture.get("architecture_attempt"),
                    "architecture_team_sha256": current_team,
                    "initial_repository_tree_sha256": current_initial,
                    "prompt_sha256": architecture.get("prompt_sha256"),
                },
                "attempt_evidence": str(
                    (final_path / "evidence.json").relative_to(campaign.REPRO_ROOT)
                ),
                "attempt_generation_report": str(
                    (final_path / "generation_report.json").relative_to(
                        campaign.REPRO_ROOT
                    )
                ),
                "attempt_evaluator_log": str(
                    (final_path / evaluator_name).relative_to(campaign.REPRO_ROOT)
                ),
            }
        )
        campaign.atomic_json(accepted_root / "seed.json", seed_record)
        campaign.atomic_json(accepted_root / "evidence.json", accepted_evidence)
        accepted_updated = True

    return {
        "unit_id": unit["unit_id"],
        "architecture_attempt": architecture.get("architecture_attempt"),
        "architecture_team_sha256": current_team,
        "initial_repository_tree_sha256": current_initial,
        "archived_obsolete_attempt_count": len(archived),
        "excluded_interrupted_attempt_count": len(excluded_interrupted),
        "current_attempt_count": len(renumbered),
        "archived": archived,
        "excluded_interrupted": excluded_interrupted,
        "renumbered": renumbered,
        "accepted_metadata_updated": accepted_updated,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accepted-only", action="store_true")
    args = parser.parse_args()
    if args.accepted_only:
        synchronized = synchronize_accepted_epochs()
        payload = {
            "schema_version": 1,
            "synchronized_at": campaign.utc_now(),
            "accepted_count": len(synchronized),
            "units": synchronized,
        }
        evidence_root = campaign.REPRO_ROOT / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        campaign.atomic_json(evidence_root / "accepted_epoch_sync_latest.json", payload)
        campaign.refresh_state()
        campaign.write_results(campaign.all_units())
        print(json.dumps({"accepted_synchronized": len(synchronized)}, indent=2))
        return 0

    started_at = campaign.utc_now()
    evidence_root = campaign.REPRO_ROOT / "evidence"
    previous_path = evidence_root / "attempt_epoch_migration_latest.json"
    previous = campaign.load_json(previous_path) if previous_path.exists() else {}
    units = [migrate_unit(unit) for unit in campaign.all_units()]
    run_totals = {
        "archived_obsolete_attempts": sum(
            int(item.get("archived_obsolete_attempt_count", 0)) for item in units
        ),
        "excluded_interrupted_attempts": sum(
            int(item.get("excluded_interrupted_attempt_count", 0)) for item in units
        ),
        "current_attempts": sum(
            int(item.get("current_attempt_count", 0)) for item in units
        ),
        "accepted_metadata_updated": sum(
            bool(item.get("accepted_metadata_updated")) for item in units
        ),
    }
    previous_cumulative = previous.get("cumulative_totals") or previous.get("totals") or {}
    payload = {
        "schema_version": 1,
        "started_at": started_at,
        "completed_at": campaign.utc_now(),
        "policy": (
            "Seed attempts are valid only for the exact current architecture team "
            "and initial-repository hashes; current-epoch attempts are numbered from 1."
        ),
        "units": units,
        "previous_migration_completed_at": previous.get("completed_at"),
        "totals": run_totals,
        "cumulative_totals": {
            "archived_obsolete_attempts": int(
                previous_cumulative.get("archived_obsolete_attempts", 0)
            )
            + run_totals["archived_obsolete_attempts"],
            "excluded_interrupted_attempts": int(
                previous_cumulative.get("excluded_interrupted_attempts", 0)
            )
            + run_totals["excluded_interrupted_attempts"],
            "accepted_metadata_updates": int(
                previous_cumulative.get(
                    "accepted_metadata_updates",
                    previous_cumulative.get("accepted_metadata_updated", 0),
                )
            )
            + run_totals["accepted_metadata_updated"],
            "current_attempts": run_totals["current_attempts"],
        },
    }
    evidence_root.mkdir(parents=True, exist_ok=True)
    campaign.atomic_json(evidence_root / "attempt_epoch_migration_latest.json", payload)
    campaign.refresh_state()
    campaign.write_results(campaign.all_units())
    print(json.dumps({"run": payload["totals"], "cumulative": payload["cumulative_totals"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
