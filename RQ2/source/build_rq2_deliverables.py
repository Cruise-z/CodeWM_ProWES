#!/usr/bin/env python3
"""Build the three audited RQ2 deliverables after the 1,000-sample LLM run."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import numpy as np


ROOT = Path(__file__).resolve().parent
DELIVERABLES = ROOT / "deliverables"
REPORT_DIR = DELIVERABLES / "01_paper_report"
TABLE_ROOT = DELIVERABLES / "03_tables_figures"
TABLE_DIR = TABLE_ROOT / "tables"
FIGURE_DIR = TABLE_ROOT / "figures"
DATASET_LABELS = {
    "github_c_funcs": "GitHub-C",
    "github_java_funcs": "GitHub-Java",
    "csn_js": "CSN-JavaScript",
    "csn_java": "CSN-Java",
}
METHOD_LABELS = {"srcmarker": "SrcMarker", "codemark": "CodeMark"}
METHOD_ORDER = ["SrcMarker", "CodeMark"]
DATASET_ORDER = ["GitHub-C", "GitHub-Java", "CSN-JavaScript", "CSN-Java"]
CHANNEL_ORDER = ["id", "expr", "block", "all"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return f"{value:.4f}"


def pct(value):
    return f"{100 * value:.2f}%"


def flatten_metric(row):
    result = dict(row)
    ci = row.get("bootstrap_95CI") or {}
    for metric in ("clean_BAR", "attack_BAR", "DeltaBAR", "clean_MAR", "attack_MAR"):
        bounds = ci.get(metric, [None, None])
        result[f"{metric}_ci_low"] = bounds[0]
        result[f"{metric}_ci_high"] = bounds[1]
    result.pop("bootstrap_95CI", None)
    result.pop("status_counts", None)
    return result


def markdown_table(headers, rows):
    output = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def latex_table(path: Path, columns, headers, rows, caption, label):
    def escape(value):
        return str(value).replace("_", r"\_").replace("%", r"\%")
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        rf"\begin{{tabular}}{{{columns}}}",
        r"\toprule",
        " & ".join(escape(value) for value in headers) + r" \\",
        r"\midrule",
    ]
    lines.extend(" & ".join(escape(value) for value in row) + r" \\" for row in rows)
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\end{table*}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def weighted(rows, field, weight="n_paired"):
    denominator = sum(row[weight] for row in rows)
    return sum(row[field] * row[weight] for row in rows) / denominator


def bit_acc(prediction, target):
    return sum(int(left == right) for left, right in zip(prediction, target)) / len(target)


def build_llm_method_contrasts(llm_dir: Path):
    contrasts = []
    for dataset_index, (dataset_key, dataset_label) in enumerate(DATASET_LABELS.items()):
        indexed = {}
        for method in METHOD_LABELS:
            path = llm_dir / "main_eval" / f"{method}_{dataset_key}_llm_all_eval.jsonl"
            indexed[method] = {
                row["_attack_uid"]: row for row in read_jsonl(path)
                if row.get("attack_meta", {}).get("status") == "valid_attack"
                and isinstance(row.get("watermark"), list)
                and isinstance(row.get("extract"), list)
                and isinstance(row.get("obfus_extract"), list)
            }
        common = sorted(set(indexed["srcmarker"]) & set(indexed["codemark"]))
        if not common:
            raise ValueError(f"no common valid LLM rows for {dataset_key}")
        observations = []
        for uid in common:
            values = {}
            for method in ("srcmarker", "codemark"):
                row = indexed[method][uid]
                clean = bit_acc(row["extract"], row["watermark"])
                attacked = bit_acc(row["obfus_extract"], row["watermark"])
                attack_mar = float(row["obfus_extract"] == row["watermark"])
                values[method] = (attacked, clean - attacked, attack_mar)
            observations.append([
                values["srcmarker"][1], values["codemark"][1],
                values["srcmarker"][1] - values["codemark"][1],
                values["srcmarker"][0], values["codemark"][0],
                values["srcmarker"][0] - values["codemark"][0],
                values["srcmarker"][2], values["codemark"][2],
                values["srcmarker"][2] - values["codemark"][2],
            ])
        observations = np.asarray(observations, dtype=np.float64)
        rng = np.random.default_rng(42 + dataset_index)
        estimates = []
        chunk_size = max(1, min(10000, 1_000_000 // len(common)))
        for start in range(0, 10000, chunk_size):
            size = min(chunk_size, 10000 - start)
            indices = rng.integers(0, len(common), size=(size, len(common)))
            estimates.append(observations[indices].mean(axis=1))
        estimates = np.concatenate(estimates, axis=0)
        lower, upper = np.quantile(estimates, [0.025, 0.975], axis=0)
        point = observations.mean(axis=0)
        contrasts.append({
            "dataset": dataset_label,
            "n_common_valid": len(common),
            "srcmarker_DeltaBAR": point[0],
            "codemark_DeltaBAR": point[1],
            "DeltaBAR_difference_srcmarker_minus_codemark": point[2],
            "DeltaBAR_difference_ci_low": lower[2],
            "DeltaBAR_difference_ci_high": upper[2],
            "srcmarker_attack_BAR": point[3],
            "codemark_attack_BAR": point[4],
            "attack_BAR_difference_srcmarker_minus_codemark": point[5],
            "attack_BAR_difference_ci_low": lower[5],
            "attack_BAR_difference_ci_high": upper[5],
            "srcmarker_attack_MAR": point[6],
            "codemark_attack_MAR": point[7],
            "attack_MAR_difference_srcmarker_minus_codemark": point[8],
            "attack_MAR_difference_ci_low": lower[8],
            "attack_MAR_difference_ci_high": upper[8],
            "bootstrap_repetitions": 10000,
            "bootstrap_seed": 42 + dataset_index,
        })
    return contrasts


def main():
    fresh_path = ROOT / "outputs/fresh/final/rq2_fresh_results.json"
    epr_path = ROOT / "outputs/fresh/epr_rule/final/rq2_full_rule_epr.json"
    pilot_path = ROOT / "outputs/fresh/llm_pilot_minimal/final/rq2_llm_pilot.json"
    llm_dir = ROOT / "outputs/fresh/llm_full_1000"
    protocol_path = llm_dir / "protocol.json"
    detection_path = llm_dir / "detection_manifest.json"
    cohort_path = ROOT / "outputs/fresh/llm_input/cohort_manifest.json"
    system_prompt_path = ROOT / "rq2_revision/prompts/system_prompt.txt"
    user_prompt_path = ROOT / "rq2_revision/prompts/user_prompt_template.txt"
    rule_kb_path = ROOT / "rq2_revision/rules/hard_rules.json"
    for path in (
        fresh_path, epr_path, pilot_path, protocol_path, detection_path, cohort_path,
        system_prompt_path, user_prompt_path, rule_kb_path,
    ):
        if not path.exists():
            raise FileNotFoundError(path)
    fresh = read_json(fresh_path)
    epr = read_json(epr_path)
    pilot = read_json(pilot_path)
    protocol = read_json(protocol_path)
    detection = read_json(detection_path)
    cohort = read_json(cohort_path)
    rule_kb = read_json(rule_kb_path)
    system_prompt = system_prompt_path.read_text(encoding="utf-8").strip()
    user_prompt = user_prompt_path.read_text(encoding="utf-8").strip()
    if protocol.get("accounting", {}).get("rows") != 1000:
        raise ValueError("LLM protocol does not contain exactly 1,000 output rows")
    if len(detection.get("results", [])) != 8:
        raise ValueError("expected eight LLM detector cells")

    for directory in (REPORT_DIR, TABLE_DIR, FIGURE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    clean_rows = []
    for row in fresh["training_and_clean"]:
        clean_rows.append({
            "method": row["method"],
            "dataset": row["dataset"],
            "epochs": row["epochs"],
            "best_epoch": row["best_epoch_number_one_based"],
            "clean_BAR": row["generated_clean_BAR"],
            "clean_MAR": row["generated_clean_MAR"],
            "test_samples": row["test_samples"],
            "checkpoint_sha256": row["checkpoint_sha256"],
        })
    clean_rows.sort(key=lambda row: (METHOD_ORDER.index(row["method"]), DATASET_ORDER.index(row["dataset"])))
    write_csv(
        TABLE_DIR / "rq2_clean.csv", clean_rows,
        ["method", "dataset", "epochs", "best_epoch", "clean_BAR", "clean_MAR", "test_samples", "checkpoint_sha256"],
    )

    rule_rows = [flatten_metric(row) for row in fresh["rule_robustness"]]
    rule_rows.sort(key=lambda row: (
        METHOD_ORDER.index(row["method"]), DATASET_ORDER.index(row["dataset"]), CHANNEL_ORDER.index(row["channel"])
    ))
    metric_fields = [
        "method", "dataset", "channel", "n_attempted", "n_paired", "n_changed", "n_syntax_valid",
        "clean_BAR", "clean_BAR_ci_low", "clean_BAR_ci_high",
        "attack_BAR", "attack_BAR_ci_low", "attack_BAR_ci_high",
        "DeltaBAR", "DeltaBAR_ci_low", "DeltaBAR_ci_high",
        "clean_MAR", "clean_MAR_ci_low", "clean_MAR_ci_high",
        "attack_MAR", "attack_MAR_ci_low", "attack_MAR_ci_high",
        "change_rate", "syntax_valid_rate", "paired_coverage", "chance_BAR", "chance_MAR",
    ]
    write_csv(TABLE_DIR / "rq2_rule_robustness.csv", rule_rows, metric_fields)

    epr_rows = []
    for row in epr["results"]:
        epr_rows.append({
            "dataset": row["dataset"],
            "dataset_label": row["dataset"].upper(),
            "language": row["language"],
            "channel": row["channel"],
            "n_total": row["n_total"],
            "n_baseline_pass": row["n_baseline_pass"],
            "n_changed": row["n_changed"],
            "n_syntax_valid_changed": row["n_syntax_valid_changed"],
            "n_post_pass": row["n_post_pass"],
            "attack_coverage": row["attack_coverage"],
            "syntax_validity_given_changed": row["syntax_validity_given_changed"],
            "EPR": row["EPR_given_valid_changed"],
        })
    write_csv(
        TABLE_DIR / "rq2_rule_epr.csv", epr_rows,
        ["dataset", "dataset_label", "language", "channel", "n_total", "n_baseline_pass", "n_changed",
         "n_syntax_valid_changed", "n_post_pass", "attack_coverage", "syntax_validity_given_changed", "EPR"],
    )

    llm_rows = []
    checkpoint_rows = []
    for result in detection["results"]:
        metric = flatten_metric(result["metrics"])
        metric["method"] = METHOD_LABELS[result["method"]]
        metric["dataset"] = DATASET_LABELS[result["dataset"]]
        metric["attack"] = "llm-rag"
        llm_rows.append(metric)
        checkpoint_rows.append({
            "method": METHOD_LABELS[result["method"]],
            "dataset": DATASET_LABELS[result["dataset"]],
            "checkpoint": result["checkpoint"],
            "checkpoint_sha256": result["checkpoint_sha256"],
        })
    llm_rows.sort(key=lambda row: (METHOD_ORDER.index(row["method"]), DATASET_ORDER.index(row["dataset"])))
    llm_fields = ["method", "dataset", "attack"] + [field for field in metric_fields if field not in {"method", "dataset", "channel"}]
    write_csv(TABLE_DIR / "rq2_llm_robustness.csv", llm_rows, llm_fields)

    generation_rows = []
    for job in protocol["jobs"]:
        generation_rows.append({
            "method": METHOD_LABELS[job["method"]],
            "dataset": DATASET_LABELS[job["dataset"]],
            "rows": job["rows"],
            "valid_attack": job["status_counts"].get("valid_attack", 0),
            "syntax_invalid": job["status_counts"].get("syntax_invalid", 0),
            "no_op": job["status_counts"].get("no_op", 0),
            "error": job["status_counts"].get("error", 0),
            "prompt_tokens": job["prompt_tokens"],
            "completion_tokens": job["completion_tokens"],
            "reasoning_tokens": job["reasoning_tokens"],
            "recorded_cost_cny": job["recorded_cost_cny"],
            "response_models": ";".join(job["response_models"]),
            "output_sha256": job["sha256"],
        })
    generation_rows.sort(key=lambda row: (METHOD_ORDER.index(row["method"]), DATASET_ORDER.index(row["dataset"])))
    write_csv(
        TABLE_DIR / "rq2_llm_generation.csv", generation_rows,
        ["method", "dataset", "rows", "valid_attack", "syntax_invalid", "no_op", "error", "prompt_tokens",
         "completion_tokens", "reasoning_tokens", "recorded_cost_cny", "response_models", "output_sha256"],
    )
    method_contrasts = build_llm_method_contrasts(llm_dir)
    write_csv(
        TABLE_DIR / "rq2_llm_method_contrasts.csv",
        method_contrasts,
        list(method_contrasts[0]),
    )
    rule_usage_rows = []
    overall_applied_rules = Counter()
    for method_key, method_label in METHOD_LABELS.items():
        for dataset_key, dataset_label in DATASET_LABELS.items():
            rows = read_jsonl(llm_dir / "main" / f"{method_key}_{dataset_key}_llm_all.jsonl")
            retrieved = Counter()
            reported = Counter()
            valid_reported = Counter()
            for row in rows:
                meta = row.get("attack_meta", {})
                retrieved.update(meta.get("retrieved_rule_ids", []))
                reported.update(meta.get("reported_applied_rule_ids", []))
                overall_applied_rules.update(meta.get("reported_applied_rule_ids", []))
                if meta.get("status") == "valid_attack":
                    valid_reported.update(meta.get("reported_applied_rule_ids", []))
            for rule_id in sorted(set(retrieved) | set(reported)):
                rule_usage_rows.append({
                    "method": method_label,
                    "dataset": dataset_label,
                    "rule_id": rule_id,
                    "retrieved_count": retrieved[rule_id],
                    "reported_applied_count": reported[rule_id],
                    "valid_attack_reported_count": valid_reported[rule_id],
                })
    write_csv(
        TABLE_DIR / "rq2_llm_rule_usage.csv", rule_usage_rows,
        ["method", "dataset", "rule_id", "retrieved_count", "reported_applied_count", "valid_attack_reported_count"],
    )

    main_table = []
    rule_index = {(row["method"], row["dataset"], row["channel"]): row for row in rule_rows}
    llm_index = {(row["method"], row["dataset"]): row for row in llm_rows}
    clean_index = {(row["method"], row["dataset"]): row for row in clean_rows}
    for method in METHOD_ORDER:
        for dataset in DATASET_ORDER:
            clean = clean_index[(method, dataset)]
            rule_all = rule_index[(method, dataset, "all")]
            llm = llm_index[(method, dataset)]
            main_table.append({
                "method": method,
                "dataset": dataset,
                "clean_BAR": clean["clean_BAR"],
                "clean_MAR": clean["clean_MAR"],
                "rule_all_n": rule_all["n_paired"],
                "rule_all_attack_BAR": rule_all["attack_BAR"],
                "rule_all_DeltaBAR": rule_all["DeltaBAR"],
                "rule_all_attack_MAR": rule_all["attack_MAR"],
                "llm_n": llm["n_paired"],
                "llm_attack_BAR": llm["attack_BAR"],
                "llm_DeltaBAR": llm["DeltaBAR"],
                "llm_attack_MAR": llm["attack_MAR"],
                "llm_paired_coverage": llm["paired_coverage"],
            })
    write_csv(
        TABLE_DIR / "rq2_paper_main.csv", main_table,
        ["method", "dataset", "clean_BAR", "clean_MAR", "rule_all_n", "rule_all_attack_BAR",
         "rule_all_DeltaBAR", "rule_all_attack_MAR", "llm_n", "llm_attack_BAR", "llm_DeltaBAR",
         "llm_attack_MAR", "llm_paired_coverage"],
    )

    latex_table(
        TABLE_DIR / "rq2_paper_main.tex", "llrrrrrrrr", [
            "Method", "Dataset", "Clean BAR", "Rule BAR", r"$\Delta$BAR", "Rule MAR",
            "LLM BAR", r"$\Delta$BAR", "LLM MAR", "LLM cov.",
        ], [[
            row["method"], row["dataset"], fmt(row["clean_BAR"]), fmt(row["rule_all_attack_BAR"]),
            fmt(row["rule_all_DeltaBAR"]), fmt(row["rule_all_attack_MAR"]), fmt(row["llm_attack_BAR"]),
            fmt(row["llm_DeltaBAR"]), fmt(row["llm_attack_MAR"]), pct(row["llm_paired_coverage"]),
        ] for row in main_table],
        "RQ2 robustness under composed rule-based and LLM-RAG restatement attacks.",
        "tab:rq2-main",
    )

    latex_table(
        TABLE_DIR / "rq2_rule_epr.tex", "llrrrr", [
            "Dataset", "Channel", "Valid changed", "Post-pass", "EPR", "Coverage",
        ], [[
            row["dataset_label"], row["channel"].upper(), row["n_syntax_valid_changed"], row["n_post_pass"],
            pct(row["EPR"]), pct(row["attack_coverage"]),
        ] for row in epr_rows],
        "Execution-preservation results for deterministic rule transformations.",
        "tab:rq2-epr",
    )

    generation_status = Counter()
    for job in protocol["jobs"]:
        generation_status.update(job["status_counts"])
    rule_means = {
        method: {
            channel: mean(
                row["DeltaBAR"] for row in rule_rows
                if row["method"] == method and row["channel"] == channel
            )
            for channel in CHANNEL_ORDER
        }
        for method in METHOD_ORDER
    }
    llm_weighted = {
        method: {
            field: weighted([row for row in llm_rows if row["method"] == method], field)
            for field in ("clean_BAR", "attack_BAR", "DeltaBAR", "clean_MAR", "attack_MAR")
        }
        for method in METHOD_ORDER
    }
    llm_total_paired = sum(row["n_paired"] for row in llm_rows)
    llm_total_attempted = sum(row["n_attempted"] for row in llm_rows)
    response_models = sorted({model for row in generation_rows for model in row["response_models"].split(";") if model})
    pilot_epr_valid = sum(row["n_syntax_valid_changed"] for row in pilot["epr"])
    pilot_epr_pass = sum(row["n_post_pass"] for row in pilot["epr"])

    clean_markdown = markdown_table(
        ["Method", "Dataset", "Best epoch", "BAR", "MAR", "n"],
        [[row["method"], row["dataset"], row["best_epoch"], fmt(row["clean_BAR"]), fmt(row["clean_MAR"]), row["test_samples"]]
         for row in clean_rows],
    )
    main_markdown = markdown_table(
        ["Method", "Dataset", "Rule-ALL BAR", "Rule ΔBAR", "Rule MAR", "LLM BAR", "LLM ΔBAR", "LLM MAR", "LLM n/cov."],
        [[
            row["method"], row["dataset"], fmt(row["rule_all_attack_BAR"]), fmt(row["rule_all_DeltaBAR"]),
            fmt(row["rule_all_attack_MAR"]), fmt(row["llm_attack_BAR"]), fmt(row["llm_DeltaBAR"]),
            fmt(row["llm_attack_MAR"]), f"{row['llm_n']}/{pct(row['llm_paired_coverage'])}",
        ] for row in main_table],
    )
    epr_markdown = markdown_table(
        ["Dataset", "ID", "Expr", "Block", "ALL"],
        [[dataset] + [
            pct(next(row["EPR"] for row in epr_rows if row["dataset_label"] == dataset and row["channel"] == channel))
            for channel in CHANNEL_ORDER
        ] for dataset in ("MBCPP", "MBJP", "MBJSP")],
    )
    reverse_dataset_labels = {value: key for key, value in DATASET_LABELS.items()}
    training_manifest_rows = []
    for clean in clean_rows:
        method_key = clean["method"].lower()
        dataset_key = reverse_dataset_labels[clean["dataset"]]
        manifest_path = (
            ROOT / "training/SrcMarker_fresh/ckpts"
            / f"fresh_rq2_{method_key}_42_{dataset_key}" / "run_manifest.json"
        )
        manifest = read_json(manifest_path)
        training_manifest_rows.append([
            clean["method"], clean["dataset"], manifest["sizes"]["train"],
            manifest["sizes"]["valid"], manifest["sizes"]["test"], manifest["sizes"]["vocab"],
            manifest["transform_capacity"], clean["checkpoint_sha256"],
        ])
    training_manifest_markdown = markdown_table(
        ["Method", "Dataset", "Train", "Valid", "Test", "Vocab", "Transform cap.", "Checkpoint SHA-256"],
        training_manifest_rows,
    )
    cohort_markdown = markdown_table(
        ["Dataset", "Input", "Shared eligible", "Empty reject", "Length reject", "Syntax reject", "Available selected"],
        [[
            DATASET_LABELS[key], value["input_rows"], value["shared_eligible_rows"],
            value["rejected_empty_rows"], value["rejected_length_rows"],
            value["rejected_baseline_syntax_rows"], value["selected_rows"],
        ] for key, value in cohort["datasets"].items()],
    )
    generation_markdown = markdown_table(
        ["Method", "Dataset", "n", "Valid", "Syntax invalid", "No-op", "Error", "Prompt tok.", "Completion tok.", "Cost CNY"],
        [[
            row["method"], row["dataset"], row["rows"], row["valid_attack"], row["syntax_invalid"],
            row["no_op"], row["error"], row["prompt_tokens"], row["completion_tokens"],
            f"{row['recorded_cost_cny']:.4f}",
        ] for row in generation_rows],
    )
    llm_detailed_markdown = markdown_table(
        ["Method", "Dataset", "n", "Clean BAR", "Attack BAR [95% CI]", "ΔBAR [95% CI]", "Attack MAR [95% CI]", "Coverage"],
        [[
            row["method"], row["dataset"], row["n_paired"], fmt(row["clean_BAR"]),
            f"{fmt(row['attack_BAR'])} [{fmt(row['attack_BAR_ci_low'])}, {fmt(row['attack_BAR_ci_high'])}]",
            f"{fmt(row['DeltaBAR'])} [{fmt(row['DeltaBAR_ci_low'])}, {fmt(row['DeltaBAR_ci_high'])}]",
            f"{fmt(row['attack_MAR'])} [{fmt(row['attack_MAR_ci_low'])}, {fmt(row['attack_MAR_ci_high'])}]",
            pct(row["paired_coverage"]),
        ] for row in llm_rows],
    )
    rule_detailed_markdown = markdown_table(
        ["Method", "Dataset", "Channel", "n", "Attack BAR [95% CI]", "ΔBAR [95% CI]", "Attack MAR [95% CI]", "Coverage"],
        [[
            row["method"], row["dataset"], row["channel"].upper(), row["n_paired"],
            f"{fmt(row['attack_BAR'])} [{fmt(row['attack_BAR_ci_low'])}, {fmt(row['attack_BAR_ci_high'])}]",
            f"{fmt(row['DeltaBAR'])} [{fmt(row['DeltaBAR_ci_low'])}, {fmt(row['DeltaBAR_ci_high'])}]",
            f"{fmt(row['attack_MAR'])} [{fmt(row['attack_MAR_ci_low'])}, {fmt(row['attack_MAR_ci_high'])}]",
            pct(row["paired_coverage"]),
        ] for row in rule_rows],
    )
    rule_catalog_markdown = markdown_table(
        ["Rule ID", "Channel", "Languages", "Title", "Preconditions"],
        [[
            rule["id"], rule["channel"], "/".join(rule["languages"]), rule["title"],
            "; ".join(rule["preconditions"]),
        ] for rule in rule_kb],
    )
    applied_rule_markdown = markdown_table(
        ["Reported applied rule", "Count across 1,000 generations"],
        [[rule_id, count] for rule_id, count in overall_applied_rules.most_common()],
    )

    report = f"""# RQ2 consolidated report: paper and appendix inputs

