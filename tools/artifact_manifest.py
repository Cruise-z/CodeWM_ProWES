#!/usr/bin/env python3
"""Generate or verify the artifact inventory and SHA-256 ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL = {"ARTIFACT_MANIFEST.csv", "ARTIFACT_MANIFEST.json", "SHA256SUMS.txt"}


def files(include_control: bool = False):
    for path in sorted(ROOT.rglob("*")):
        if (not path.is_file() and not path.is_symlink()) or ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if not include_control and relative in CONTROL:
            continue
        yield path, relative


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(path.readlink().as_posix().encode("utf-8"))
        return digest.hexdigest()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative: str) -> tuple[str, str, str, str]:
    parts = relative.split("/")
    rq = next((part for part in parts if part in {"RQ1", "RQ2", "RQ3"}), "Common")
    if relative.startswith("results/"):
        role = "result"
    elif relative.startswith(("RQ1/", "RQ2/", "RQ3/")):
        role = "source-or-input"
    else:
        role = "metadata-or-reproduction"
    if parts[0] == "results" and len(parts) > 2:
        stage = parts[2]
    elif parts[0] in {"RQ1", "RQ2", "RQ3"} and len(parts) > 1:
        stage = parts[1]
    else:
        stage = parts[0]
    mapping = ""
    if "05_baseline_qualification" in relative or "tables/rq1/baseline" in relative:
        mapping = (
            "RQ1 baseline qualification; 88 attempts, 42 accepted repositories, "
            "42 verified replays"
        )
    elif (
        "results/RQ1/Applicability" in relative
        or "tables/rq1/applicability" in relative
        or "figures/rq1/applicability" in relative
    ):
        mapping = "RQ1 applicability; medium-project strength-sweep derived outputs"
    elif "results/RQ1/Detectability" in relative or "tables/rq1/detectability" in relative:
        mapping = "RQ1 detectability; per-strength AUROC and FNR@5% FPR"
    elif "03_tables_figures/tables" in relative:
        mapping = "Main Tables VIII-IX; Supplement Tables VIII-XVII"
    elif "03_tables_figures/figures" in relative:
        mapping = "Main Figures 4-5; RQ2 supplemental figures"
    elif "04_mbxp_validation" in relative:
        mapping = "Main Table VIII; Supplement Table IX"
    elif "05_llm_rag" in relative:
        mapping = "Main Table IX and Figure 5; Supplement Tables XIII-XVII"
    elif "03_rule_attacks" in relative:
        mapping = "Main Table VIII and Figures 4-5; Supplement Tables X-XII"
    elif rq == "RQ3" or "tables/rq3" in relative or "reproduce_rq3" in relative:
        mapping = "Main Table X; raw timing, token normalization, and training-cost evidence"
    return rq, stage, role, mapping


def write() -> None:
    rows = []
    payload_digests = {}
    for path, relative in files():
        rq, stage, role, mapping = classify(relative)
        digest = sha256(path)
        payload_digests[relative] = digest
        rows.append({
            "path": relative,
            "bytes": path.lstat().st_size,
            "sha256": digest,
            "rq": rq,
            "stage": stage,
            "role": role,
            "paper_mapping": mapping,
        })
    fields = ["path", "bytes", "sha256", "rq", "stage", "role", "paper_mapping"]
    with (ROOT / "ARTIFACT_MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (ROOT / "ARTIFACT_MANIFEST.json").write_text(
        json.dumps({"schema_version": 1, "files": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_rows = []
    for path, relative in files(include_control=True):
        if relative == "SHA256SUMS.txt":
            continue
        checksum_rows.append(f"{payload_digests.get(relative) or sha256(path)}  {relative}")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} manifest rows and {len(checksum_rows)} checksums")


def verify() -> None:
    ledger = ROOT / "SHA256SUMS.txt"
    if not ledger.is_file():
        raise SystemExit("SHA256SUMS.txt is missing; run with --write")
    checked = 0
    for line_number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        expected, separator, relative = line.partition("  ")
        if not separator:
            raise SystemExit(f"malformed checksum line {line_number}")
        path = ROOT / relative
        if not path.is_file() and not path.is_symlink():
            raise SystemExit(f"missing payload: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"checksum mismatch: {relative}")
        checked += 1
    print(f"verified {checked} files")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--verify", action="store_true")
    arguments = parser.parse_args()
    write() if arguments.write else verify()


if __name__ == "__main__":
    main()
