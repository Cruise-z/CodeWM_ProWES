#!/usr/bin/env python3
"""Rebuild the formal RQ2 tables and figures from the released result tree."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "RQ2" / "source"
RESULTS = ROOT / "results" / "RQ2"
OUTPUT = ROOT / "paper_reproduction"
TABLE_OUTPUT = OUTPUT / "tables" / "RQ2"
FIGURE_OUTPUT = OUTPUT / "figures" / "RQ2"


def link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source, target_is_directory=source.is_dir())


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="prowes-rq2-") as temporary:
        build_root = Path(temporary)
        shutil.copy2(SOURCE / "build_rq2_deliverables.py", build_root)
        shutil.copy2(SOURCE / "plot_rq2_results.py", build_root)
        link(SOURCE / "pipeline", build_root / "pipeline")
        link(RESULTS / "08_statistics" / "fresh", build_root / "inputs/training")
        link(
            RESULTS / "04_mbxp_validation" / "final",
            build_root / "inputs/rule_epr",
        )
        link(
            RESULTS / "06_llm_rag_mbxp_pilot" / "final",
            build_root / "inputs/llm_mbxp",
        )
        link(RESULTS / "05_llm_rag", build_root / "inputs/llm_rag")
        link(RESULTS / "05_llm_rag" / "cohort", build_root / "inputs/cohort")
        link(
            RESULTS / "02_training" / "checkpoints",
            build_root / "training/SrcMarker_fresh/ckpts",
        )

        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(SOURCE), environment.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        subprocess.run(
            [sys.executable, "build_rq2_deliverables.py"],
            cwd=build_root,
            env=environment,
            check=True,
        )

        generated = build_root / "deliverables/03_tables_figures"
        shutil.copytree(generated / "tables", TABLE_OUTPUT, dirs_exist_ok=True)
        shutil.copytree(generated / "figures", FIGURE_OUTPUT, dirs_exist_ok=True)
        shutil.copy2(
            build_root / "deliverables/01_paper_report/rq2_complete_results.json",
            TABLE_OUTPUT / "rq2_complete_results.json",
        )
    print(f"RQ2 tables: {TABLE_OUTPUT}")
    print(f"RQ2 figures: {FIGURE_OUTPUT}")


if __name__ == "__main__":
    main()
