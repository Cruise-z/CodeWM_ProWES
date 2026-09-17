"""Zero-strength WM-OFF reference and parity helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from batch_snapshots import describe_snapshot_diff


def generation_response_manifest(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return stable generation facts without storing response contents."""
    return [
        {
            "filename": item.get("filename"),
            "finish_reason": item.get("finish_reason"),
            "response_content_sha256": item.get("response_content_sha256"),
            "generated_code_sha256": item.get("generated_code_sha256"),
            "detection_payload_sha256": item.get("detection_payload_sha256"),
        }
        for item in list(report.get("files") or [])
        if isinstance(item, dict)
    ]


def wm_off_reference_cache_key(
    *,
    project_name: str,
    repo_path: Path,
    rng_seed: int,
    language: str,
    args: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    generation_config = {
        "temperature": args["temperature"],
        "max_tokens": args["max_tokens"],
        "top_p": args.get("top_p", "<model-default>"),
    }
    payload = {
        "project_name": project_name,
        "repo_path": str(repo_path),
        "rng_seed": int(rng_seed),
        "language": language,
        "generation_config": generation_config,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), generation_config


def initial_zero_strength_audit(
    *,
    requested: bool,
    contract: str,
    rng_seed: int,
) -> dict[str, Any]:
    return {
        "requested": requested,
        "contract": contract,
        "reference_status": "pending" if requested else "not_requested",
        "reference_cache_hit": False,
        "reference_cache_key": None,
        "reference_generation_config": None,
        "reference_rng_seed": int(rng_seed) if requested else None,
        "reference_source_snapshot_hash": None,
        "reference_response_manifest": [],
        "reference_artifact_path": None,
        "comparison_status": "pending" if requested else "not_requested",
        "source_exact_match": None,
        "generated_text_exact_match": None,
        "finish_reasons_exact_match": None,
        "contract_status": "pending" if requested else "not_applicable",
    }


def _generated_text_exact_match(
    reference: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> Optional[bool]:
    if not reference or len(reference) != len(candidate):
        return None
    if not all(
        item.get("generated_code_sha256")
        for item in (*reference, *candidate)
    ):
        return None
    reference_text = [
        (item.get("filename"), item.get("generated_code_sha256"))
        for item in reference
    ]
    candidate_text = [
        (item.get("filename"), item.get("generated_code_sha256"))
        for item in candidate
    ]
    return reference_text == candidate_text


def compare_zero_strength_reference(
    *,
    contract: str,
    reference: dict[str, Any],
    candidate_snapshot: dict[str, str],
    candidate_snapshot_hash: str,
    candidate_manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    reference_snapshot = reference.get("source_snapshot")
    if not isinstance(reference_snapshot, dict) or not reference_snapshot:
        raise RuntimeError("zero-strength WM-OFF reference snapshot is invalid")

    reference_manifest = list(reference.get("generation_response_manifest") or [])
    reference_finish_reasons = [
        (item.get("filename"), item.get("finish_reason"))
        for item in reference_manifest
    ]
    candidate_finish_reasons = [
        (item.get("filename"), item.get("finish_reason"))
        for item in candidate_manifest
    ]
    finish_reasons_exact_match = (
        bool(reference_finish_reasons)
        and reference_finish_reasons == candidate_finish_reasons
    )
    generated_text_exact_match = _generated_text_exact_match(
        reference_manifest,
        candidate_manifest,
    )
    source_exact_match = candidate_snapshot == reference_snapshot
    source_diff = (
        None
        if source_exact_match
        else describe_snapshot_diff(reference_snapshot, candidate_snapshot)
    )

    if (
        source_exact_match
        and finish_reasons_exact_match
        and generated_text_exact_match is True
    ):
        comparison_status = "exact_match"
    elif (
        generated_text_exact_match is None
        and source_exact_match
        and finish_reasons_exact_match
    ):
        comparison_status = "incomplete_generation_evidence"
    else:
        comparison_status = "different"

    if contract == "exact_noop":
        if comparison_status == "exact_match":
            contract_status = "satisfied"
        elif comparison_status == "incomplete_generation_evidence":
            contract_status = "evidence_incomplete"
        else:
            contract_status = "violated"
    else:
        contract_status = (
            "exact_match" if comparison_status == "exact_match" else comparison_status
        )

    return {
        "status": comparison_status,
        "contract": contract,
        "source_exact_match": source_exact_match,
        "source_diff": source_diff,
        "generated_text_exact_match": generated_text_exact_match,
        "finish_reasons_exact_match": finish_reasons_exact_match,
        "contract_status": contract_status,
        "wm_off_source_snapshot_hash": reference.get("source_snapshot_hash"),
        "zero_strength_source_snapshot_hash": candidate_snapshot_hash,
    }
