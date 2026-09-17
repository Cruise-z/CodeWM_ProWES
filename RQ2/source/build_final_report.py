#!/usr/bin/env python3
"""Build the final RQ2 JSON/CSV/Markdown artifacts from completed runs."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
FINAL = OUT / "final"
DATASETS = {
    "csn_java": "CSN-Java",
    "csn_js": "CSN-JavaScript",
    "github_c_funcs": "GitHub-C",
    "github_java_funcs": "GitHub-Java",
}
CHANNELS = ["id", "expr", "block", "all"]
METHODS = ["codemark", "srcmarker"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metric_record(method, dataset, channel, metrics, evidence):
    return {
        "method": method,
        "dataset": dataset,
        "dataset_label": DATASETS[dataset],
        "channel": channel,
        "evidence": evidence,
        **metrics,
    }


def pct(value):
    return "–" if value is None else f"{100 * value:.2f}%"


def ci_pct(values):
    return "–" if values is None else f"[{100 * values[0]:.2f}%, {100 * values[1]:.2f}%]"


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(out)


def main():
    FINAL.mkdir(parents=True, exist_ok=True)

    revised_metrics = []
    for dataset in DATASETS:
        for channel in CHANNELS:
            path = OUT / "metrics" / f"srcmarker_{dataset}_{channel}.json"
            revised_metrics.append(metric_record(
                "SrcMarker", dataset, channel, load_json(path), "revised_end_to_end",
            ))

    archived_metrics = []
    for method in METHODS:
        for dataset in ["csn_js", "github_c_funcs", "github_java_funcs"]:
            for channel in CHANNELS:
                path = OUT / "archive_metrics" / f"{method}_{dataset}_{channel}.json"
                archived_metrics.append(metric_record(
                    "CodeMark" if method == "codemark" else "SrcMarker",
                    dataset, channel, load_json(path), "workspace_archived_output_reanalysis",
                ))

    validity = []
    for method in METHODS:
        datasets = ["csn_js", "github_c_funcs", "github_java_funcs"]
        if method == "srcmarker":
            datasets = ["csn_java"] + datasets
        for dataset in datasets:
            for channel in CHANNELS:
                path = OUT / "rule" / f"{method}_{dataset}_{channel}.jsonl"
                rows = load_jsonl(path)
                statuses = Counter(r.get("attack_meta", {}).get("status", "unclassified") for r in rows)
                operator_statuses = Counter(
                    op.get("status", "unknown")
                    for r in rows for op in r.get("attack_meta", {}).get("operators", [])
                )
                applied_keys = Counter(
                    key for r in rows for key in r.get("attack_meta", {}).get("applied_keys", [])
                )
                validity.append({
                    "method": "CodeMark" if method == "codemark" else "SrcMarker",
                    "dataset": dataset,
                    "dataset_label": DATASETS[dataset],
                    "channel": channel,
                    "n_attempted": len(rows),
                    "status_counts": dict(statuses),
                    "valid_attack_rate": statuses["valid_attack"] / len(rows) if rows else None,
                    "syntax_invalid_rate": statuses["syntax_invalid"] / len(rows) if rows else None,
                    "operator_status_counts": dict(operator_statuses),
                    "applied_key_counts": dict(sorted(applied_keys.items())),
                    "seed": 42,
                })

    mbxp = [load_json(p) for p in sorted((OUT / "mbxp_sanity").glob("*_summary.json"))]

    llm_mock = []
    for path in sorted((OUT / "llm_rag_mock_sanity").glob("*.jsonl")):
        rows = load_jsonl(path)
        statuses = Counter(r.get("attack_meta", {}).get("status", "unclassified") for r in rows)
        llm_mock.append({
            "name": path.stem,
            "n": len(rows),
            "status_counts": dict(statuses),
            "all_have_prompt_hash": all(bool(r.get("attack_meta", {}).get("prompt_sha256")) for r in rows),
            "all_have_retrieved_rules": all(bool(r.get("attack_meta", {}).get("retrieved_rule_ids")) for r in rows),
            "provider": "mock_identity_pipeline_check",
        })

    # Values transcribed from Table IX in the bundled manuscript. They are reference
    # evidence only, because the package contains neither those generated rows nor an
    # operational LLM provider configuration in this environment.
    llm_reference = []
    reference_values = {
        "CodeMark": {"clean": (0.971, 0.921), "id": (0.558, 0.142),
                     "expr": (0.969, 0.918), "block": (0.970, 0.916), "all": (0.543, 0.117)},
        "SrcMarker": {"clean": (0.986, 0.961), "id": (0.580, 0.158),
                      "expr": (0.968, 0.927), "block": (0.962, 0.904), "all": (0.562, 0.134)},
    }
    for method, values in reference_values.items():
        for channel in CHANNELS:
            clean_bar, clean_mar = values["clean"]
            attack_bar, attack_mar = values[channel]
            llm_reference.append({
                "method": method, "dataset": "csn_java", "dataset_label": "CSN-Java",
                "channel": channel, "n": 1000, "clean_BAR": clean_bar,
                "attack_BAR": attack_bar, "DeltaBAR": clean_bar - attack_bar,
                "clean_MAR": clean_mar, "attack_MAR": attack_mar,
                "evidence": "bundled_manuscript_table_ix_not_rerun",
            })

    package_inputs = ROOT / "project" / "srcMarker" / "testResult"
    input_checksums = {p.name: sha256_file(p) for p in sorted(package_inputs.glob("*.jsonl"))}
    checkpoint_root = Path("/home/zhaorz/project/CodeWM/SrcMarker/ckpts")
    checkpoint_paths = [
        checkpoint_root / "4bit_gru_srcmarker_42_csn_java_SrcMarker/models_best.pt",
        checkpoint_root / "4bit_gru_srcmarker_42_csn_js_SrcMarker/models_best.pt",
        checkpoint_root / "4bit_gru_srcmarker_42_github_c_funcs_SrcMarker/models_best.pt",
        checkpoint_root / "4bit_gru_srcmarker_42_github_java_funcs_SrcMarker/models_best.pt",
    ]
    checkpoint_checksums = {str(p): sha256_file(p) for p in checkpoint_paths}
    parser_path = ROOT / "cStyleLang" / "parser" / "languages.so"
    environment = {
        "python": platform.python_version(),
        "seed": 42,
        "n_bits": 4,
        "chance_BAR": 0.5,
        "chance_MAR": 0.0625,
        "bootstrap_replicates": 10000,
        "bootstrap_method": "paired sample-level percentile 95% CI",
        "tree_sitter_parser_sha256": sha256_file(parser_path),
        "input_sha256": input_checksums,
        "checkpoint_sha256": checkpoint_checksums,
        "detector_device": "cpu",
        "codeMark_checkpoint_available": False,
        "llm_provider_available": False,
        "dynamic_runtime_availability": {"cpp_g++": True, "java_javac": False, "javascript_node": False},
        "determinism_check": load_json(OUT / "verification" / "determinism.json"),
    }

    complete = {
        "configuration": environment,
        "revised_end_to_end_rule_metrics": revised_metrics,
        "revised_rule_validity": validity,
        "archived_two_method_reanalysis": archived_metrics,
        "mbxp_cpp_sanity": mbxp,
        "llm_rag_mock_pipeline_checks": llm_mock,
        "llm_rag_manuscript_reference_only": llm_reference,
    }
    (FINAL / "rq2_results.json").write_text(json.dumps(complete, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (FINAL / "environment.json").write_text(json.dumps(environment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    metric_fields = ["evidence", "method", "dataset", "dataset_label", "channel", "n_paired",
                     "clean_BAR", "attack_BAR", "DeltaBAR", "clean_MAR", "attack_MAR",
                     "chance_BAR", "chance_MAR", "paired_coverage", "bootstrap_95CI"]
    with (FINAL / "robustness_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=metric_fields, extrasaction="ignore")
        writer.writeheader()
        for rec in revised_metrics + archived_metrics:
            row = dict(rec); row["bootstrap_95CI"] = json.dumps(row.get("bootstrap_95CI"), sort_keys=True)
            writer.writerow(row)

    validity_fields = ["method", "dataset", "dataset_label", "channel", "n_attempted",
                       "valid_attack_rate", "syntax_invalid_rate", "status_counts",
                       "operator_status_counts", "applied_key_counts", "seed"]
    with (FINAL / "validity_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=validity_fields, extrasaction="ignore")
        writer.writeheader()
        for rec in validity:
            row = dict(rec)
            for key in ["status_counts", "operator_status_counts", "applied_key_counts"]:
                row[key] = json.dumps(row[key], sort_keys=True)
            writer.writerow(row)

    with (FINAL / "llm_rag_reference_only.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(llm_reference[0]))
        writer.writeheader(); writer.writerows(llm_reference)

    revised_rows = []
    for r in revised_metrics:
        ci = r["bootstrap_95CI"]
        revised_rows.append([
            r["dataset_label"], r["channel"].upper(), r["n_paired"], pct(r["clean_BAR"]),
            pct(r["attack_BAR"]), pct(r["DeltaBAR"]), pct(r["attack_MAR"]),
            ci_pct(ci["attack_BAR"]), ci_pct(ci["DeltaBAR"]),
        ])
    archived_rows = []
    for r in archived_metrics:
        archived_rows.append([
            r["method"], r["dataset_label"], r["channel"].upper(), r["n_paired"],
            pct(r["clean_BAR"]), pct(r["attack_BAR"]), pct(r["DeltaBAR"]), pct(r["attack_MAR"]),
        ])
    validity_rows = []
    for r in validity:
        c = r["status_counts"]
        validity_rows.append([
            r["method"], r["dataset_label"], r["channel"].upper(), r["n_attempted"],
            c.get("valid_attack", 0), c.get("no_op", 0), c.get("syntax_invalid", 0),
            c.get("execution_invalid", 0), c.get("error", 0), pct(r["valid_attack_rate"]),
        ])
    llm_rows = [[r["method"], r["channel"].upper(), r["n"], pct(r["clean_BAR"]),
                 pct(r["attack_BAR"]), pct(r["DeltaBAR"]), pct(r["attack_MAR"])] for r in llm_reference]
    mbxp_rows = [[r["channel"].upper(), r["n_total"], r["n_baseline_pass"], r["n_changed"],
                  r["n_syntax_valid_changed"], r["n_post_pass"], pct(r["EPR_given_valid_changed"])]
                 for r in mbxp]

    report = f"""# RQ2 experiment results

