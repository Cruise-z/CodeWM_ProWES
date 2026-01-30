#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def dtresults_has_any_target(dtresults_dir: Path) -> bool:
    """
    判断 DTResults/ 及其子目录中是否存在名为 'target' 的目录（递归）。
    只要存在任意一个 DTResults/**/target/，返回 True。
    """
    for p in dtresults_dir.rglob("target"):
        if p.is_dir():
            return True
    return False


def file_contains_keyword(path: Path, keyword: str) -> bool:
    """
    判断文件内容是否包含关键字（只要出现一次就返回 True）。
    使用 errors='ignore' 以兼容非 UTF-8/乱码日志。
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if keyword in line:
                return True
    return False


def count_error_files(root_dir: Path, keyword: str = "COMPILATION ERROR") -> int:
    """
    遍历 root_dir 下所有子目录：
      - 若存在 DTResults/
      - 且 DTResults/**/target 不存在
      - 且 DTResults/** 下存在 full_*.log
    则对这些 full_*.log 中“包含 keyword 的文件”计数（按文件数，不按出现次数）。
    """
    total_files = 0

    for child in root_dir.iterdir():
        if not child.is_dir():
            continue

        dtresults_dir = child / "DTResults"
        if not dtresults_dir.is_dir():
            continue

        # 条件 1：DTResults 子树中不能有任何 target/
        if dtresults_has_any_target(dtresults_dir):
            continue

        # 条件 2：DTResults 子树中要有 full_*.log
        log_files = list(dtresults_dir.rglob("full_*.log"))
        if not log_files:
            continue

        # 对满足条件的 log：统计“包含关键字”的文件数
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