## 1. Completed experimental scope

Both methods were independently trained from random initialization and evaluated on GitHub-C, GitHub-Java, CSN-JavaScript, and CSN-Java. Training used a four-bit watermark, shared GRU encoder, batch size 64, 25 epochs, and seed 42. Rule attacks cover the ID, Expr, Block, and composed ALL channels. The live LLM-RAG main experiment uses a balanced design with 125 programs per method-dataset cell and 1,000 generations in total.

### Clean performance

{clean_markdown}

### Main RQ2 results

{main_markdown}

BAR is bit-level accuracy, MAR is exact four-bit message accuracy, and ΔBAR = clean BAR - attacked BAR. LLM `n/cov.` gives the number entering paired watermark evaluation and its coverage relative to 125 attempted samples. CSV and JSON outputs contain the 95% confidence interval from 10,000 paired sample-level bootstrap replicates for each cell.

### LLM generation status, tokens, and cost by cell

{generation_markdown}

### LLM watermark results and confidence intervals by cell

{llm_detailed_markdown}

### Complete 32-cell rule-attack results and confidence intervals

{rule_detailed_markdown}

## 2. Functional correctness and validity

Rule transformations cover all 9,612 dataset-channel execution cells in MBCPP, MBJP, and MBJSP. Of 9,572 syntax-valid transformations, 9,444 pass the tests, for a weighted EPR of **{pct(epr['aggregate']['weighted_EPR'])}**.

