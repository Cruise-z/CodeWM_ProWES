"""Source snapshotting, diversity metrics, and language helpers."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

def get_programming_language(repoPath: Path) -> str:
    prd_dir = repoPath / "docs" / "prd"

    # Find files matching <number>.json
    candidates = [p for p in prd_dir.glob("*.json") if p.is_file() and p.stem.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"No <number>.json file found under {prd_dir}.")

    # If multiple exist, pick the one with the largest number (usually a timestamp)
    target = max(candidates, key=lambda p: int(p.stem))

    # Read the first non-empty JSONL line and extract the field
    with target.open("r", encoding="utf-8-sig") as f:
        for idx, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"{target} line {idx} is not valid JSON: {e}") from e

            val = obj.get("Programming Language")
            if val is None:
                raise KeyError(f"{target} line {idx} is missing the 'Programming Language' field.")
            return re.sub(r"\d+", "", str(val)).replace("+", "p").replace(".", "")

    raise ValueError(f"{target} is empty or contains only blank lines.")

def remove_leading_h2_line(codeFilePath: Path, LANG: Optional[str] = None) -> list[Path]:
    """
    Remove one leading Markdown H2-style line from generated source files.

    If LANG is provided, only files matching the language postfix are touched,
    e.g. *.java for Java. This keeps snapshot comparison and cleanup aligned.
    If LANG is None, it falls back to scanning all files under codeFilePath.

    Note: if the leading '##...' line does NOT end with a newline, it will NOT be removed.
    """
    _PATTERN = re.compile(r"\A##[^\r\n]*\r?\n")
    modified: list[Path] = []
    encodings_try = ("utf-8", "utf-8-sig", "gb18030")  # common in CN environments; avoid latin-1 to reduce false edits

    root = Path(codeFilePath)
    if LANG is None:
        iterator = root.rglob("*")
    else:
        postfix = get_postfix(LANG)
        iterator = root.rglob(f"*.{postfix}")

    for p in iterator:
        if not p.is_file() or p.is_symlink():
            continue

        # Rough binary detection: skip if NUL byte exists
        try:
            with p.open("rb") as fb:
                head = fb.read(4096)
                if b"\x00" in head:
                    continue
                fb.seek(0)
                raw = fb.read()
        except Exception:
            continue  # skip unreadable files

        # Try decoding with multiple encodings
        text = None
        used_encoding = None
        for enc in encodings_try:
            try:
                text = raw.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            continue  # treat as non-text/unknown encoding

        m = _PATTERN.match(text)
        if not m:
            continue  # no match at file start

        new_text = text[m.end():]

        # Write back; preserve permissions and (if any) BOM: utf-8-sig writeback keeps BOM
        try:
            p.write_text(new_text, encoding=used_encoding)
            modified.append(p)
        except Exception:
            # Ignore files that fail to write back
            continue

    return modified

def get_postfix(LANG: str) -> str:
    LANG = LANG.lower()
    if LANG == "python":
        return "py"
    elif LANG == "java":
        return "java"
    # elif LANG == "javascript":
    #     return "js"
    elif LANG == "c++" or LANG == "cpp":
        return "cpp"
    else:
        raise ValueError(f"Unsupported programming language: {LANG}")

def snapshot_code_files(
    codeFilePath: Path,
    LANG: str,
) -> dict[str, str]:
    """
    Recursively snapshot generated source files under codeFilePath.

    The returned dict maps:
        relative/path/to/File.java -> sha256(content)

    For Java projects, codeFilePath may contain multiple .java files under
    src/main/java and src/test/java. If any Java file is added, removed, or
    changed, the snapshot will differ.
    """
    postfix = get_postfix(LANG)
    root = Path(codeFilePath).resolve()

    if not root.is_dir():
        raise NotADirectoryError(f"codeFilePath is not a directory: {root}")

    snapshot: dict[str, str] = {}

    for p in sorted(root.rglob(f"*.{postfix}"), key=lambda x: str(x)):
        if not p.is_file() or p.is_symlink():
            continue

        rel = p.relative_to(root).as_posix()
        content = p.read_bytes()
        snapshot[rel] = hashlib.sha256(content).hexdigest()

    if not snapshot:
        raise FileNotFoundError(f"Could not find any *.{postfix} files under {root}")

    return snapshot


def hash_code_snapshot(snapshot: dict[str, str]) -> str:
    """Hash the ordered source-path/content-digest manifest."""
    digest = hashlib.sha256(b"codewm-source-snapshot-v1\0")
    for relative_path, content_digest in sorted(snapshot.items()):
        path_bytes = relative_path.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(8, byteorder="big"))
        digest.update(path_bytes)
        digest.update(bytes.fromhex(content_digest))
    return digest.hexdigest()


def calculate_diversity_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [
        record
        for record in records
        if record.get("generation_succeeded") and record.get("source_snapshot_hash")
    ]
    unique_hashes = {record["source_snapshot_hash"] for record in complete}

    longest_length = 0
    longest_start: Optional[str] = None
    longest_end: Optional[str] = None
    run_start = 0
    for index in range(1, len(complete) + 1):
        run_ended = (
            index == len(complete)
            or complete[index]["source_snapshot_hash"]
            != complete[run_start]["source_snapshot_hash"]
        )
        if not run_ended:
            continue
        run_length = index - run_start
        if run_length > longest_length:
            longest_length = run_length
            longest_start = complete[run_start]["wm_strength"]
            longest_end = complete[index - 1]["wm_strength"]
        run_start = index

    final_plateau_length = 0
    final_plateau_start: Optional[str] = None
    if complete:
        final_index = len(complete) - 1
        final_hash = complete[final_index]["source_snapshot_hash"]
        final_start_index = final_index
        while (
            final_start_index > 0
            and complete[final_start_index - 1]["source_snapshot_hash"] == final_hash
        ):
            final_start_index -= 1
        final_plateau_length = len(complete) - final_start_index
        if final_plateau_length > 1:
            final_plateau_start = complete[final_start_index]["wm_strength"]

    build_valid_labels = {
        "[Test Error]",
        "[Packaging Error]",
        "[Runtime Error]",
        "[Pass]",
    }
    build_evaluated = [record for record in records if record.get("tested")]
    build_valid = [
        record for record in records if record.get("result_label") in build_valid_labels
    ]
    unique_build_valid = {
        record["source_snapshot_hash"]
        for record in build_valid
        if record.get("source_snapshot_hash")
    }
    complete_count = len(complete)
    build_evaluated_count = len(build_evaluated)
    return {
        "strength_configurations_attempted": len(records),
        "complete_snapshots_generated": complete_count,
        "unique_source_snapshot_count": len(unique_hashes),
        "unique_generation_ratio": (
            len(unique_hashes) / complete_count if complete_count else None
        ),
        "unchanged_snapshot_skip_count": sum(
            bool(record.get("build_skipped_due_to_unchanged_snapshot"))
            for record in records
        ),
        "already_seen_snapshot_count": sum(
            bool(record.get("already_seen_snapshot")) for record in records
        ),
        "longest_consecutive_identical_snapshot_plateau": {
            "length": longest_length,
            "start_strength": longest_start,
            "end_strength": longest_end,
        },
        "final_identical_snapshot_plateau": {
            "length": final_plateau_length,
            "start_strength": final_plateau_start,
            "end_strength": complete[-1]["wm_strength"] if complete else None,
        },
        "syntactically_valid_outputs": None,
        "build_evaluated_count": build_evaluated_count,
        "build_valid_outputs": len(build_valid),
        "build_success_rate": (
            len(build_valid) / build_evaluated_count if build_evaluated_count else None
        ),
        "unique_build_valid_snapshot_count": len(unique_build_valid),
        "full_evaluation_pass_count": sum(
            record.get("result_label") == "[Pass]" for record in records
        ),
    }


def strength_values(wmS_config: Optional[dict[str, Any]]) -> tuple[Decimal, ...]:
    if wmS_config is not None and "values" in wmS_config:
        values = tuple(Decimal(str(value)) for value in wmS_config["values"])
        if not values:
            raise ValueError("wmS_config values must not be empty")
        return values

    config = wmS_config or {"start": "0.0", "step": "0.1", "end": "15.0"}
    current = Decimal(str(config["start"]))
    step = Decimal(str(config["step"]))
    end = Decimal(str(config["end"]))
    if step <= 0:
        raise ValueError("wmS_config step must be positive")
    values = []
    while current <= end:
        values.append(current)
        current += step
    return tuple(values)


def describe_snapshot_diff(
    prev_snapshot: dict[str, str],
    curr_snapshot: dict[str, str],
) -> str:
    """
    Return a compact human-readable summary of source snapshot differences.
    """
    prev_files = set(prev_snapshot)
    curr_files = set(curr_snapshot)

    added = sorted(curr_files - prev_files)
    removed = sorted(prev_files - curr_files)
    changed = sorted(
        p for p in (prev_files & curr_files)
        if prev_snapshot[p] != curr_snapshot[p]
    )

    parts = []
    if added:
        parts.append(f"added={added}")
    if removed:
        parts.append(f"removed={removed}")
    if changed:
        parts.append(f"changed={changed}")

    return "; ".join(parts) if parts else "no source changes"
