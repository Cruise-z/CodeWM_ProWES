#!/usr/bin/env python3
"""Package the paper report and table/figure deliverables with integrity hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[3]
SECRET_PATTERN = re.compile(rb"sk-[A-Za-z0-9_-]{20,}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace existing archives at the fixed release paths",
    )
    return parser.parse_args()


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_under(path: Path):
    if path.is_file():
        return [path]
    return sorted(
        candidate for candidate in path.rglob("*")
        if candidate.is_file() and "__pycache__" not in candidate.parts and candidate.suffix != ".pyc"
    )


def validate_no_secrets(paths):
    for path in paths:
        if SECRET_PATTERN.search(path.read_bytes()):
            raise RuntimeError(f"possible API key in package input: {path}")


def create_archive(path: Path, inputs, force: bool = False):
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {path}")
    paths = []
    for item in inputs:
        paths.extend(files_under(item))
    paths = sorted(set(paths), key=lambda item: str(item.relative_to(ROOT)))
    validate_no_secrets(paths)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()
    with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in paths:
            archive.write(item, str(item.relative_to(ROOT)))
    with zipfile.ZipFile(temporary_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"archive integrity failure at {bad}")
    os.replace(temporary_path, path)
    return {
        "path": str(path),
        "files": len(paths),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main():
    args = parse_args()
    report_archive = WORKSPACE / "RQ2_Paper_Report_20260916.zip"
    table_archive = WORKSPACE / "RQ2_Tables_Figures_20260916.zip"
    report_inputs = [
        ROOT / "deliverables/01_paper_report",
        ROOT / "outputs/fresh/final",
        ROOT / "outputs/fresh/epr_rule/final",
        ROOT / "outputs/fresh/llm_pilot_minimal/final",
        ROOT / "outputs/fresh/llm_full_1000/protocol.json",
        ROOT / "outputs/fresh/llm_full_1000/detection_manifest.json",
        ROOT / "outputs/fresh/llm_full_1000/main",
        ROOT / "outputs/fresh/llm_full_1000/main_eval",
        ROOT / "outputs/fresh/llm_full_1000/metrics",
        ROOT / "outputs/fresh/llm_full_1000/logs",
        ROOT / "outputs/fresh/llm_input/cohort_manifest.json",
        ROOT / "outputs/fresh/llm_input/cohort_build.log",
        ROOT / "rq2_revision/prompts",
        ROOT / "rq2_revision/rules/hard_rules.json",
    ]
    table_inputs = [
        ROOT / "deliverables/03_tables_figures",
        ROOT / "plot_rq2_results.py",
        ROOT / "deliverables/01_paper_report/rq2_complete_results.json",
    ]
    for path in report_inputs + table_inputs:
        if not path.exists():
            raise FileNotFoundError(path)
    packages = [
        create_archive(report_archive, report_inputs, force=args.force),
        create_archive(table_archive, table_inputs, force=args.force),
    ]
    source_archive = WORKSPACE / "RQ2_Source_Artifact_20260916.zip"
    if not source_archive.exists():
        raise FileNotFoundError("run build_source_artifact.py before packaging")
    packages.append({
        "path": str(source_archive),
        "bytes": source_archive.stat().st_size,
        "sha256": sha256_file(source_archive),
    })
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "packages": packages,
    }
    manifest_path = ROOT / "deliverables/PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
