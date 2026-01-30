#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
detection_eval.py

End-to-end detection evaluation for watermark logits processor, aligned with your codeGenBatch workflow:

(1) Generate in workspace:
    shellDelete(workspacePath) -> shellPaste(repo + storage) -> codeGen(project_name, xargs)
(2) Copy generated outputs to results folder (like codeGenBatch):
    results/<result_dir>/<project_name>_<strength>/
(3) Parse detRes from results folder:
    *_wm_detRes.txt (exclude pom_wm_detRes.txt)
(4) Compute:
    - TPR@FPR targets (default: 0.1%, 1%, 5%, 10%)
    - AUROC (overall pooled + per-strength)

Usage example:
python3 detection_eval.py \
  --project_name flappy_bird_java \
  --srcPath /home/zhaorz/project/CodeWM/srcRepo \
  --workspacePath /home/zhaorz/project/CodeWM/MetaGPT/workspace \
  --resPath /home/zhaorz/project/CodeWM/results \
  --method wllm \
  --seeds "range:100:120" \
  --strengths "0.0,0.5,1.0,2.0,3.0" \
  --baseline_strength 0.0 \
  --score_field z_score \
  --method_args_json '{"gamma":0.5,"z_threshold":4.0}' \
  --save_csv

Notes:
- This script depends on your existing `agentCodeGen.py` providing `codeGen(...)`.
- It DOES NOT run docker test (as you requested).
"""

# =====================================基础环境配置===================================== #
import os
import sys
import json
import re
import ast
import math
import time
import shutil
import argparse
import asyncio
import subprocess
from pathlib import Path
from typing import List, Any, Optional, Union, Dict, Tuple
from statistics import mean

# 1) 让官方 OpenAI 走代理（按你的梯子改端口）
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"] = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
os.environ["ALL_PROXY"] = os.environ.get("ALL_PROXY", os.environ["HTTPS_PROXY"])

# 2) 本地回环地址永远直连
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]
# =====================================基础环境配置===================================== #


# =======================
# (A) filesystem helpers (reuse from your scripts)
# =======================

def read_file(path: Union[str, Path], encoding: str = "utf-8", errors: str = "strict") -> str:
    """Read a text file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found or not a regular file: {p}")
    return p.read_text(encoding=encoding, errors=errors)


def find_file(root_abs: Path, suffix: str) -> Optional[Path]:
    """Find a file under root_abs (non-recursive) whose name endswith suffix."""
    root = Path(root_abs).resolve()
    if not root.is_dir():
        raise ValueError("root_abs must be an existing directory")

    for f in sorted(root.iterdir()):
        if f.is_file() and f.name.endswith(suffix):
            return f.resolve()
    return None


