#!/usr/bin/env python3
"""Run the stratified 1,000-sample RQ2 LLM-RAG attack without exposing credentials."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
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
INPUT_PRICE_CNY_PER_1K = 0.00875
OUTPUT_PRICE_CNY_PER_1K = 0.07


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--input-dir", default="outputs/fresh/llm_input")
    parser.add_argument("--output-dir", default="outputs/fresh/llm_full_1000")
    parser.add_argument("--samples-per-cell", type=int, default=125)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-completion-tokens", type=int, default=1100)
    parser.add_argument("--reasoning-effort", default="minimal")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_env_file(path: Path):
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").strip()
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        key = key.strip()
        value = value.strip().strip("\"'")
        markdown_link = re.fullmatch(r"\[([^]]+)]\([^)]+\)", value)
        if markdown_link:
            value = markdown_link.group(1)
        values[key] = value
    key = values.get("OPENAI_API_KEY") or values.get("api_key")
    base_url = values.get("base_url") or values.get("OPENAI_BASE_URL")
    if not key:
        raise ValueError("credential file does not define OPENAI_API_KEY or api_key")
    if not base_url:
        raise ValueError("credential file does not define base_url")
    return key, base_url


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def provider_meta(row):
    return row.get("attack_meta", {}).get("provider_response") or {}


def summarize_output(path: Path):
    rows = read_jsonl(path)
    usage_rows = [provider_meta(row).get("usage") for row in rows]
    usage_rows = [usage for usage in usage_rows if usage]
    prompt_tokens = sum(usage.get("prompt_tokens", 0) for usage in usage_rows)
    completion_tokens = sum(usage.get("completion_tokens", 0) for usage in usage_rows)
    cost_cny = (
        prompt_tokens / 1000 * INPUT_PRICE_CNY_PER_1K
        + completion_tokens / 1000 * OUTPUT_PRICE_CNY_PER_1K
    )
    return {
        "rows": len(rows),
        "status_counts": dict(Counter(row.get("attack_meta", {}).get("status", "missing") for row in rows)),
        "syntax_valid": sum(bool(row.get("attack_meta", {}).get("syntax_valid")) for row in rows),
        "changed": sum(bool(row.get("attack_meta", {}).get("changed")) for row in rows),
        "rows_with_usage": len(usage_rows),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": sum(
            usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            for usage in usage_rows
        ),
        "recorded_cost_cny": cost_cny,
        "response_models": sorted({provider_meta(row).get("response_model") for row in rows if provider_meta(row).get("response_model")}),
        "sha256": sha256_file(path),
    }


def main():
    args = parse_args()
    if args.samples_per_cell <= 0 or args.workers <= 0:
        raise ValueError("sample and worker counts must be positive")
    expected = len(METHODS) * len(DATASETS) * args.samples_per_cell
    if expected != 1000:
        raise ValueError(f"this archived protocol requires exactly 1,000 samples; got {expected}")

    env_path = Path(args.env_file).expanduser().resolve()
    mode = env_path.stat().st_mode & 0o777
    if mode & 0o077:
        raise PermissionError(f"credential file must not be group/world accessible; mode={mode:o}")
    api_key, base_url = load_env_file(env_path)
    child_env = os.environ.copy()
    child_env["OPENAI_API_KEY"] = api_key
    child_env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT / ".deps"), str(ROOT), child_env.get("PYTHONPATH", "")])
    )

    input_dir = (ROOT / args.input_dir).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    attack_dir = output_dir / "main"
    log_dir = output_dir / "logs"
    attack_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for method in METHODS:
        for dataset in DATASETS:
            input_path = input_dir / f"{method}_{dataset}.jsonl"
            output_path = attack_dir / f"{method}_{dataset}_llm_all.jsonl"
            if len(read_jsonl(input_path)) < args.samples_per_cell:
                raise ValueError(f"not enough eligible rows: {input_path}")
            command = [
                sys.executable,
                str(ROOT / "project/srcMarker/SrcMarker/1_obfus_AI.py"),
                "--input", str(input_path),
                "--output", str(output_path),
                "--lang", LANGUAGES[dataset],
                "--channel", "all",
                "--seed", str(args.seed),
                "--sample-size", str(args.samples_per_cell),
                "--max-chars", "1400",
                "--selection", "input",
                "--provider", "openai-compatible",
                "--base-url", base_url,
                "--model", args.model,
                "--temperature", "0",
                "--top-k", "6",
                "--max-completion-tokens", str(args.max_completion_tokens),
                "--reasoning-effort", args.reasoning_effort,
                "--max-attempts", "1",
                "--progress-every", "25",
                "--parser-lib", str(ROOT / "training/SrcMarker_fresh/parser/languages.so"),
            ]
            if args.resume:
                command.append("--resume")
            jobs.append((method, dataset, input_path, output_path, command))

    protocol = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "design": "balanced method-by-dataset stratified cohort",
        "methods": list(METHODS),
        "datasets": list(DATASETS),
        "samples_per_cell": args.samples_per_cell,
        "total_samples": expected,
        "provider": "openai-compatible",
        "base_url": base_url,
        "requested_model": args.model,
        "temperature": 0,
        "seed": args.seed,
        "top_k": 6,
        "max_chars": 1400,
        "max_completion_tokens": args.max_completion_tokens,
        "reasoning_effort": args.reasoning_effort,
        "max_attempts": 1,
        "credential_file_archived": False,
        "jobs": [],
    }
    (output_dir / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    if args.dry_run:
        print(json.dumps({"jobs": len(jobs), "total_samples": expected, "output_dir": str(output_dir)}, indent=2))
        return

    def run_job(job):
        method, dataset, input_path, output_path, command = job
        log_path = log_dir / f"main_{method}_{dataset}.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            result = subprocess.run(
                command, cwd=ROOT, env=child_env, stdout=log_handle,
                stderr=subprocess.STDOUT, text=True, check=False,
            )
        if result.returncode != 0:
            raise RuntimeError(f"job failed ({result.returncode}): {method}/{dataset}; see {log_path}")
        summary = summarize_output(output_path)
        summary.update({
            "method": method,
            "dataset": dataset,
            "language": LANGUAGES[dataset],
            "input": str(input_path.relative_to(ROOT)),
            "output": str(output_path.relative_to(ROOT)),
            "log": str(log_path.relative_to(ROOT)),
        })
        print(json.dumps(summary), flush=True)
        return summary

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        summaries = list(executor.map(run_job, jobs))

    protocol["completed_utc"] = datetime.now(timezone.utc).isoformat()
    protocol["jobs"] = summaries
    protocol["accounting"] = {
        "rows": sum(row["rows"] for row in summaries),
        "rows_with_usage": sum(row["rows_with_usage"] for row in summaries),
        "prompt_tokens": sum(row["prompt_tokens"] for row in summaries),
        "completion_tokens": sum(row["completion_tokens"] for row in summaries),
        "reasoning_tokens": sum(row["reasoning_tokens"] for row in summaries),
        "recorded_cost_cny": sum(row["recorded_cost_cny"] for row in summaries),
        "pricing_cny_per_1k": {
            "input": INPUT_PRICE_CNY_PER_1K,
            "output": OUTPUT_PRICE_CNY_PER_1K,
        },
    }
    (output_dir / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print(json.dumps(protocol["accounting"], indent=2))


if __name__ == "__main__":
    main()