Generation configuration: four-bit payload, seed 42, 50% random-chance BAR, and 6.25% random-chance MAR. Confidence intervals are percentile 95% intervals from 10,000 paired sample-level bootstrap replicates.

## Revised rule attack: end-to-end SrcMarker results

{table(["Dataset", "Channel", "N", "Clean BAR", "Attack BAR", "DeltaBAR", "Attack MAR", "Attack BAR 95% CI", "DeltaBAR 95% CI"], revised_rows)}

## Reanalysis of archived workspace results for both methods

The following values were recomputed from the workspace's existing per-sample `watermark/extract/obfus_extract` fields using BAR, MAR, DeltaBAR, and paired bootstrap throughout. They are not presented as outputs of the revised attack implementation.

{table(["Method", "Dataset", "Channel", "N", "Clean BAR", "Attack BAR", "DeltaBAR", "Attack MAR"], archived_rows)}

## Revised rule-attack validity

Non-MBXP data do not provide executable tests, so only static syntax validity is reported here; dynamic execution remains unassessed.

{table(["Method", "Dataset", "Channel", "Attempts", "Valid", "No-op", "Syntax invalid", "Execution invalid", "Error", "Valid rate"], validity_rows)}

## MBXP C++ dynamic validation (sanity gate)

{table(["Channel", "Total", "Baseline pass", "Changed", "Syntax-valid changed", "Post-pass", "EPR"], mbxp_rows)}