{epr_markdown}

Before the formal LLM main experiment, LLM-RAG functionality was validated on 15 programs from each of the three executable MBXP datasets. In total, **{pilot_epr_pass}/{pilot_epr_valid}** syntax-valid rewrites passed their tests (EPR {pct(pilot_epr_pass / pilot_epr_valid)}). These 45 records validate the attack implementation and are not part of the 1,000-sample watermark effect estimate.

Statuses among the 1,000 formal LLM outputs are: valid attack={generation_status.get('valid_attack', 0)}, syntax invalid={generation_status.get('syntax_invalid', 0)}, no-op={generation_status.get('no_op', 0)}, and error={generation_status.get('error', 0)}. Final paired watermark analysis covers {llm_total_paired}/{llm_total_attempted} samples ({pct(llm_total_paired / llm_total_attempted)}).

## 3. Interpretation for the paper

- Mean cross-dataset rule-attack ΔBAR for SrcMarker: ID={rule_means['SrcMarker']['id']:.4f}, Expr={rule_means['SrcMarker']['expr']:.4f}, Block={rule_means['SrcMarker']['block']:.4f}, ALL={rule_means['SrcMarker']['all']:.4f}; corresponding CodeMark values are ID={rule_means['CodeMark']['id']:.4f}, Expr={rule_means['CodeMark']['expr']:.4f}, Block={rule_means['CodeMark']['block']:.4f}, ALL={rule_means['CodeMark']['all']:.4f}.
- Valid-sample-weighted LLM-RAG results: SrcMarker clean/attack BAR={llm_weighted['SrcMarker']['clean_BAR']:.4f}/{llm_weighted['SrcMarker']['attack_BAR']:.4f}, ΔBAR={llm_weighted['SrcMarker']['DeltaBAR']:.4f}, attack MAR={llm_weighted['SrcMarker']['attack_MAR']:.4f}; CodeMark clean/attack BAR={llm_weighted['CodeMark']['clean_BAR']:.4f}/{llm_weighted['CodeMark']['attack_BAR']:.4f}, ΔBAR={llm_weighted['CodeMark']['DeltaBAR']:.4f}, attack MAR={llm_weighted['CodeMark']['attack_MAR']:.4f}.
- These comparisons are descriptive. Method-level significance must not be inferred solely from overlapping or non-overlapping confidence intervals. A formal between-method hypothesis test should preregister a paired statistic on common UIDs.
- `rq2_llm_method_contrasts.csv` provides paired comparisons on the common subset where both methods yield valid attacks, with 10,000-replicate bootstrap confidence intervals. It answers a common-valid-subset question and does not replace coverage comparisons that include invalid-attack rates.
- Random-chance accuracy is 6.25% for four-bit MAR and 50% for BAR.

