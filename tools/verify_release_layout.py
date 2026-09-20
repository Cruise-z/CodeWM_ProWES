#!/usr/bin/env python3
"""Verify the final reviewer-facing Artifact layout."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RQS = ("RQ1", "RQ2", "RQ3")

REQUIRED = (
    "paper_reproduction/tables/RQ1",
    "paper_reproduction/tables/RQ2",
    "paper_reproduction/tables/RQ3",
    "paper_reproduction/figures/RQ1",
    "paper_reproduction/figures/RQ2",
    "paper_reproduction/figures/RQ3",
    "results/RQ1/05_baseline_qualification",
    "results/RQ1/07_strength_sweep",
    "results/RQ1/08_detectability",
    "results/RQ2/01_datasets",
    "results/RQ2/02_training",
    "results/RQ2/03_rule_attacks",
    "results/RQ2/04_mbxp_validation",
    "results/RQ2/05_llm_rag",
    "results/RQ2/06_llm_rag_mbxp_pilot",
    "results/RQ2/07_predictions",
    "results/RQ2/08_statistics",
    "RQ2/source/pipeline",
)

FORBIDDEN = (
    "paper_reproduction/tables/rq1",
    "paper_reproduction/tables/rq2",
    "paper_reproduction/tables/rq3",
    "paper_reproduction/figures/rq1",
    "paper_reproduction/figures/rq2",
    "paper_reproduction/figures/rq3",
    "results/RQ1/Applicability",
    "results/RQ1/Detectability",
    "results/RQ1/Applicability.zip",
    "results/RQ1/Detectability.zip",
    "results/RQ1/ARCHIVE_PROVENANCE.json",
    "results/RQ1/07_strength_sweep/derived/figures",
    "results/RQ2/08_statistics/paper_outputs",
    "results/RQ2/06_llm_rag_mbxp_pilot/main",
    "results/RQ2/06_llm_rag_mbxp_pilot/main_eval",
    "results/RQ2/06_llm_rag_mbxp_pilot/metrics",
    "RQ2/source/rq2_revision",
    "RQ2/source/CHANGELOG_REVISION.md",
    "RQ2/source/README_REVISION.md",
    "RQ2/source/TEST_REPORT.md",
    "RQ3/TIMING_DESIGN_AUDIT.md",
    "RQ3/SWEET_TIMING_CORRECTION.md",
    "RQ3/01_timing_harness/merge_logits_bias_rerun.py",
)


def main() -> None:
    missing = [relative for relative in REQUIRED if not (ROOT / relative).exists()]
    forbidden = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]

    misplaced: list[str] = []
    for category in ("tables", "figures"):
        base = ROOT / "paper_reproduction" / category
        children = {path.name for path in base.iterdir() if path.is_dir()}
        if children != set(RQS):
            misplaced.append(
                f"paper_reproduction/{category} has directories {sorted(children)}"
            )
        misplaced.extend(
            str(path.relative_to(ROOT))
            for path in base.iterdir()
            if path.is_file()
        )

    if missing or forbidden or misplaced:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if forbidden:
            details.append("forbidden: " + ", ".join(forbidden))
        if misplaced:
            details.append("misplaced: " + ", ".join(misplaced))
        raise SystemExit("release layout verification failed\n" + "\n".join(details))

    counts = {
        category: {
            rq: sum(path.is_file() for path in (ROOT / "paper_reproduction" / category / rq).rglob("*"))
            for rq in RQS
        }
        for category in ("tables", "figures")
    }
    print(f"PASS: final release layout verified; output counts={counts}")


if __name__ == "__main__":
    main()
