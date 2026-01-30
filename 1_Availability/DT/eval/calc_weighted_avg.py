#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import ast
import json
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple


FOLDER_RE = re.compile(r"^(?P<prefix>.+)_(?P<int>\d+)\.(?P<frac>\d+)$")


def parse_strength_from_folder(folder_name: str) -> Optional[float]:
    """从形如 'tiny_calculator_0.2' 解析出 0.2"""
    m = FOLDER_RE.match(folder_name)
    if not m:
        return None
    return float(f"{m.group('int')}.{m.group('frac')}")


def safe_load_single_line_mapping(line: str) -> dict:
    """
    文件中往往是单引号 dict（非严格 JSON），因此先 json.loads，失败再 ast.literal_eval。
    """
    line = line.strip()
    if not line:
        raise ValueError("Empty line")
    try:
        return json.loads(line)
    except Exception:
        return ast.literal_eval(line)


def read_first_non_empty_line(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                return raw
    raise ValueError(f"No non-empty lines in {path}")


def find_project_dir(child_dir: Path) -> Path:
    """
    在 xxx_p.q 子目录下，找到项目目录 ./xxx （如 tiny_calculator）。
    约束：该目录应包含 *_wm_detRes.txt 文件。
    """
    candidates = [p for p in child_dir.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No subdirectories found under {child_dir}")

    # 以是否存在 *_wm_detRes.txt 作为判据
    scored = []
    for d in candidates:
        wm_files = list(d.glob("*_wm_detRes.txt"))
        if wm_files:
            scored.append(d)

    if len(scored) == 1:
        return scored[0]
    if len(scored) == 0:
        raise FileNotFoundError(f"Cannot find project dir under {child_dir}: no '*_wm_detRes.txt' found")
    raise RuntimeError(f"Ambiguous project dirs under {child_dir}: {scored}")


def find_target_detres_file(project_dir: Path, exclude_name: str = "pom_wm_detRes.txt") -> Path:
    """
    在 ./xxx 下只会有两个 *_wm_detRes.txt：
      - pom_wm_detRes.txt（排除）
      - 目标文件（保留）
    用“排除法”找到目标文件。
    """
    all_detres = sorted(project_dir.glob("*_wm_detRes.txt"))
    if not all_detres:
        raise FileNotFoundError(f"No '*_wm_detRes.txt' files found in {project_dir}")

    kept = [p for p in all_detres if p.name != exclude_name]
    if len(kept) == 1:
        return kept[0]

    # 这里将异常情况报清楚，便于你定位目录是否符合预期
    names = [p.name for p in all_detres]
    raise RuntimeError(
        f"Expected exactly 1 target '*_wm_detRes.txt' after excluding '{exclude_name}', "
        f"but got {len(kept)}. Files: {names}"
    )


def extract_metric_from_detres(detres_path: Path, field: str, strategy_key: Optional[str] = None) -> float:
    """
    从 detRes 文件（单行 dict/JSON）中提取指定字段 field（如 z_score）。
    - strategy_key=None：取外层 dict 的第一个 key
    - strategy_key=xxx：取指定策略 key
    """
    line = read_first_non_empty_line(detres_path)
    obj = safe_load_single_line_mapping(line)

    if not isinstance(obj, dict) or not obj:
        raise ValueError(f"Unexpected content in {detres_path}: not a non-empty dict")

    if strategy_key is None:
        k = next(iter(obj.keys()))
    else:
        if strategy_key not in obj:
            raise KeyError(f"strategy_key '{strategy_key}' not found in {detres_path}. Available: {list(obj.keys())}")
        k = strategy_key

    inner = obj[k]
    if not isinstance(inner, dict):
        raise ValueError(f"Unexpected inner object for key '{k}' in {detres_path}: not a dict")

    if field not in inner:
        raise KeyError(f"Field '{field}' not found under '{k}' in {detres_path}. Available: {list(inner.keys())}")

    v = inner[field]
    if not isinstance(v, (int, float)):
        raise ValueError(f"Field '{field}' is not numeric in {detres_path}: {v}")

    return float(v)


def read_baseline_metric(root_dir: Path, baseline_strength: float, field: str, strategy_key: Optional[str]) -> Tuple[Path, float]:
    """
    读取 p.q=baseline_strength 子目录的目标 detRes 文件中的 field 值（作为基线）。
    """
    baseline_dir = None
    for child in root_dir.iterdir():
        if not child.is_dir():
            continue
        s = parse_strength_from_folder(child.name)
        if s is not None and abs(s - baseline_strength) < 1e-12:
            baseline_dir = child
            break

    if baseline_dir is None:
        raise FileNotFoundError(f"Cannot find baseline folder for strength {baseline_strength} under {root_dir}")

    project_dir = find_project_dir(baseline_dir)
    detres_path = find_target_detres_file(project_dir)
    metric0 = extract_metric_from_detres(detres_path, field=field, strategy_key=strategy_key)
    return baseline_dir, metric0


def find_metrics_with_dtresults(root_dir: Path, field: str, strategy_key: Optional[str]) -> Dict[float, float]:
    """
    遍历 root_dir 下所有 xxx_p.q：
      - 只取含 DTResults/ 的
      - 用“排除法”在 ./xxx 下找到目标 *_wm_detRes.txt
      - 从中提取 field
    返回 {strength: metric}
    """
    out: Dict[float, float] = {}
    for child in root_dir.iterdir():
        if not child.is_dir():
            continue
        s = parse_strength_from_folder(child.name)
        if s is None:
            continue

        if not (child / "DTResults").is_dir():
            continue

        project_dir = find_project_dir(child)
        detres_path = find_target_detres_file(project_dir)
        metric = extract_metric_from_detres(detres_path, field=field, strategy_key=strategy_key)
        out[s] = metric

    return out


def weighted_average(values_by_strength: Dict[float, float]) -> float:
    """
    对 value_{p.q} 按权重 p.q 做加权平均：
      sum(p.q * value_{p.q}) / sum(p.q)
    """
    num = 0.0
    den = 0.0
    for s, v in values_by_strength.items():
        if s <= 0:
            continue
        num += s * v
        den += s
    if den == 0.0:
        raise ZeroDivisionError("Sum of weights is zero (no positive strengths?)")
    return num / den


def main():
    parser = argparse.ArgumentParser(
        description="Traverse watermark strength folders, extract metric from detRes (excluding pom), compute normalized values and weighted average."
    )
    parser.add_argument("root_dir", type=str, help="Root dir containing subfolders like xxx_0.0 ... xxx_15.0")
    parser.add_argument("--baseline", type=float, default=0.0, help="Baseline strength (default: 0.0)")
    parser.add_argument("--field", type=str, default="z_score", help="Metric field to extract (default: z_score)")
    parser.add_argument(
        "--strategy-key",
        type=str,
        default=None,
        help="Outer dict key (watermark strategy). Default: take the first key.",
    )
    parser.add_argument("--epsilon", type=float, default=1e-12, help="Guard for division by zero on |baseline|")
    parser.add_argument("--print-pairs", action="store_true", help="Print extracted strength->metric and strength->value")

    args = parser.parse_args()
    root_dir = Path(args.root_dir).expanduser().resolve()
    if not root_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_dir}")

    # baseline metric
    baseline_dir, m0 = read_baseline_metric(
        root_dir, baseline_strength=args.baseline, field=args.field, strategy_key=args.strategy_key
    )
    abs_m0 = abs(m0)
    if abs_m0 < args.epsilon:
        raise ZeroDivisionError(
            f"|baseline {args.field}| is too small: {m0}. Adjust --epsilon or choose a different baseline."
        )

    # metrics only for folders with DTResults
    metrics_dt = find_metrics_with_dtresults(root_dir, field=args.field, strategy_key=args.strategy_key)

    # compute normalized values (exclude baseline)
    values: Dict[float, float] = {}
    for s, m in metrics_dt.items():
        if abs(s - args.baseline) < 1e-12:
            continue
        values[s] = (m - m0) / abs_m0

    if args.print_pairs:
        print(f"Baseline folder: {baseline_dir}")
        print(f"{args.field}_{{{args.baseline}}} = {m0}")

        print(f"\nExtracted metrics (only folders WITH DTResults), field='{args.field}':")
        for s in sorted(metrics_dt.keys()):
            print(f"  {s:.1f} -> {metrics_dt[s]}")

        print("\nComputed values:")
        for s in sorted(values.keys()):
            print(f"  {s:.1f} -> {values[s]}")

    wavg = weighted_average(values)
    print(f"\nWeighted average of value_{{p.q}} weighted by p.q = {wavg}")


if __name__ == "__main__":
    main()