## LLM + RAG

The local environment completed an offline RAG-pipeline check for both methods and four channels with 20 samples per cell. Every row records a prompt hash and retrieved rule IDs. The mock provider returns a no-op by design and is therefore not treated as attack-performance evidence. This earlier environment had neither an OpenAI-compatible API key nor the legacy `aiAPI` client in the workspace or on PyPI, so it could not produce compliant live-LLM per-sample rewrites.

The following table transcribes the bundled paper's Table IX (CSN-Java, 1,000 samples) for reference only; it is not evidence from this rerun:

{table(["Method", "Channel", "N", "Clean BAR", "Attack BAR", "DeltaBAR", "Attack MAR"], llm_rows)}

## Integrity and limitations

- Every entry in the outer package's `MANIFEST_SHA256.txt` passed verification.
- A 20-sample deterministic rerun is byte-identical to the first 20 full-run outputs, with SHA-256 `{environment['determinism_check']['rerun_sha256']}`.
- The revised SrcMarker rule attack completed the full attack, CPU extraction, and 10,000 bootstrap replicates. Revised CodeMark attacks and metadata are complete, but that workspace did not include its detector checkpoint and therefore cannot support trustworthy re-extraction for the revised outputs.
- The archive did not contain the CodeMark/CSN-Java input, so revised CodeMark validity covers the three datasets that were actually available.
- Dynamic EPR in that environment was available only for C++ through g++; Java and JavaScript dynamic validation was not claimed because `javac` and Node were unavailable.
- BFR is not reported.
"""
    (FINAL / "RQ2_RESULTS.md").write_text(report, encoding="utf-8")

    artifacts = sorted(p for p in FINAL.iterdir() if p.name != "SHA256SUMS")
    sums = "".join(f"{sha256_file(p)}  {p.name}\n" for p in artifacts)
    (FINAL / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(f"wrote {len(artifacts) + 1} final artifacts to {FINAL}")


if __name__ == "__main__":
    main()
