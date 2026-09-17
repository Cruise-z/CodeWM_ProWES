#!/usr/bin/env python3
"""Merge a method-specific corrected timing campaign into the Table X record."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any


CONTRACT_FIELDS = (
    "manifest_sha256",
    "temperature",
    "top_p",
    "max_tokens",
    "base_seed",
    "warmups_per_method",
    "measured_repeats",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def case_signature(payload: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (str(case["name"]), str(case["rendered_prompt_sha256"]))
        for case in payload["workload"]["cases"]
    ]


def campaign(payload: dict[str, Any], methods: list[str]) -> dict[str, Any]:
    return {
        "methods": methods,
        "created_at_utc": payload["created_at_utc"],
        "environment": payload["environment"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--method", default="sweet")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    method = args.method.strip().lower()
    base = load(args.base)
    correction = load(args.correction)
    correction_methods = tuple(correction["workload"]["method_order"])
    if correction_methods != (method,):
        raise ValueError(
            f"correction must contain only {method!r}, got {correction_methods}"
        )
    if method not in base["workload"]["method_order"]:
        raise ValueError(f"base record does not contain method {method!r}")
    for field in CONTRACT_FIELDS:
        if base["workload"][field] != correction["workload"][field]:
            raise ValueError(
                f"workload contract mismatch for {field}: "
                f"{base['workload'][field]!r} != {correction['workload'][field]!r}"
            )
    if case_signature(base) != case_signature(correction):
        raise ValueError("rendered workload cases differ between timing campaigns")

    merged = deepcopy(base)
    previous_methods = [
        item for item in base["workload"]["method_order"] if item != method
    ]
    old_campaigns = base.get("measurement_campaigns")
    if old_campaigns:
        retained_campaigns = []
        for item in old_campaigns:
            retained = [name for name in item["methods"] if name != method]
            if retained:
                clone = deepcopy(item)
                clone["methods"] = retained
                retained_campaigns.append(clone)
    else:
        retained_campaigns = [campaign(base, previous_methods)]

    merged["schema_version"] = max(4, int(correction.get("schema_version", 0)))
    merged["created_at_utc"] = correction["created_at_utc"]
    merged["measurement_contract"] = correction["measurement_contract"]
    merged["environment"] = {
        "mixed_campaigns": True,
        "details": "See measurement_campaigns for method-specific environments and source revisions.",
    }
    merged["measurement_campaigns"] = retained_campaigns + [
        campaign(correction, [method])
    ]
    merged["server_catalog"] = correction["server_catalog"]
    merged["summary"][method] = correction["summary"][method]
    merged["runs"][method] = correction["runs"][method]
    merged["workload"]["method_params"][method] = correction["workload"][
        "method_params"
    ][method]
    merged["warmups"] = [
        row for row in base["warmups"] if row["method"] != method
    ] + list(correction["warmups"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"merged {method} campaign with {len(merged['runs'][method])} measured runs "
        f"into {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
