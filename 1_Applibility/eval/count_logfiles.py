#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def dtresults_has_any_target(dtresults_dir: Path) -> bool:
    """
    Check whether DTResults/ or any of its subdirectories contains a directory named 'target'.
    Return True if any DTResults/**/target/ exists.
    """
    for p in dtresults_dir.rglob("target"):
        if p.is_dir():
            return True
    return False


def file_contains_keyword(path: Path, keyword: str) -> bool:
    """
    Check whether the file content contains the keyword (return True when it appears once).
    Use errors='ignore' to tolerate non-UTF-8 or corrupted logs.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if keyword in line:
                return True
    return False


def count_error_files(root_dir: Path, keyword: str = "COMPILATION ERROR") -> int:
    """
    Iterate over all subdirectories under root_dir:
      - if DTResults/ exists
      - and no DTResults/**/target exists
      - and full_*.log exists under DTResults/**
    count the number of full_*.log files that contain the keyword (count files, not occurrences).
    """
    total_files = 0

    for child in root_dir.iterdir():
        if not child.is_dir():
            continue

        dtresults_dir = child / "DTResults"
        if not dtresults_dir.is_dir():
            continue

        # Condition 1: no target/ directories under the DTResults subtree
        if dtresults_has_any_target(dtresults_dir):
            continue

        # Condition 2: there must be full_*.log files under the DTResults subtree
        log_files = list(dtresults_dir.rglob("full_*.log"))
        if not log_files:
            continue

        # For matching logs: count the files containing the keyword
        for log_path in log_files:
            try:
                if file_contains_keyword(log_path, keyword):
                    total_files += 1
            except Exception as e:
                print(f"[WARN] Failed to read {log_path}: {e}")

    return total_files


def main():
    parser = argparse.ArgumentParser(
        description="Count number of full_*.log files (under DTResults with NO target anywhere) that contain a given keyword."
    )
    parser.add_argument("root_dir", type=str, help="Root directory containing xxx_p.q subfolders")
    parser.add_argument(
        "--keyword",
        type=str,
        default="COMPILATION ERROR",
        help="Keyword to search in log files (default: 'COMPILATION ERROR')",
    )

    args = parser.parse_args()
    root_dir = Path(args.root_dir).expanduser().resolve()
    if not root_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_dir}")

    n = count_error_files(root_dir, keyword=args.keyword)
    print(f"Number of full_*.log files containing '{args.keyword}': {n}")


if __name__ == "__main__":
    main()
