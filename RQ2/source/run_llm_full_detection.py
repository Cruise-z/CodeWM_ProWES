#!/usr/bin/env python3
"""Run checkpoint-specific watermark extraction and paired analysis for LLM attacks."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
METHODS = ("srcmarker", "codemark")
DATASETS = ("github_c_funcs", "github_java_funcs", "csn_js", "csn_java")
LANGUAGES = {
    "github_c_funcs": "cpp",
    "github_java_funcs": "java",
    "csn_js": "javascript",
    "csn_java": "java",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="outputs/fresh/llm_full_1000")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--gpus", default="0,1")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    args = parse_args()
    run_dir = (ROOT / args.run_dir).resolve()
    eval_dir = run_dir / "main_eval"
    metric_dir = run_dir / "metrics"
    log_dir = run_dir / "logs"
    for directory in (eval_dir, metric_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    gpu_ids = [value.strip() for value in args.gpus.split(",") if value.strip()]
    if args.device == "cuda" and not gpu_ids:
        raise ValueError("at least one GPU id is required for CUDA")

    base_env = os.environ.copy()
    base_env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT / ".deps"), str(ROOT), base_env.get("PYTHONPATH", "")])
    )
    jobs = [(method, dataset) for method in METHODS for dataset in DATASETS]

    def run_job(index_job):
        index, (method, dataset) = index_job
        attack = run_dir / "main" / f"{method}_{dataset}_llm_all.jsonl"
        evaluated = eval_dir / f"{method}_{dataset}_llm_all_eval.jsonl"
        metric = metric_dir / f"{method}_{dataset}_llm_all.json"
        checkpoint = (
            ROOT / "training/SrcMarker_fresh/ckpts"
            / f"fresh_rq2_{method}_42_{dataset}" / "models_best.pt"
        )
        if not attack.exists() or not checkpoint.exists():
            raise FileNotFoundError(f"missing attack/checkpoint for {method}/{dataset}")
        env = base_env.copy()
        assigned_gpu = None
        if args.device == "cuda":
            assigned_gpu = gpu_ids[index % len(gpu_ids)]
            env["CUDA_VISIBLE_DEVICES"] = assigned_gpu
        detect_command = [
            sys.executable,
            str(ROOT / "project/srcMarker/SrcMarker/run_watermark_detector_portable.py"),
            "--input", str(attack),
            "--output", str(evaluated),
            "--srcmarker-root", str(ROOT / "training/SrcMarker_fresh"),
            "--checkpoint-path", str(checkpoint),
            "--lang", LANGUAGES[dataset],
            "--device", args.device,
            "--batch-size", str(args.batch_size),
        ]
        detect_log = log_dir / f"detect_{method}_{dataset}.log"
        with detect_log.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                detect_command, cwd=ROOT, env=env, stdout=handle,
                stderr=subprocess.STDOUT, text=True, check=False,
            )
        if result.returncode != 0:
            raise RuntimeError(f"detector failed: {method}/{dataset}; see {detect_log}")

        analysis_command = [
            sys.executable,
            str(ROOT / "project/srcMarker/SrcMarker/3_analysis.py"),
            "--input", str(evaluated),
            "--bootstrap", str(args.bootstrap),
            "--seed", str(args.seed),
            "--json-output", str(metric),
        ]
        analysis_log = log_dir / f"analysis_{method}_{dataset}.log"
        with analysis_log.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                analysis_command, cwd=ROOT, env=env, stdout=handle,
                stderr=subprocess.STDOUT, text=True, check=False,
            )
        if result.returncode != 0:
            raise RuntimeError(f"analysis failed: {method}/{dataset}; see {analysis_log}")
        metrics = json.loads(metric.read_text(encoding="utf-8"))
        summary = {
            "method": method,
            "dataset": dataset,
            "language": LANGUAGES[dataset],
            "device": args.device,
            "assigned_gpu": assigned_gpu,
            "checkpoint": str(checkpoint.relative_to(ROOT)),
            "checkpoint_sha256": sha256_file(checkpoint),
            "attack_sha256": sha256_file(attack),
            "evaluated_sha256": sha256_file(evaluated),
            "metrics_sha256": sha256_file(metric),
            "metrics": metrics,
        }
        print(json.dumps({
            "method": method,
            "dataset": dataset,
            "n_paired": metrics["n_paired"],
            "attack_BAR": metrics["attack_BAR"],
            "attack_MAR": metrics["attack_MAR"],
        }), flush=True)
        return summary

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(run_job, enumerate(jobs)))
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "device": args.device,
            "gpu_ids": gpu_ids if args.device == "cuda" else [],
            "batch_size": args.batch_size,
            "bootstrap_repetitions": args.bootstrap,
            "bootstrap_seed": args.seed,
            "n_bits": 4,
            "model_architecture": "GRU shared encoder",
            "token_truncation": 512,
        },
        "results": results,
    }
    (run_dir / "detection_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
