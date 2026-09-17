#!/usr/bin/env python3
"""Stream and cross-check the formal RQ2 evidence released with the artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "RQ2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"{path}:{line_number}: {error}") from error


def checkpoint_audit() -> dict:
    summary = json.loads(
        (RESULTS / "08_statistics/fresh/rq2_fresh_results.json").read_text(encoding="utf-8")
    )
    expected = {
        (row["method"].lower(), row["dataset"]): row["checkpoint_sha256"]
        for row in summary["training_and_clean"]
    }
    dataset_keys = {
        "GitHub-C": "github_c_funcs",
        "GitHub-Java": "github_java_funcs",
        "CSN-JavaScript": "csn_js",
        "CSN-Java": "csn_java",
    }
    observed = {}
    for directory in sorted((RESULTS / "02_training/checkpoints").glob("fresh_rq2_*")):
        manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
        key = (manifest["method"], manifest["dataset"])
        digest = sha256(directory / "models_best.pt")
        paper_key = (manifest["method"], next(
            label for label, value in dataset_keys.items() if value == manifest["dataset"]
        ))
        if digest != expected[paper_key]:
            raise AssertionError(f"checkpoint hash mismatch: {directory}")
        observed["/".join(key)] = digest
    if len(observed) != 8:
        raise AssertionError(f"expected 8 checkpoints, found {len(observed)}")
    return {"count": len(observed), "sha256": observed}


def mbxp_audit() -> dict:
    paths = sorted((RESULTS / "04_mbxp_validation").glob("mb*_rule_*.jsonl"))
    if len(paths) != 12:
        raise AssertionError(f"expected 12 MBXP cells, found {len(paths)}")
    valid_changed = post_pass = rows = 0
    by_cell = {}
    for path in paths:
        cell_valid = cell_pass = cell_rows = 0
        for row in json_rows(path):
            cell_rows += 1
            if row.get("changed") and row.get("syntax_valid"):
                cell_valid += 1
                cell_pass += int(bool(row.get("post_pass")))
        rows += cell_rows
        valid_changed += cell_valid
        post_pass += cell_pass
        by_cell[path.stem] = {
            "rows": cell_rows,
            "changed_syntax_valid": cell_valid,
            "post_pass": cell_pass,
        }
    if (valid_changed, post_pass) != (9572, 9444):
        raise AssertionError(
            f"MBXP matrix mismatch: valid={valid_changed}, post_pass={post_pass}"
        )
    return {
        "cells": len(paths),
        "rows": rows,
        "changed_syntax_valid": valid_changed,
        "post_pass": post_pass,
        "weighted_EPR": post_pass / valid_changed,
        "by_cell": by_cell,
    }


def llm_audit() -> dict:
    main_paths = sorted((RESULTS / "05_llm_rag/main").glob("*.jsonl"))
    eval_paths = sorted((RESULTS / "05_llm_rag/main_eval").glob("*.jsonl"))
    if len(main_paths) != 8 or len(eval_paths) != 8:
        raise AssertionError("expected 8 LLM generation and 8 LLM evaluation cells")
    statuses = Counter()
    models = Counter()
    usage_rows = 0
    rows = 0
    for path in main_paths:
        for row in json_rows(path):
            rows += 1
            metadata = row.get("attack_meta", {})
            statuses[metadata.get("status", "missing")] += 1
            response = metadata.get("provider_response") or {}
            if response.get("response_model"):
                models[response["response_model"]] += 1
            usage_rows += int(bool(response.get("usage")))
    expected = Counter({"valid_attack": 972, "no_op": 23, "syntax_invalid": 5})
    if rows != 1000 or statuses != expected:
        raise AssertionError(f"LLM generation mismatch: rows={rows}, statuses={statuses}")
    predicted = 0
    for path in eval_paths:
        for row in json_rows(path):
            if row.get("attack_meta", {}).get("status") == "valid_attack":
                predicted += int(isinstance(row.get("obfus_extract"), list))
    if predicted != 972:
        raise AssertionError(f"expected 972 attacked predictions, found {predicted}")
    if models != Counter({"gpt-5-2025-08-07": 1000}):
        raise AssertionError(f"unexpected returned model snapshots: {models}")
    return {
        "rows": rows,
        "statuses": dict(statuses),
        "rows_with_usage": usage_rows,
        "returned_models": dict(models),
        "attacked_predictions": predicted,
    }


def pilot_audit() -> dict:
    paths = sorted((RESULTS / "06_llm_rag_mbxp_pilot/epr").glob("*.jsonl"))
    if len(paths) != 3:
        raise AssertionError(f"expected 3 pilot datasets, found {len(paths)}")
    rows = valid = post_pass = 0
    for path in paths:
        for row in json_rows(path):
            rows += 1
            is_valid = bool(row.get("changed") and row.get("syntax_valid"))
            valid += int(is_valid)
            post_pass += int(is_valid and bool(row.get("post_pass")))
    if (rows, valid, post_pass) != (45, 45, 45):
        raise AssertionError(f"pilot mismatch: rows={rows}, valid={valid}, pass={post_pass}")
    return {"rows": rows, "changed_syntax_valid": valid, "post_pass": post_pass}


def rule_audit() -> dict:
    raw = sorted((RESULTS / "03_rule_attacks/raw").glob("*.jsonl"))
    evaluated = sorted((RESULTS / "03_rule_attacks/evaluated").glob("*.jsonl"))
    if len(raw) != 32 or len(evaluated) != 32:
        raise AssertionError(f"expected 32 rule cells, found raw={len(raw)}, eval={len(evaluated)}")
    row_count = prediction_count = 0
    status_counts = Counter()
    for path in evaluated:
        for row in json_rows(path):
            row_count += 1
            status_counts[row.get("attack_meta", {}).get("status", "missing")] += 1
            prediction_count += int(isinstance(row.get("obfus_extract"), list))
    if prediction_count == 0:
        raise AssertionError("no rule-attack predictions found")
    return {
        "cells": len(evaluated),
        "rows": row_count,
        "predictions": prediction_count,
        "status_counts": dict(status_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = {
        "checkpoints": checkpoint_audit(),
        "rule_robustness": rule_audit(),
        "mbxp_rule_validation": mbxp_audit(),
        "llm_rag": llm_audit(),
        "llm_rag_mbxp_pilot": pilot_audit(),
        "status": "PASS",
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