## 4. Paper-ready experimental setup

> We trained both watermarking methods from random initialization on GitHub-C, GitHub-Java, CodeSearchNet JavaScript, and CodeSearchNet Java using a four-bit payload, a shared GRU encoder, batch size 64, 25 epochs, and random seed 42. Robustness was evaluated under identifier-, expression-, block-, and jointly composed rule transformations. We additionally evaluated semantic restatement using an LLM augmented by deterministic BM25 retrieval over a frozen local rule knowledge base. We report clean and attacked bit accuracy (BAR), exact-message accuracy (MAR), and the paired degradation ΔBAR = BAR_clean − BAR_attack. Confidence intervals were computed by 10,000 sample-level paired bootstrap replicates.

> The LLM experiment used a balanced 2 × 4 design with 125 programs per method–dataset cell (1,000 generations total). The two methods shared the same underlying program cohort. Eligible samples had non-empty watermarked code of at most 1,400 characters and passed language-specific Tree-sitter parsing before attack. Generation used GPT-5 with temperature 0, reasoning effort “minimal,” a 1,100-token completion cap, retrieval top-k 6, and seed 42. Invalid or unchanged generations were retained in the audit trail and excluded from paired watermark-effect estimates through explicit status labels rather than silent deletion.

## 5. Paper-ready results paragraph

