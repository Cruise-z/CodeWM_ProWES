#!/usr/bin/env python3
"""Reject CJK text in reviewer-facing, first-party release files.

Raw observations, generated architecture artifacts, and frozen upstream/vendor
snapshots are deliberately outside this check. See 00_common/LANGUAGE_AUDIT.md.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
TEXT_SUFFIXES = {
    ".csv", ".json", ".md", ".py", ".sh", ".txt", ".yaml", ".yml"
}

CHECK_TREES = [
    "00_common",
    "paper_reproduction",
    "tools",
    "RQ1/01_task_specs",
    "RQ1/04_docker",
    "RQ1/06_watermark_configs",
    "RQ1/07_strength_sweep",
    "RQ1/08_detectability",
    "RQ1/09_analysis",
    "RQ1/source/reproduct/model_runtime",
    "RQ1/source/DT/codeGen/modelDeploy/modelDeployer",
    "RQ2/01_datasets",
    "RQ2/02_training",
    "RQ2/03_rule_attacks",
    "RQ2/04_mbxp_validation",
    "RQ2/05_llm_rag",
    "RQ2/06_llm_rag_mbxp_pilot",
    "RQ2/07_predictions",
    "RQ2/08_statistics",
    "RQ2/source/rq2_revision",
    "RQ2/source/cStyleLang",
    "RQ2/source/project",
    "RQ2/source/tests",
    "RQ2/source/training/SrcMarker_fresh",
    "RQ3",
]

CHECK_FILES = [
    "README.md",
    "ARTIFACT_COMPLETENESS.md",
    "THIRD_PARTY_NOTICES.md",
    "RQ1/README.md",
    "RQ1/02_prompts/README.md",
    "RQ1/02_prompts/build_prompt_bundle.py",
    "RQ1/02_prompts/bundle_summary.json",
    "RQ1/02_prompts/stage0/README.md",
    "RQ1/02_prompts/stage0/prompt_manifest.csv",
    "RQ1/02_prompts/stage0/prompt_manifest.json",
    "RQ1/02_prompts/stage1/README.md",
    "RQ1/02_prompts/stage1/prompt_manifest.csv",
    "RQ1/02_prompts/stage1/prompt_manifest.json",
    "RQ1/02_prompts/stage1/system_prompt.txt",
    "RQ1/source/DT/codeGen/README.md",
    "RQ1/source/DT/codeGen/batchConfig.multi.example.json",
    "RQ1/source/reproduct/REPRODUCIBILITY.md",
    "RQ1/source/reproduct/campaign.py",
    "RQ2/README.md",
    "RQ2/source/README_REVISION.md",
    "RQ2/source/CHANGELOG_REVISION.md",
    "RQ2/source/build_final_report.py",
    "RQ2/source/build_fresh_report.py",
    "RQ2/source/build_full_epr_report.py",
    "RQ2/source/build_llm_pilot_report.py",
    "RQ2/source/build_rq2_deliverables.py",
    "results/RQ1/README.md",
    "results/RQ1/05_baseline_qualification/README.md",
    "results/RQ1/05_baseline_qualification/PROVENANCE.json",
    "RQ1/05_baseline_qualification/README.md",
]


def candidates() -> list[Path]:
    paths = {ROOT / relative for relative in CHECK_FILES}
    for relative in CHECK_TREES:
        base = ROOT / relative
        if not base.exists():
            raise SystemExit(f"language-audit path is missing: {relative}")
        for path in base.rglob("*"):
            if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name == "Dockerfile"):
                paths.add(path)
    return sorted(paths)


def main() -> None:
    violations: list[str] = []
    checked = 0
    for path in candidates():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        checked += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            if CJK.search(line):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {line.strip()[:160]}"
                )
    if violations:
        raise SystemExit(
            "CJK text found in reviewer-facing release files:\n" + "\n".join(violations)
        )
    print(f"PASS: {checked} reviewer-facing first-party text files are English-only")
    print("Excluded immutable evidence/vendor scopes are documented in 00_common/LANGUAGE_AUDIT.md")


if __name__ == "__main__":
    main()