def shellPaste(sources, target):
    """
    Explorer/Finder-like merge copy:
      - dirs: merge into target/<dir>, overwrite files
      - files: copy into target, overwrite
    Windows: robocopy
    Linux/macOS: rsync preferred, otherwise cp -a
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)

    is_windows = os.name == "nt"
    has_rsync = shutil.which("rsync") is not None

    for src in map(Path, sources):
        if not src.exists():
            raise FileNotFoundError(f"{src} does not exist")

        if is_windows:
            if src.is_dir():
                dst = target / src.name
                cmd = [
                    "robocopy", str(src), str(dst),
                    "/E", "/R:0", "/W:0",
                    "/NFL", "/NDL", "/NP"
                ]
            else:
                cmd = [
                    "robocopy", str(src.parent), str(target), src.name,
                    "/R:0", "/W:0",
                    "/NFL", "/NDL", "/NP"
                ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode >= 8:
                raise RuntimeError(f"robocopy failed (code={res.returncode})\n{res.stdout}\n{res.stderr}")
        else:
            if src.is_dir():
                dst = target / src.name
                if has_rsync:
                    dst.mkdir(parents=True, exist_ok=True)
                    cmd = ["rsync", "-aAX", str(src) + "/", str(dst) + "/"]
                else:
                    cmd = ["cp", "-a", str(src), str(target)]
            else:
                if has_rsync:
                    cmd = ["rsync", "-aAX", str(src), str(target) + "/"]
                else:
                    cmd = ["cp", "-a", str(src), str(target)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"copy failed: {' '.join(cmd)}\n{res.stdout}\n{res.stderr}")


def shellDelete(dir_path: str, dry_run: bool = False) -> None:
    """
    Clear all contents under dir_path (do NOT delete dir_path itself).
    """
    p = Path(dir_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"path not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"not a dir: {p}")

    def _is_root_like(path: Path) -> bool:
        return (os.name == "nt" and path == Path(path.anchor)) or (os.name != "nt" and str(path) == "/")

    if _is_root_like(p):
        raise RuntimeError(f"refusing to wipe root path: {p}")

    if os.name == "nt":
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            raise RuntimeError("PowerShell not found.")

        script = (
            "$p=$args[0];"
            "if (-not (Test-Path -LiteralPath $p -PathType Container)) { throw 'Not a directory: ' + $p };"
            "if ($p -match '^[A-Za-z]:\\\\$') { throw 'Refusing to wipe drive root ' + $p };"
            "if ($args.Count -gt 1 -and $args[1] -eq 'dry') { "
            "  Get-ChildItem -LiteralPath $p -Force | Select-Object FullName | Out-Host; exit 0 "
            "} else { "
            "  Get-ChildItem -LiteralPath $p -Force | Remove-Item -Recurse -Force -ErrorAction Stop "
            "}"
        )
        argv = [pwsh, "-NoProfile", "-NonInteractive", "-Command", script, str(p)]
        if dry_run:
            argv.append("dry")
        res = subprocess.run(argv, text=True, capture_output=not dry_run)
        if res.returncode != 0:
            raise RuntimeError(f"PowerShell failed ({res.returncode}):\n{res.stderr or res.stdout}")
    else:
        if dry_run:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-print"]
        else:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1",
                   "-exec", "rm", "-rf", "--", "{}", "+"]
        subprocess.run(cmd, check=True)


def get_programming_language(repoPath: Path) -> str:
    """
    Reads docs/prd/<timestamp>.json (jsonl), fetches "Programming Language"
    """
    prd_dir = repoPath / "docs" / "prd"
    candidates = [p for p in prd_dir.glob("*.json") if p.is_file() and p.stem.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"cannot find <digits>.json under {prd_dir}")

    target = max(candidates, key=lambda p: int(p.stem))
    with target.open("r", encoding="utf-8-sig") as f:
        for idx, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            val = obj.get("Programming Language")
            if val is None:
                raise KeyError(f"{target} line {idx} missing 'Programming Language'")
            return val
    raise ValueError(f"{target} is empty")


def remove_leading_h2_line(codeFilePath: Path) -> List[Path]:
    """
    Remove leading "## ..." line for every text file under codeFilePath.
    """
    _PATTERN = re.compile(r"\A##[^\r\n]*\r?\n")
    modified: List[Path] = []
    encodings_try = ("utf-8", "utf-8-sig", "gb18030")

    for p in Path(codeFilePath).rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        try:
            raw = p.read_bytes()
            if b"\x00" in raw[:4096]:
                continue
        except Exception:
            continue

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
            continue

        m = _PATTERN.match(text)
        if not m:
            continue

        new_text = text[m.end():]
        try:
            p.write_text(new_text, encoding=used_encoding)
            modified.append(p)
        except Exception:
            continue
    return modified


# =======================
# (B) detRes parsing
# =======================

def read_first_non_empty_line(
    path: Path,
    *,
    max_wait_sec: float = 30.0,
    poll_interval_sec: float = 0.25,
) -> str:
    """
    Read first non-empty line with wait-retry.
    This is REQUIRED because *_wm_detRes.txt can be created before being filled.
    """
    deadline = time.time() + max_wait_sec
    last_size = None

    while True:
        if path.exists():
            try:
                st = path.stat()
                last_size = st.st_size
                if st.st_size > 0:
                    with path.open("r", encoding="utf-8", errors="ignore") as f:
                        for raw in f:
                            s = raw.strip()
                            if s:
                                return s
            except Exception:
                pass

        if time.time() >= deadline:
            raise ValueError(
                f"No non-empty lines in {path} after waiting {max_wait_sec:.1f}s "
                f"(last_size={last_size})"
            )
        time.sleep(poll_interval_sec)


def safe_load_mapping(line: str) -> dict:
    """
    detRes often is a single-line dict:
      - JSON: {"z_score": 3.2, ...}
      - Python dict: {'z_score': 3.2, ...}
    """
    line = line.strip()
    if not line:
        return {}
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    try:
        obj = ast.literal_eval(line)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    raise ValueError(f"detRes line is not dict-like: {line[:200]}")


def find_detres_files(
    project_dir: Path,
    *,
    detres_suffix: str = "_wm_detRes.txt",
    exclude_name: str = "pom_wm_detRes.txt",
) -> List[Path]:
    """
    Find all *_wm_detRes.txt under project_dir, excluding pom_wm_detRes.txt.
    """
    all_detres = sorted(project_dir.rglob(f"*{detres_suffix}"))
    kept = [p for p in all_detres if p.name != exclude_name]
    return kept


def ensure_detres_ready(
    project_dir: Path,
    *,
    detres_suffix: str = "_wm_detRes.txt",
    exclude_name: str = "pom_wm_detRes.txt",
    max_wait_sec: float = 500.0,
) -> List[Path]:
    """
    Wait until at least one non-pom detRes exists and has non-empty content.
    """
    deadline = time.time() + max_wait_sec
    last_seen: List[Path] = []

    while True:
        detres_files = find_detres_files(
            project_dir,
            detres_suffix=detres_suffix,
            exclude_name=exclude_name,
        )
        last_seen = detres_files

        if detres_files:
            for p in detres_files:
                try:
                    _ = read_first_non_empty_line(p, max_wait_sec=2.0, poll_interval_sec=0.2)
                    return detres_files
                except Exception:
                    continue

        if time.time() >= deadline:
            raise RuntimeError(
                f"detRes not ready after waiting {max_wait_sec:.1f}s under {project_dir}. "
                f"last_seen={last_seen}"
            )
        time.sleep(0.5)


def extract_metric_from_detres(
    detres_path: Path,
    field: str = "z_score",
    strategy_key: Optional[str] = None,
    wait_sec: float = 30.0,
) -> Optional[float]:
    """
    Extract metric from detRes.
    If strategy_key provided, try obj[strategy_key][field].
    Else:
      - try obj[field]
      - or find a nested dict value with `field`.
    """
    try:
        line = read_first_non_empty_line(detres_path, max_wait_sec=wait_sec, poll_interval_sec=0.25)
    except Exception as e:
        print(f"[WARN] detRes empty/unready: {detres_path} ({e})", file=sys.stderr)
        return None

    obj = safe_load_mapping(line)
    if not obj:
        return None

    # strategy_key path
    if strategy_key is not None:
        if strategy_key in obj and isinstance(obj[strategy_key], dict):
            v = obj[strategy_key].get(field, None)
            return None if v is None else float(v)
        # if key not exists, fallthrough

    # direct field
    if field in obj:
        return float(obj[field])

    # nested search
    for _, vv in obj.items():
        if isinstance(vv, dict) and field in vv:
            return float(vv[field])

    return None


def aggregate_detres_scores(
    detres_files: List[Path],
    *,
    field: str,
    strategy_key: Optional[str],
    mode: str = "mean",
    wait_sec: float = 30.0,
) -> float:
    """
    Aggregate scores across detRes files (multiple generated code files).
    mode: mean | max | min
    """
    if not detres_files:
        return float("nan")

    vals: List[float] = []
    for p in detres_files:
        try:
            v = extract_metric_from_detres(p, field=field, strategy_key=strategy_key, wait_sec=wait_sec)
            if v is None:
                continue
            if not (math.isnan(float(v)) or math.isinf(float(v))):
                vals.append(float(v))
        except Exception as e:
            print(f"[WARN] Failed parsing detRes={p}: {e}", file=sys.stderr)
            continue

    if not vals:
        return float("nan")

    if mode == "mean":
        return float(mean(vals))
    if mode == "max":
        return float(max(vals))
    if mode == "min":
        return float(min(vals))
    raise ValueError(f"Unknown detres_agg mode: {mode}")


# =======================
# (C) evaluation metrics
# =======================

def warn_fpr_resolution(n_neg: int, fpr_targets: List[float]) -> None:
    """
    With finite negatives, the smallest non-zero FPR step is 1/n_neg.
    """
    if n_neg <= 0:
        return
    min_step = 1.0 / n_neg
    for fpr in fpr_targets:
        if fpr > 0 and fpr < min_step:
            print(
                f"[WARN] FPR target={fpr:.6f} is below resolution 1/Nneg={min_step:.6f} "
                f"(Nneg={n_neg}). It will behave like 0-FP threshold.",
                file=sys.stderr,
            )


def compute_tpr_at_fpr(neg_scores: List[float], pos_scores: List[float], fpr_target: float) -> Tuple[float, float]:
    """
    Compute TPR@fixed FPR.
    We pick threshold maximizing TPR subject to FPR <= target.

    Returns: (tpr, threshold)
    """
    if not neg_scores or not pos_scores:
        return float("nan"), float("nan")

    # Higher score => more likely watermarked
    # Candidate thresholds = unique scores + extremes
    all_scores = sorted(set(neg_scores + pos_scores))
    # Add a threshold above max => FPR=0
    all_scores.append(max(all_scores) + 1e-12)

    best_tpr = -1.0
    best_thr = all_scores[-1]

    n_neg = len(neg_scores)
    n_pos = len(pos_scores)

    for thr in all_scores:
        fp = sum(1 for x in neg_scores if x >= thr)
        tp = sum(1 for x in pos_scores if x >= thr)
        fpr = fp / n_neg
        tpr = tp / n_pos
        if fpr <= fpr_target:
            if tpr > best_tpr:
                best_tpr = tpr
                best_thr = thr

    if best_tpr < 0:
        # impossible unless numeric weirdness
        return 0.0, best_thr
    return best_tpr, best_thr


def auc_mann_whitney(pos_scores: List[float], neg_scores: List[float]) -> float:
    """
    AUROC via rank statistic (Mann-Whitney U).
    Handles ties by average ranks.

    AUC = P(score_pos > score_neg) + 0.5*P(equal)
    """
    if not pos_scores or not neg_scores:
        return float("nan")

    scores = [(s, 1) for s in pos_scores] + [(s, 0) for s in neg_scores]
    scores.sort(key=lambda x: x[0])

    # Assign average ranks for ties
    ranks = [0.0] * len(scores)
    i = 0
    r = 1
    while i < len(scores):
        j = i
        while j < len(scores) and scores[j][0] == scores[i][0]:
            j += 1
        avg_rank = (r + (r + (j - i) - 1)) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        r += (j - i)
        i = j

    n_pos = len(pos_scores)
    n_neg = len(neg_scores)

    rank_sum_pos = 0.0
    for (rk, (_, label)) in zip(ranks, scores):
        if label == 1:
            rank_sum_pos += rk

    u = rank_sum_pos - (n_pos * (n_pos + 1) / 2.0)
    auc = u / (n_pos * n_neg)
    return float(auc)


# =======================
# (D) generation config builders
# =======================

def _require_keys(method: str, args: Dict[str, Any], keys: List[str]) -> None:
    missing = [k for k in keys if k not in args]
    if missing:
        raise KeyError(f"method={method} missing required args: {missing}")


def build_external_params(method: str, method_args: Dict[str, Any], strength: float, lang: Optional[str]) -> Dict[str, Any]:
    """
    Build external_processor_params (exactly like your codeGenBatch) with delta/kappa=strength.
    """
    method = method.lower()

    if method == "wllm":
        _require_keys(method, method_args, ["gamma", "z_threshold"])
        return {
            "wllm": {
                "gamma": method_args["gamma"],
                "delta": float(strength),
                "z_threshold": method_args["z_threshold"],
            }
        }

    if method == "sweet":
        # sweet uses entropy_threshold (ET) and z_threshold
        _require_keys(method, method_args, ["gamma", "ET", "z_threshold"])
        return {
            "sweet": {
                "gamma": method_args["gamma"],
                "delta": float(strength),
                "entropy_threshold": method_args["ET"],
                "z_threshold": method_args["z_threshold"],
            }
        }

    if method == "ewd":
        _require_keys(method, method_args, ["gamma", "hash_key", "z_threshold", "prefix_length"])
        return {
            "ewd": {
                "gamma": method_args["gamma"],
                "delta": float(strength),
                "hash_key": method_args["hash_key"],
                "z_threshold": method_args["z_threshold"],
                "prefix_length": method_args["prefix_length"],
            }
        }

    if method == "stone":
        _require_keys(method, method_args, ["gamma", "hash_key", "z_threshold", "prefix_length"])
        if lang is None:
            raise RuntimeError("STONE requires language; failed to detect language.")
        # optional params with defaults
        return {
            "stone": {
                "gamma": method_args["gamma"],
                "delta": float(strength),
                "hash_key": method_args["hash_key"],
                "z_threshold": method_args["z_threshold"],
                "prefix_length": method_args["prefix_length"],
                "language": lang,
                "watermark_on_pl": str(method_args.get("watermark_on_pl", "False")),
                "skipping_rule": method_args.get("skipping_rule", "all_pl"),
            }
        }

    if method == "waterfall":
        _require_keys(method, method_args, ["id_mu", "k_p", "n_gram", "wm_fn"])
        return {
            "waterfall": {
                "id_mu": method_args["id_mu"],
                "k_p": method_args["k_p"],
                "kappa": float(strength),
                "n_gram": method_args["n_gram"],
                "wm_fn": method_args["wm_fn"],
                "auto_reset": bool(method_args.get("auto_reset", True)),
                "detect_mode": method_args.get("detect_mode", "batch"),
            }
        }

    if method == "codeip":
        _require_keys(method, method_args, ["mode", "gamma", "message_code_len", "encode_ratio", "top_k", "message"])
        return {
            "codeip": {
                "mode": method_args["mode"],
                "delta": float(strength),
                "gamma": method_args["gamma"],
                "message_code_len": method_args["message_code_len"],
                "encode_ratio": method_args["encode_ratio"],
                "top_k": method_args["top_k"],
                "message": method_args["message"],
                "pda_model": None,
            }
        }

    raise ValueError(f"Unknown method: {method}")


def fmt_strength_for_dir(x: float) -> str:
    """
    Make strength folder name stable and human-readable.
    """
    s = f"{x:.6f}"
    s = s.rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return s


def make_result_dir_name(
    *,
    project_name: str,
    method: str,
    temperature: float,
    seed: int,
    method_args: Dict[str, Any],
    lang: Optional[str],
) -> str:
    """
    Mirror your codeGenBatch result_dir naming patterns (stable subset).
    """
    method = method.lower()
    base = f"{project_name}_{method}_T={temperature}_rngS={seed}"

    if method == "wllm":
        base += f"_gamma={method_args.get('gamma')}"
    elif method == "sweet":
        base += f"_gamma={method_args.get('gamma')}_ET={method_args.get('ET')}"
    elif method == "ewd":
        base += f"_gamma={method_args.get('gamma')}_hashKey={method_args.get('hash_key')}_prefixLen={method_args.get('prefix_length')}"
    elif method == "stone":
        base += f"_gamma={method_args.get('gamma')}_hashKey={method_args.get('hash_key')}_prefixLen={method_args.get('prefix_length')}_lang={(lang or method_args.get('language'))}"
    elif method == "waterfall":
        base += f"_idMu={method_args.get('id_mu')}_kP={method_args.get('k_p')}_nGram={method_args.get('n_gram')}_wmFn={method_args.get('wm_fn')}"
    elif method == "codeip":
        base += f"_gamma={method_args.get('gamma')}_mode={method_args.get('mode')}_messageLen={method_args.get('message_code_len')}_encodeRatio={method_args.get('encode_ratio')}_topK={method_args.get('top_k')}"
    else:
        pass

    return base


# =======================
# (E) seed / list parsing
# =======================

def parse_seeds(spec: str) -> List[int]:
    """
    seeds format:
      - "range:100:120" => [100..119]  (Python style, end exclusive)
      - "range:100:120:2"
      - "1,2,3"
    """
    spec = spec.strip()
    if spec.startswith("range:"):
        parts = spec.split(":")
        if len(parts) not in (3, 4):
            raise ValueError("range spec must be range:start:end or range:start:end:step")
        start = int(parts[1])
        end = int(parts[2])
        step = int(parts[3]) if len(parts) == 4 else 1
        return list(range(start, end, step))

    out = []
    for tok in spec.split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    return out


def parse_floats(spec: str) -> List[float]:
    out: List[float] = []
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(float(tok))
    return out


# =======================
# (F) core pipeline (generate -> copy -> read -> score)
# =======================

async def run_codegen_once(
    project_name: str,
    repoPath: Path,
    storagePath: Path,
    workspacePath: Path,
    xargs: Dict[str, Any],
) -> Path:
    """
    Exactly like your script:
      shellDelete(workspacePath) -> shellPaste([repoPath, storagePath]) -> codeGen()
    Returns workspace project_dir: workspace/<project>/<project>/
    """
    # import lazily
    from agentCodeGen import codeGen

    shellDelete(str(workspacePath), dry_run=False)
    shellPaste([repoPath, storagePath], workspacePath)

    await codeGen(project_name, xargs)

    project_dir = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Generated project_dir not found: {project_dir}")

    remove_leading_h2_line(project_dir)
    return project_dir


async def generate_score(seed: int, strength: float, cfg: Dict[str, Any]) -> Tuple[float, Path]:
    """
    Generate one sample and return (score, result_sample_path).
    Score is aggregated from detRes files in results folder.
    """
    project_name = cfg["project_name"]
    method = cfg["method"]
    temperature = cfg["temperature"]
    max_tokens = cfg["max_tokens"]
    parallel = cfg["parallel"]
    method_args = cfg["method_args"]
    score_field = cfg["score_field"]
    strategy_key = cfg["strategy_key"]
    detres_agg = cfg["detres_agg"]
    detres_wait_sec = cfg["detres_wait_sec"]

    # detect language if needed (STONE)
    lang = cfg.get("lang", None)

    xargs = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "parallel": True,
        "rng_seed": seed,
        "internal_processor_names": [],
        "external_processor_names": [] if method == "none" else [method],
        "external_processor_params": build_external_params(method, method_args, strength, lang),
    }

    # (1) Generate in workspace
    ws_project_dir = await run_codegen_once(
        project_name=project_name,
        repoPath=cfg["repoPath"],
        storagePath=cfg["storagePath"],
        workspacePath=cfg["workspacePath"],
        xargs=xargs,
    )

    # (2) Wait detRes ready (workspace)
    _ = ensure_detres_ready(
        ws_project_dir,
        detres_suffix=cfg.get("detres_suffix", "_wm_detRes.txt"),
        exclude_name=cfg.get("exclude_detres_name", "pom_wm_detRes.txt"),
        max_wait_sec=detres_wait_sec,
    )

    # (3) Copy to results (mirror your codeGenBatch)
    res_root: Path = cfg["resPath"]
    result_dir_name = make_result_dir_name(
        project_name=project_name,
        method=method,
        temperature=temperature,
        seed=seed,
        method_args=method_args,
        lang=lang,
    )
    st_dir = fmt_strength_for_dir(strength)
    destPath = (res_root / result_dir_name / f"{project_name}_{st_dir}").resolve()
    destPath.mkdir(parents=True, exist_ok=True)

    # copy code folder
    shellPaste([ws_project_dir], destPath)

    # copy DTResults if exists (optional, as you did)
    dt_results = (ws_project_dir / "DTResults").resolve()
    if dt_results.exists():
        shellPaste([dt_results], destPath)

    # (4) Parse detRes from results tree
    detres_files = find_detres_files(
        destPath,
        detres_suffix=cfg.get("detres_suffix", "_wm_detRes.txt"),
        exclude_name=cfg.get("exclude_detres_name", "pom_wm_detRes.txt"),
    )
    if not detres_files:
        # fallback to workspace (should not happen)
        detres_files = find_detres_files(
            ws_project_dir,
            detres_suffix=cfg.get("detres_suffix", "_wm_detRes.txt"),
            exclude_name=cfg.get("exclude_detres_name", "pom_wm_detRes.txt"),
        )

    score = aggregate_detres_scores(
        detres_files,
        field=score_field,
        strategy_key=strategy_key,
        mode=detres_agg,
        wait_sec=min(30.0, detres_wait_sec),
    )

    return score, destPath


async def evaluate_detection(cfg: Dict[str, Any]) -> None:
    """
    Main evaluation:
      - Generate NEG at baseline_strength
      - Generate POS at each strength != baseline_strength
      - Compute overall AUROC + TPR@FPR
      - Compute per-strength AUROC + TPR@FPR
      - Save CSV if requested
    """
    seeds = cfg["seeds"]
    strengths = cfg["strengths"]
    baseline_strength = cfg["baseline_strength"]

    fpr_targets = cfg["fpr_targets"]
    warn_fpr_resolution(len(seeds), fpr_targets)

    # ---- NEG
    neg_rows = []
    neg_scores: List[float] = []
    print(f"[INFO] Generating NEG samples: method={cfg['method']} strength={baseline_strength}, N={len(seeds)}")
    for s in seeds:
        sc, out_dir = await generate_score(s, baseline_strength, cfg)
        if sc is None or (isinstance(sc, float) and math.isnan(sc)):
            print(f"[WARN] NEG seed={s} score=NaN skipped. out={out_dir}", file=sys.stderr)
            continue
        neg_scores.append(float(sc))
        neg_rows.append({
            "seed": s,
            "strength": baseline_strength,
            "label": 0,
            "score": float(sc),
            "path": str(out_dir),
        })

    if not neg_scores:
        raise RuntimeError("All NEG samples invalid (NaN). Your detRes generation is broken.")

    # ---- POS
    pos_rows = []
    pos_scores_by_strength: Dict[float, List[float]] = {}
    for st in strengths:
        if abs(st - baseline_strength) < 1e-12:
            continue
        pos_scores_by_strength[st] = []
        print(f"[INFO] Generating POS samples: strength={st}, N={len(seeds)}")
        for s in seeds:
            sc, out_dir = await generate_score(s, st, cfg)
            if sc is None or (isinstance(sc, float) and math.isnan(sc)):
                print(f"[WARN] POS seed={s} strength={st} score=NaN skipped. out={out_dir}", file=sys.stderr)
                continue
            pos_scores_by_strength[st].append(float(sc))
            pos_rows.append({
                "seed": s,
                "strength": st,
                "label": 1,
                "score": float(sc),
                "path": str(out_dir),
            })

    # ---- overall pooled across all strengths (pos pooled)
    pooled_pos = []
    for st, lst in pos_scores_by_strength.items():
        pooled_pos.extend(lst)

    print("\n==================== OVERALL METRICS (pos pooled across strengths) ====================")
    auc_all = auc_mann_whitney(pooled_pos, neg_scores)
    print(f"[AUROC] overall pooled = {auc_all:.6f} (Npos={len(pooled_pos)}, Nneg={len(neg_scores)})")

    for fpr in fpr_targets:
        tpr, thr = compute_tpr_at_fpr(neg_scores, pooled_pos, fpr)
        print(f"[TPR@FPR={fpr*100:.3f}%] TPR={tpr:.6f}  thr={thr:.6f}")

    # ---- per-strength metrics
    print("\n==================== PER-STRENGTH METRICS ====================")
    per_strength_summary = []
    for st, pos_scores in pos_scores_by_strength.items():
        if not pos_scores:
            continue
        auc_st = auc_mann_whitney(pos_scores, neg_scores)
        print(f"\n[Strength={st}] AUROC={auc_st:.6f}  (Npos={len(pos_scores)}, Nneg={len(neg_scores)})")

        row = {"strength": st, "auroc": auc_st}
        for fpr in fpr_targets:
            tpr, thr = compute_tpr_at_fpr(neg_scores, pos_scores, fpr)
            print(f"  TPR@FPR={fpr*100:.3f}% : TPR={tpr:.6f}  thr={thr:.6f}")
            row[f"tpr@fpr={fpr}"] = tpr
            row[f"thr@fpr={fpr}"] = thr
        per_strength_summary.append(row)

    # ---- save CSV
    if cfg["save_csv"]:
        import csv
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_csv = cfg["resPath"] / f"det_eval_{cfg['project_name']}_{cfg['method']}_{ts}.csv"

        all_rows = neg_rows + pos_rows
        fieldnames = ["seed", "strength", "label", "score", "path"]
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in all_rows:
                w.writerow(r)

        # also save a tiny summary json
        out_json = cfg["resPath"] / f"det_eval_{cfg['project_name']}_{cfg['method']}_{ts}_summary.json"
        summary = {
            "project": cfg["project_name"],
            "method": cfg["method"],
            "baseline_strength": baseline_strength,
            "strengths": strengths,
            "seeds": seeds,
            "score_field": cfg["score_field"],
            "strategy_key": cfg["strategy_key"],
            "detres_agg": cfg["detres_agg"],
            "overall": {
                "auroc": auc_all,
                "n_pos": len(pooled_pos),
                "n_neg": len(neg_scores),
            },
            "per_strength": per_strength_summary,
            "fpr_targets": cfg["fpr_targets"],
        }
        out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"\n[INFO] Saved CSV: {out_csv}")
        print(f"[INFO] Saved summary JSON: {out_json}")


# =======================
# (G) CLI
# =======================

def parse_args():
    ap = argparse.ArgumentParser()

    ap.add_argument("--project_name", type=str, required=True)
    ap.add_argument("--srcPath", type=str, required=True,
                    help="Root containing <project_name>/ and storage/")
    ap.add_argument("--workspacePath", type=str, required=True)
    ap.add_argument("--resPath", type=str, required=True,
                    help="Results root, same as your codeGenBatch resPath")

    ap.add_argument("--method", type=str, required=True,
                    help="one of: wllm, sweet, ewd, stone, waterfall, codeip")

    ap.add_argument("--seeds", type=str, required=True,
                    help='e.g. "range:100:120" or "1,2,3"')
    ap.add_argument("--strengths", type=str, required=True,
                    help='e.g. "0.0,0.5,1.0,2.0,3.0"')

    ap.add_argument("--baseline_strength", type=float, default=0.0)

    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max_tokens", type=int, default=4096)
    # IMPORTANT:
    # Your codeGen pipeline REQUIRES "parallel" field to exist and usually to be True,
    # otherwise it may skip generating *_wm_detRes.txt (or generate empty files).
    # So we default parallel=True and allow explicit disabling if needed.
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--parallel", dest="parallel", action="store_true", default=True,
                   help="Enable parallel mode (default: True).")
    g.add_argument("--no_parallel", dest="parallel", action="store_false",
                   help="Disable parallel mode (NOT recommended).")

    ap.add_argument("--score_field", type=str, default="z_score",
                    help="field extracted from detRes (e.g., z_score)")
    ap.add_argument("--strategy_key", type=str, default=None,
                    help="optional nested key in detRes mapping (if detRes contains multiple strategies)")
    ap.add_argument("--detres_agg", type=str, default="mean",
                    choices=["mean", "max", "min"],
                    help="aggregate scores across multiple detRes files")

    ap.add_argument("--fpr_targets", type=str, default="0.001,0.01,0.05,0.10",
                    help="comma-separated FPR targets, default 0.1%,1%,5%,10%")

    ap.add_argument("--detres_wait_sec", type=float, default=500.0,
                    help="Max seconds to wait for detRes non-empty.")

    ap.add_argument("--method_args_json", type=str, required=True,
                    help="JSON string for method args. Must match method requirements.")

    ap.add_argument("--save_csv", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()

    srcPath = Path(args.srcPath).resolve()
    repoPath = (srcPath / args.project_name).resolve()
    storagePath = (srcPath / "storage").resolve()
    workspacePath = Path(args.workspacePath).resolve()
    resPath = Path(args.resPath).resolve()

    if not repoPath.is_dir():
        raise FileNotFoundError(f"repoPath not found: {repoPath}")
    if not storagePath.is_dir():
        raise FileNotFoundError(f"storagePath not found: {storagePath}")

    workspacePath.mkdir(parents=True, exist_ok=True)
    resPath.mkdir(parents=True, exist_ok=True)

    method_args = json.loads(args.method_args_json)

    # detect language once (needed by STONE)
    lang = None
    try:
        lang = get_programming_language(repoPath).lower()
    except Exception:
        # allowed: only matters if method is stone
        lang = None

    cfg = {
        "project_name": args.project_name,
        "repoPath": repoPath,
        "storagePath": storagePath,
        "workspacePath": workspacePath,
        "resPath": resPath,

        "method": args.method.lower(),
        "method_args": method_args,

        "seeds": parse_seeds(args.seeds),
        "strengths": parse_floats(args.strengths),
        "baseline_strength": float(args.baseline_strength),

        "temperature": float(args.temperature),
        "max_tokens": int(args.max_tokens),
        "parallel": bool(args.parallel),

        "score_field": args.score_field,
        "strategy_key": args.strategy_key if args.strategy_key else None,
        "detres_agg": args.detres_agg,

        "fpr_targets": parse_floats(args.fpr_targets),

        "detres_wait_sec": float(args.detres_wait_sec),
        "save_csv": bool(args.save_csv),

        "lang": lang,
        "detres_suffix": "_wm_detRes.txt",
        "exclude_detres_name": "pom_wm_detRes.txt",
    }

    # sanity
    if cfg["method"] == "stone" and cfg["lang"] is None:
        raise RuntimeError("Failed to detect Programming Language from repo docs/prd. STONE needs language.")
    if cfg["method"] not in {"wllm", "sweet", "ewd", "stone", "waterfall", "codeip"}:
        raise ValueError(f"Unsupported method: {cfg['method']}")

    asyncio.run(evaluate_detection(cfg))


if __name__ == "__main__":
    main()