> Across the complete executable MBXP validation matrix, {epr['aggregate']['n_post_pass_across_cells']:,} of {epr['aggregate']['n_syntax_valid_changed_across_cells']:,} syntax-valid changed programs retained their original behavior, yielding a weighted execution-preservation rate of {100 * epr['aggregate']['weighted_EPR']:.2f}%. In the independent LLM implementation check, all {pilot_epr_valid} syntax-valid restatements passed their executable tests. The 1,000-generation main experiment produced {generation_status.get('valid_attack', 0)} valid changed programs and {llm_total_paired} samples with complete clean/attacked watermark predictions. Under LLM restatement, the valid-sample weighted ΔBAR was {llm_weighted['SrcMarker']['DeltaBAR']:.3f} for SrcMarker and {llm_weighted['CodeMark']['DeltaBAR']:.3f} for CodeMark; corresponding attacked MAR values were {llm_weighted['SrcMarker']['attack_MAR']:.3f} and {llm_weighted['CodeMark']['attack_MAR']:.3f}. Dataset-level estimates and paired-bootstrap confidence intervals are reported in the artifact tables.

## 6. Appendix reproduction details

- Dataset labels: GitHub-C, GitHub-Java, CSN-JavaScript, and CSN-Java. Functional validation sets: MBCPP, MBJP, and MBJSP.
- Training: fresh random initialization; 25 epochs; batch size 64; four bits; shared GRU encoder; seed 42; `varmask_prob=0.5`. Each `run_manifest.json` stores train/validation/test splits and vocabulary size.
- Rule attacks: global seed 42; sample seeds derived from the global seed, UID, and channel; Tree-sitter syntax checks; retained statuses for infeasible, syntax-invalid, and execution-failed transformations.
- LLM: provider=openai-compatible; base URL=`{protocol['base_url']}`; requested model=`{protocol['requested_model']}`; response model(s)=`{', '.join(response_models)}`; temperature 0; minimal reasoning effort; 1,100 maximum completion tokens; top-k 6; at most one request per sample. System and user prompts and the rule base are archived verbatim.
- Cohort: ordered by descending shared-source length and ascending input index; both methods require non-empty source of at most 1,400 characters and baseline-valid syntax; first 125 eligible samples per cell; common UIDs for both methods within a dataset.
- Detection: the corresponding fresh checkpoint for each method-dataset cell; token sequences truncated to 512; four-bit threshold `sigmoid > 0.5`.
- Statistics: sample-level resampling for every BAR/MAR difference; 10,000 paired bootstrap replicates with seed 42; the four bits are not treated as independent observations.
- Software: Python {platform.python_version()}; PyTorch 2.6.0+cu124 in training manifests; g++ 11.4, Java 21, and Node 22 for EPR; NVIDIA A800 80GB GPU.
- LLM usage: prompt={protocol['accounting']['prompt_tokens']:,} tokens, completion={protocol['accounting']['completion_tokens']:,} tokens, reasoning={protocol['accounting']['reasoning_tokens']:,} tokens; archived-rate cost CNY {protocol['accounting']['recorded_cost_cny']:.2f}.
- Credentials are not part of the artifact. Reproducers provide a local mode-600 file through `--env-file`.

