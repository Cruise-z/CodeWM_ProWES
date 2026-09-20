#!/usr/bin/env python3
"""Paired robustness analysis for attacked watermark results.

Reports clean/attacked BAR, clean/attacked MAR, DeltaBAR, attack validity
coverage, and paired sample-bootstrap confidence intervals. Attacked bit
accuracy is not conditioned on clean bit-level correctness.
"""
from __future__ import annotations
import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def bit_acc(pred, gt):
    if len(pred) != len(gt) or not gt:
        raise ValueError("prediction and ground-truth bit lengths differ")
    return sum(int(a == b) for a, b in zip(pred, gt)) / len(gt)


def msg_acc(pred, gt):
    return float(list(pred) == list(gt))


def summarize(rows):
    paired = []
    for r in rows:
        gt, clean, attacked = r.get("watermark"), r.get("extract"), r.get("obfus_extract")
        if isinstance(gt, list) and isinstance(clean, list) and isinstance(attacked, list):
            if len(gt) == len(clean) == len(attacked) and len(gt) > 0:
                paired.append((gt, clean, attacked))
    if not paired:
        raise ValueError("No paired rows containing watermark/extract/obfus_extract")
    k_values = {len(x[0]) for x in paired}
    if len(k_values) != 1:
        raise ValueError(f"Mixed message lengths: {sorted(k_values)}")
    k = next(iter(k_values))
    clean_bar = mean(bit_acc(c, g) for g, c, a in paired)
    attack_bar = mean(bit_acc(a, g) for g, c, a in paired)
    clean_mar = mean(msg_acc(c, g) for g, c, a in paired)
    attack_mar = mean(msg_acc(a, g) for g, c, a in paired)
    return {
        "n_paired": len(paired), "n_bits": k,
        "clean_BAR": clean_bar, "attack_BAR": attack_bar,
        "DeltaBAR": clean_bar - attack_bar,
        "clean_MAR": clean_mar, "attack_MAR": attack_mar,
        "chance_BAR": 0.5, "chance_MAR": 2 ** (-k),
    }, paired


def bootstrap(paired, reps, seed):
    import numpy as np

    rng = np.random.default_rng(seed)
    n = len(paired)
    names = ["clean_BAR", "attack_BAR", "DeltaBAR", "clean_MAR", "attack_MAR"]
    observations = np.asarray([
        [bit_acc(c, g), bit_acc(a, g), bit_acc(c, g) - bit_acc(a, g),
         msg_acc(c, g), msg_acc(a, g)]
        for g, c, a in paired
    ], dtype=np.float64)
    chunks = []
    # Bound the temporary resampling matrix to roughly one million indices.
    chunk_size = max(1, min(reps, 1_000_000 // n))
    for start in range(0, reps, chunk_size):
        size = min(chunk_size, reps - start)
        indices = rng.integers(0, n, size=(size, n))
        chunks.append(observations[indices].mean(axis=1))
    estimates = np.concatenate(chunks, axis=0)
    quantiles = np.quantile(estimates, [0.025, 0.975], axis=0)
    return {name: [float(quantiles[0, i]), float(quantiles[1, i])]
            for i, name in enumerate(names)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--json-output", default=None)
    a = ap.parse_args()
    rows = read_jsonl(a.input)
    metrics, paired = summarize(rows)
    attempted = len(rows)
    changed = sum(bool(r.get("attack_meta", {}).get("changed")) for r in rows)
    syntax_valid = sum(bool(r.get("attack_meta", {}).get("syntax_valid")) for r in rows)
    known_statuses = ["no_op", "syntax_invalid", "execution_invalid", "valid_attack", "error"]
    status_counts = {
        status: sum(r.get("attack_meta", {}).get("status") == status for r in rows)
        for status in known_statuses
    }
    status_counts["unclassified"] = attempted - sum(status_counts.values())
    metrics.update({
        "n_attempted": attempted,
        "n_changed": changed,
        "n_syntax_valid": syntax_valid,
        "change_rate": changed/attempted if attempted else math.nan,
        "syntax_valid_rate": syntax_valid/attempted if attempted else math.nan,
        "paired_coverage": metrics["n_paired"]/attempted if attempted else math.nan,
        "status_counts": status_counts,
        "bootstrap_95CI": bootstrap(paired, a.bootstrap, a.seed) if a.bootstrap > 0 else None,
    })
    print(json.dumps(metrics, indent=2))
    if a.json_output:
        Path(a.json_output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
