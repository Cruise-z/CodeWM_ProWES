#!/usr/bin/env python3
"""Build final artifacts for the fresh-checkpoint RQ2 runs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TRAIN = ROOT / "training" / "SrcMarker_fresh"
OUT = ROOT / "outputs" / "fresh"
FINAL = OUT / "final"
METHODS = ("srcmarker", "codemark")
DATASETS = ("github_c_funcs", "github_java_funcs", "csn_js", "csn_java")
CHANNELS = ("id", "expr", "block", "all")
LABELS = {
    "srcmarker": "SrcMarker",
    "codemark": "CodeMark",
    "github_c_funcs": "GitHub-C",
    "github_java_funcs": "GitHub-Java",
    "csn_js": "CSN-JavaScript",
    "csn_java": "CSN-Java",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def accuracy(rows):
    paired = [
        (row["watermark"], row["extract"])
        for row in rows
        if isinstance(row.get("watermark"), list)
        and isinstance(row.get("extract"), list)
        and len(row["watermark"]) == len(row["extract"])
    ]
    total_bits = sum(len(gt) for gt, _ in paired)
    correct_bits = sum(sum(a == b for a, b in zip(gt, pred)) for gt, pred in paired)
    exact = sum(gt == pred for gt, pred in paired)
    return {
        "n": len(paired),
        "BAR": correct_bits / total_bits,
        "MAR": exact / len(paired),
    }


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_complete():
    required = []
    for method in METHODS:
        for dataset in DATASETS:
            ckpt = TRAIN / "ckpts" / f"fresh_rq2_{method}_42_{dataset}"
            required.extend(
                [
                    ckpt / "run_manifest.json",
                    ckpt / "training_history.json",
                    ckpt / "models_best.pt",
                    OUT / "base" / f"{method}_{dataset}.jsonl",
                ]
            )
            required.extend(
                OUT / "metrics" / f"{method}_{dataset}_{channel}.json"
                for channel in CHANNELS
            )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Fresh experiment is incomplete:\n" + "\n".join(missing))


def main():
    require_complete()
    FINAL.mkdir(parents=True, exist_ok=True)
    runs = []
    robustness = []

    for method in METHODS:
        for dataset in DATASETS:
            ckpt_dir = TRAIN / "ckpts" / f"fresh_rq2_{method}_42_{dataset}"
            manifest = load_json(ckpt_dir / "run_manifest.json")
            history = load_json(ckpt_dir / "training_history.json")
            best = max(history, key=lambda epoch: epoch["valid"]["actual_acc"])
            checkpoint = ckpt_dir / "models_best.pt"
            clean = accuracy(load_jsonl(OUT / "base" / f"{method}_{dataset}.jsonl"))
            runs.append(
                {
                    "method": LABELS[method],
                    "dataset": LABELS[dataset],
                    "epochs": len(history),
                    "best_epoch_index_zero_based": best["epoch"],
                    "best_epoch_number_one_based": best["epoch"] + 1,
                    "best_valid_BAR": best["valid"]["actual_acc"],
                    "best_epoch_test_BAR": best["test"]["actual_acc"],
                    "best_epoch_test_MAR": best["test"]["msg_acc"],
                    "generated_clean_BAR": clean["BAR"],
                    "generated_clean_MAR": clean["MAR"],
                    "test_samples": clean["n"],
                    "transform_capacity": manifest["transform_capacity"],
                    "checkpoint_bytes": checkpoint.stat().st_size,
                    "checkpoint_sha256": sha256(checkpoint),
                    "from_scratch": manifest["initialization"] == "random_from_seed"
                    and not manifest["checkpoint_loaded"],
                }
            )
            for channel in CHANNELS:
                metric = load_json(OUT / "metrics" / f"{method}_{dataset}_{channel}.json")
                robustness.append(
                    {
                        "method": LABELS[method],
                        "dataset": LABELS[dataset],
                        "channel": channel,
                        **metric,
                    }
                )

    artifact = {
        "protocol": {
            "initialization": "fresh random initialization",
            "epochs": 25,
            "n_bits": 4,
            "architecture": "GRU shared encoder",
            "batch_size": 64,
            "seed": 42,
            "bootstrap_repetitions": 10000,
        },
        "training_and_clean": runs,
        "rule_robustness": robustness,
    }
    (FINAL / "rq2_fresh_results.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )

    scalar_keys = [
        "method", "dataset", "channel", "n_paired", "clean_BAR", "attack_BAR",
        "DeltaBAR", "clean_MAR", "attack_MAR", "change_rate", "syntax_valid_rate",
        "paired_coverage",
    ]
    with (FINAL / "rq2_fresh_rule_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=scalar_keys)
        writer.writeheader()
        writer.writerows({key: row[key] for key in scalar_keys} for row in robustness)

    run_lines = []
    for run in runs:
        run_lines.append(
            f"| {run['method']} | {run['dataset']} | "
            f"{run['best_epoch_number_one_based']} | "
            f"{run['generated_clean_BAR']:.4f} | {run['generated_clean_MAR']:.4f} | "
            f"{run['test_samples']} |"
        )
    robust_lines = []
    for row in robustness:
        robust_lines.append(
            f"| {row['method']} | {row['dataset']} | {row['channel']} | "
            f"{row['clean_BAR']:.4f} | {row['attack_BAR']:.4f} | "
            f"{row['DeltaBAR']:.4f} | {row['attack_MAR']:.4f} | "
            f"{row['change_rate']:.4f} | {row['syntax_valid_rate']:.4f} |"
        )

    report = f"""# RQ2 fresh-checkpoint results

Both methods were randomly initialized with seed 42 and trained independently for 25 epochs on four datasets. All runs used a four-bit payload, shared GRU encoder, and batch size 64. Rule attacks covered the Id, Expr, Block, and ALL channels. Robustness confidence intervals use 10,000 paired sample-level bootstrap replicates.

## Clean results after training

| Method | Dataset | Best epoch | BAR | MAR | Samples |
|---|---|---:|---:|---:|---:|
{chr(10).join(run_lines)}

## Rule-attack results

| Method | Dataset | Channel | Clean BAR | Attack BAR | DeltaBAR | Attack MAR | Change rate | Syntax-valid rate |
|---|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(robust_lines)}

See `rq2_fresh_results.json` for complete checkpoint hashes, training records, status counts, and 95% confidence intervals. Flat metrics are in `rq2_fresh_rule_metrics.csv`.

## Data not generated by this script

This workspace did not configure live LLM-provider credentials for this earlier report stage, so mock identity outputs are not treated as LLM attack-performance data. The rule-attack and detector records are actual fresh-checkpoint results.
"""
    (FINAL / "RQ2_FRESH_RESULTS.md").write_text(report, encoding="utf-8")
    print(f"wrote fresh report to {FINAL}")


if __name__ == "__main__":
    main()