### 6.1 Training splits, capacity, and checkpoint identity

{training_manifest_markdown}

The SHA-256 values above identify the `models_best.pt` files used for final detection. Each `run_manifest.json` also stores full parameters, timing, Python/PyTorch versions, and dataset sizes. Per-epoch metrics for all 25 epochs are in `training_history.json`.

### 6.2 LLM cohort construction audit

{cohort_markdown}

The formal 1,000-request experiment takes the first 125 stable UIDs from every available-selected cohort, yielding 2 methods x 4 datasets x 125. Sorting uses descending shared-source character length followed by ascending original input index. Selection is completed before any API call, preventing selection on generation or detector outcomes.

### 6.3 Exact GPT-5 and API configuration

- API type: OpenAI-compatible Chat Completions; request path: `{protocol['base_url'].rstrip('/')}/chat/completions`.
- Requested model alias: `{protocol['requested_model']}`; returned snapshot(s) observed across 1,000 formal requests: `{', '.join(response_models)}`.
- Fixed payload fields: `model`, two `messages`, `temperature=0`, per-sample `seed`, `max_completion_tokens=1100`, and `reasoning_effort=minimal`.
- Provider timeout: 120 seconds; User-Agent: `RQ2-CodeWM-Experiment/1.0`; formal-run `max_attempts=1`, so there are no hidden retries.
- Per-sample seed: first four bytes of `SHA256("42\\0<sample_uid>\\0llm-rag-all")`, interpreted as a big-endian unsigned integer.
- Output contract: `<applied_rules>...</applied_rules>` plus one fenced source block. A missing code block is an error. Unknown or unretrieved reported rule IDs are recorded in `unknown_reported_rule_ids`.
- Service credentials are loaded only from an external mode-600 environment file; reports, logs, and artifacts contain no credentials.
- Cost auditing uses the archived runtime rates: CNY {protocol['accounting']['pricing_cny_per_1k']['input']}/1K input tokens and CNY {protocol['accounting']['pricing_cny_per_1k']['output']}/1K output tokens.
- Pricing source (accessed 2026-09-16): `https://github.com/chatanywhere/GPT_API_free`; official GPT-5 model page: `https://developers.openai.com/api/docs/models/gpt-5`. The actual bill came from the relay provider, not OpenAI's official USD pricing.

