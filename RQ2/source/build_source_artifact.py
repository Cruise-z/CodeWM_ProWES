#!/usr/bin/env python3
"""Create a credential-free RQ2 implementation artifact from an explicit source allowlist."""

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
OUTPUT_DIR = ROOT / "deliverables/02_source_artifact"
ARCHIVE = ROOT.parents[3] / "RQ2_Source_Artifact_20260916.zip"
ALLOWED_SUFFIXES = {".py", ".sh", ".md", ".txt", ".json", ".toml", ".java"}
EXCLUDED_PARTS = {
    "__pycache__", ".pytest_cache", ".git", ".deps", "datasets", "ckpts", "logs",
    "run_logs", "results", "testResult", "outputs", "node_modules",
}
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace the existing archive at the fixed release path",
    )
    return parser.parse_args()


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def eligible(path: Path):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name.startswith(".") or path.suffix not in ALLOWED_SUFFIXES:
        return False
    if path.name.lower().endswith(("env", "credentials.json", "config.ini")):
        return False
    return True


def collect_sources():
    paths = []
    for name in (
        "README_REVISION.md", "CHANGELOG_REVISION.md", "TEST_REPORT.md", "LLM_RAG_PROMPT.md",
        "requirements_revision.txt", "build_final_report.py", "build_fresh_report.py",
        "build_full_epr_report.py", "build_llm_pilot_report.py", "merge_mbxp_epr_chunks.py",
        "prepare_fresh_llm_cohorts.py", "run_llm_full_1000.py", "run_llm_full_detection.py",
        "build_rq2_deliverables.py", "build_source_artifact.py", "plot_rq2_results.py",
        "package_rq2_deliverables.py",
    ):
        path = ROOT / name
        if path.exists():
            paths.append(path)
    for directory in ("rq2_revision", "tests", "project/srcMarker/SrcMarker", "training/SrcMarker_fresh", "cStyleLang"):
        for path in (ROOT / directory).rglob("*"):
            if path.is_file() and eligible(path):
                paths.append(path)
    # Training provenance is data-like JSON under ckpts; include only manifests/history, never weights.
    for name in ("run_manifest.json", "training_history.json"):
        paths.extend((ROOT / "training/SrcMarker_fresh/ckpts").glob(f"fresh_rq2_*/{name}"))
    return sorted(set(paths), key=lambda path: str(path.relative_to(ROOT)))


def main():
    args = parse_args()
    sources = collect_sources()
    if not sources:
        raise RuntimeError("source allowlist is empty")
    for path in sources:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET_PATTERN.search(text):
            raise RuntimeError(f"possible API key in source artifact input: {path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    readme = """# RQ2 source artifact

This credential-free archive contains the implementation required to train the two methods,
generate clean watermarked code, run deterministic rule attacks, execute the LLM-RAG attack,
validate transformations on MBXP, extract watermarks, compute paired metrics and confidence
intervals, and regenerate tables/figures.

The archive intentionally excludes datasets, API credentials, raw model checkpoints, runtime
logs, caches, and generated attack outputs. Checkpoint SHA-256 values and training provenance are
recorded in the delivered experiment report; `training_history.json` and `run_manifest.json` are
included. Reproduction requires obtaining the public datasets and supplying a local mode-600
credential file for the configured OpenAI-compatible provider.

Start with `README_REVISION.md`. Run unit tests with:

```bash
PYTHONPATH=.deps pytest -q
```

The complete source inventory and SHA-256 hashes are stored in `SOURCE_MANIFEST.json`.
"""
    readme_path = OUTPUT_DIR / "README_ARTIFACT.md"
    readme_path.write_text(readme, encoding="utf-8")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "credential_files_included": False,
        "model_checkpoints_included": False,
        "source_files": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sources
        ],
    }
    manifest_path = OUTPUT_DIR / "SOURCE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if ARCHIVE.exists() and not args.force:
        raise FileExistsError(f"refusing to overwrite {ARCHIVE}")
    temporary_archive = ARCHIVE.with_suffix(ARCHIVE.suffix + ".tmp")
    if temporary_archive.exists():
        temporary_archive.unlink()
    with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(readme_path, "README_ARTIFACT.md")
        archive.write(manifest_path, "SOURCE_MANIFEST.json")
        for path in sources:
            archive.write(path, str(path.relative_to(ROOT)))
    with zipfile.ZipFile(temporary_archive) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"archive integrity failure at {bad}")
    os.replace(temporary_archive, ARCHIVE)
    print(json.dumps({
        "archive": str(ARCHIVE),
        "source_files": len(sources),
        "bytes": ARCHIVE.stat().st_size,
        "sha256": sha256_file(ARCHIVE),
    }, indent=2))


if __name__ == "__main__":
    main()