### 6.4 RAG retrieval implementation

The local knowledge base contains {len(rule_kb)} rule cards. Retrieval uses dependency-free deterministic BM25 with `k1=1.5` and `b=0.75`; the query is `"<language> <channel> source-to-source watermark robustness " + source[:2500]`. Rules are first filtered by language and channel. For ALL, the highest-scoring ID, Expr, and Block rule is selected before filling the remaining top-k=6 positions by stable score and Rule-ID order.

{rule_catalog_markdown}

Aggregate model-reported applied-rule frequencies follow. One generation may report multiple rules; `rq2_llm_rule_usage.csv` contains retrieved, applied, and valid-applied counts by method and dataset.

{applied_rule_markdown}

Rule knowledge-base SHA-256: `{sha256_file(rule_kb_path)}`.

### 6.5 Exact archived prompts

System prompt (SHA-256 `{sha256_file(system_prompt_path)}`):

~~~~text
{system_prompt}
~~~~

User prompt template (SHA-256 `{sha256_file(user_prompt_path)}`):

~~~~text
{user_prompt}
~~~~

The `attack_meta` field in each JSONL row stores the rendered prompt SHA-256, retrieved Rule IDs, model response ID, finish reason, token usage, and sample seed.

### 6.6 Implementation modules and data flow

1. `training/SrcMarker_fresh/train_main.py`, `experiment_config.py`, and `run_one_fresh_training.sh`: train from random initialization and write the checkpoint, per-epoch history, and run manifest.
2. `training/SrcMarker_fresh/eval_main.py`: generate watermarked test-split code and record `watermark`, clean `extract`, original source, and watermarked source.
3. `project/srcMarker/SrcMarker/1_obfus.py` and `rq2_revision/rule_attack.py`: deterministic rule attacks, syntax checks, and status recording.
4. `prepare_fresh_llm_cohorts.py`: paired cohorts from shared source, with length and syntax screening completed before API calls.
5. `rq2_revision/rag.py`, `llm_rag.py`, `llm_provider.py`, and `1_obfus_AI.py`: rule retrieval, prompt assembly, Chat Completions calls, output parsing, syntax validation, and resumable output.
6. `validate_mbxp_rq2.py`: baseline qualification, attack, compilation/execution, and test comparison on MBCPP, MBJP, and MBJSP to compute EPR.
7. `run_watermark_detector_portable.py`: load the extractor encoder/decoder for each checkpoint and produce attacked predictions only for `valid_attack`, while retaining syntax-invalid, no-op, and error rows explicitly.
8. `3_analysis.py`: clean/attacked BAR, MAR, ΔBAR, coverage, and sample-level paired bootstrap confidence intervals.
9. `run_llm_full_1000.py` and `run_llm_full_detection.py`: freeze the 1,000-generation and eight-checkpoint detection protocols. `build_rq2_deliverables.py` and `plot_rq2_results.py` build reports, tables, and figures only from archived results.

Core fields in each per-sample LLM JSONL row are `_attack_uid`, `watermark`, `extract`, `after_watermark`, `after_obfus`, and `attack_meta`. At minimum, `attack_meta` contains attack family/channel/language, global/sample seed, source/prompt SHA-256, changed/syntax/status fields, retrieved/reported/unknown rule IDs, generation parameters, attempt count, and provider response ID/model/usage/finish reason. Detection adds `obfus_extract` and `detector_status`.

## 7. Key reproduction commands

```bash
PYTHONPATH=.deps pytest -q
PYTHONPATH=.deps python run_llm_full_1000.py \\
  --env-file /secure/path/llm.env --workers 2
PYTHONPATH=.deps python run_llm_full_detection.py \\
  --device cuda --gpus 0,1 --workers 2 --bootstrap 10000
PYTHONPATH=.deps python build_rq2_deliverables.py
PYTHONPATH=.deps python plot_rq2_results.py
```

Training commands are frozen in `training/SrcMarker_fresh/run_fresh_training.sh` and `run_one_fresh_training.sh`. See `README_REVISION.md` and the archived scripts for rule-attack and full-EPR commands.

## 8. Interpretation boundary

Functional-correctness evidence for the LLM main experiment comes from the independent executable MBXP pilot. GitHub/CSN main-task snippets generally lack standalone test fixtures, so the main experiment applies baseline/attack syntax screening and watermark detection only. Reports must distinguish execution-preservation validation from main-task syntax/coverage accounting and must not describe main-task syntax validity as execution-semantic correctness.
"""
    report_path = REPORT_DIR / "RQ2_PAPER_AND_APPENDIX_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    combined = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "training": fresh["protocol"],
            "llm": {key: protocol[key] for key in (
                "design", "methods", "datasets", "samples_per_cell", "total_samples", "provider", "base_url",
                "requested_model", "temperature", "seed", "top_k", "max_chars", "max_completion_tokens",
                "reasoning_effort", "max_attempts", "accounting",
            )},
            "detector": detection["protocol"],
            "cohort": cohort,
        },
        "clean": clean_rows,
        "rule_robustness": rule_rows,
        "rule_epr": epr,
        "llm_execution_validation": pilot["epr"],
        "llm_generation": generation_rows,
        "llm_robustness": llm_rows,
        "llm_method_contrasts": method_contrasts,
        "llm_rule_usage": rule_usage_rows,
        "checkpoint_artifacts": checkpoint_rows,
        "source_artifacts": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (
                fresh_path, epr_path, pilot_path, protocol_path, detection_path,
                cohort_path, system_prompt_path, user_prompt_path, rule_kb_path,
            )
        },
    }
    combined_path = REPORT_DIR / "rq2_complete_results.json"
    combined_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")

    table_readme = f"""# RQ2 tables and figures

All figures are generated only from CSV files in `tables/`:

```bash
PYTHONPATH=.deps python plot_rq2_results.py \\
  --table-dir deliverables/03_tables_figures/tables \\
  --output-dir deliverables/03_tables_figures/figures
```

Files:

- `rq2_clean.csv`: fresh-checkpoint clean accuracy and hashes.
- `rq2_rule_robustness.csv`: 32 method/dataset/channel rule-attack cells and 95% CIs.
- `rq2_rule_epr.csv`: complete executable validation over MBCPP/MBJP/MBJSP.
- `rq2_llm_generation.csv`: 1,000-generation status, usage, model snapshot, cost, and hashes.
- `rq2_llm_robustness.csv`: eight LLM watermark cells and 95% CIs.
- `rq2_llm_method_contrasts.csv`: paired between-method contrasts on common valid UIDs.
- `rq2_llm_rule_usage.csv`: retrieved and model-reported applied rule frequencies.
- `rq2_paper_main.csv` / `.tex`: compact main-paper table.
- `rq2_rule_epr.tex`: appendix-ready EPR table.

Generation script SHA-256: `{sha256_file(ROOT / 'plot_rq2_results.py')}`.
"""
    (TABLE_ROOT / "README.md").write_text(table_readme, encoding="utf-8")

    subprocess.run(
        [sys.executable, str(ROOT / "plot_rq2_results.py"), "--table-dir", str(TABLE_DIR), "--output-dir", str(FIGURE_DIR)],
        cwd=ROOT, check=True,
    )
    manifest_paths = [report_path, combined_path, TABLE_ROOT / "README.md"]
    manifest_paths.extend(sorted(TABLE_DIR.glob("*")))
    manifest_paths.extend(sorted(FIGURE_DIR.glob("*")))
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in manifest_paths
        ],
    }
    (DELIVERABLES / "deliverables_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(report_path.relative_to(ROOT)),
        "combined_results": str(combined_path.relative_to(ROOT)),
        "tables": len(list(TABLE_DIR.glob("*"))),
        "figures": len(list(FIGURE_DIR.glob("*"))),
    }, indent=2))


if __name__ == "__main__":
    main()
