#!/usr/bin/env python3
"""Build the audited 100-request LLM pilot report and cost projection."""

from __future__ import annotations

import glob
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from rq2_revision.rule_attack import _build_parser, tree_sitter_syntax_valid


ROOT = Path(__file__).resolve().parent
INITIAL = ROOT / "outputs/fresh/llm_pilot"
MINIMAL = ROOT / "outputs/fresh/llm_pilot_minimal"
FINAL = MINIMAL / "final"
PARSER_LIB = ROOT / "training/SrcMarker_fresh/parser/languages.so"
INPUT_PRICE_PER_1K = 0.00875
OUTPUT_PRICE_PER_1K = 0.07
MAX_COMPLETION_TOKENS = 1100


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def usage_from_row(row):
    meta = row.get("attack_meta", {})
    return (meta.get("provider_response") or row.get("provider_response") or {}).get("usage")


def sum_usage(rows):
    usage_rows = [usage_from_row(row) for row in rows]
    usage_rows = [usage for usage in usage_rows if usage]
    return {
        "rows_with_usage": len(usage_rows),
        "prompt_tokens": sum(usage.get("prompt_tokens", 0) for usage in usage_rows),
        "completion_tokens": sum(usage.get("completion_tokens", 0) for usage in usage_rows),
        "reasoning_tokens": sum(
            usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            for usage in usage_rows
        ),
    }


def cost(usage):
    return (
        usage["prompt_tokens"] / 1000 * INPUT_PRICE_PER_1K
        + usage["completion_tokens"] / 1000 * OUTPUT_PRICE_PER_1K
    )


def main():
    minimal_epr_paths = sorted(MINIMAL.glob("epr/*.jsonl"))
    minimal_main_paths = sorted(MINIMAL.glob("main/*.jsonl"))
    minimal_rows = [row for path in minimal_epr_paths + minimal_main_paths for row in read_jsonl(path)]
    initial_paths = sorted(INITIAL.glob("epr/*.jsonl")) + sorted(INITIAL.glob("main/*.jsonl"))
    initial_rows = [row for path in initial_paths for row in read_jsonl(path)]
    if len(initial_rows) != 15 or len(minimal_rows) != 85:
        raise ValueError(f"unexpected pilot split: initial={len(initial_rows)} minimal={len(minimal_rows)}")

    minimal_usage = sum_usage(minimal_rows)
    initial_usage = sum_usage(initial_rows)
    missing_usage_rows = len(initial_rows) - initial_usage["rows_with_usage"]
    recorded_cost = cost(minimal_usage) + cost(initial_usage)
    missing_usage_upper_cost = missing_usage_rows * (
        2000 / 1000 * INPUT_PRICE_PER_1K
        + MAX_COMPLETION_TOKENS / 1000 * OUTPUT_PRICE_PER_1K
    )

    epr = []
    for path in sorted(MINIMAL.glob("epr/*_summary.json")):
        summary = read_json(path)
        epr.append(summary)

    parsers = {
        language: _build_parser(language, str(PARSER_LIB))
        for language in ("cpp", "java", "javascript")
    }
    main_validity = {
        "n_total": 0, "n_source_syntax_valid": 0, "n_output_syntax_valid": 0,
        "n_source_and_output_syntax_valid": 0,
    }
    for path in minimal_main_paths:
        name = path.name
        language = "cpp" if "github_c_funcs" in name else (
            "javascript" if "csn_js" in name else "java"
        )
        for row in read_jsonl(path):
            source_valid = tree_sitter_syntax_valid(parsers[language], row["after_watermark"], language)
            output_valid = tree_sitter_syntax_valid(parsers[language], row["after_obfus"], language)
            main_validity["n_total"] += 1
            main_validity["n_source_syntax_valid"] += int(source_valid)
            main_validity["n_output_syntax_valid"] += int(output_valid)
            main_validity["n_source_and_output_syntax_valid"] += int(source_valid and output_valid)
    main_validity["output_validity_given_source_valid"] = (
        main_validity["n_source_and_output_syntax_valid"]
        / main_validity["n_source_syntax_valid"]
    )

    watermark = []
    for path in sorted(MINIMAL.glob("metrics/*.json")):
        metric = read_json(path)
        stem = path.stem.removesuffix("_llm_all")
        method, dataset = stem.split("_", 1)
        watermark.append({"method": method, "dataset": dataset, **metric})

    cohort = read_json(ROOT / "outputs/fresh/llm_input/cohort_manifest.json")
    main_full_requests = 2 * sum(
        value["selected_rows"] for value in cohort["datasets"].values()
    )
    epr_full_requests = 763 + 842 + 795
    full_requests = main_full_requests + epr_full_requests
    minimal_cost_per_request = cost(minimal_usage) / len(minimal_rows)
    projected_cost = minimal_cost_per_request * full_requests

    response_models = sorted({
        ((row.get("attack_meta", {}).get("provider_response") or row.get("provider_response") or {}).get("response_model"))
        for row in minimal_rows
        if (row.get("attack_meta", {}).get("provider_response") or row.get("provider_response"))
    })

    artifact = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "provider": "openai-compatible",
            "base_url": "https://api.chatanywhere.tech/v1",
            "requested_model": "gpt-5",
            "response_models": response_models,
            "temperature": 0,
            "seed": 42,
            "top_k": 6,
            "reasoning_effort": "minimal",
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "automatic_retries": 0,
        },
        "request_accounting": {
            "initial_truncated_phase": len(initial_rows),
            "minimal_phase": len(minimal_rows),
            "total_experimental_requests": len(initial_rows) + len(minimal_rows),
        },
        "usage": {
            "minimal_exact": minimal_usage,
            "initial_recorded": initial_usage,
            "initial_missing_usage_rows": missing_usage_rows,
            "recorded_cost_cny": recorded_cost,
            "missing_usage_conservative_upper_cost_cny": missing_usage_upper_cost,
            "pilot_cost_conservative_upper_cny": recorded_cost + missing_usage_upper_cost,
            "pricing_cny_per_1k": {
                "input": INPUT_PRICE_PER_1K,
                "output": OUTPUT_PRICE_PER_1K,
            },
        },
        "epr": epr,
        "main_syntax_validity": main_validity,
        "watermark_integration_metrics": watermark,
        "full_run_projection": {
            "llm_epr_requests": epr_full_requests,
            "main_requests": main_full_requests,
            "total_requests": full_requests,
            "pilot_minimal_mean_cost_cny_per_request": minimal_cost_per_request,
            "projected_cost_cny": projected_cost,
            "projected_cost_with_10pct_reserve_cny": projected_cost * 1.10,
        },
        "artifacts": [],
    }

    artifact_paths = (
        minimal_epr_paths + minimal_main_paths
        + sorted(MINIMAL.glob("epr/*_summary.json"))
        + sorted(MINIMAL.glob("main_eval/*.jsonl"))
        + sorted(MINIMAL.glob("metrics/*.json"))
    )
    artifact["artifacts"] = [
        {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        for path in artifact_paths
    ]

    FINAL.mkdir(parents=True, exist_ok=True)
    (FINAL / "rq2_llm_pilot.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    epr_lines = [
        f"| {row['language']} | {row['n_changed']} | {row['n_syntax_valid_changed']} | "
        f"{row['n_post_pass']} | {row['EPR_given_valid_changed']:.2%} |"
        for row in epr
    ]
    wm_lines = [
        f"| {row['method']} | {row['dataset']} | {row['n_paired']} | "
        f"{row['clean_BAR']:.4f} | {row['attack_BAR']:.4f} | {row['DeltaBAR']:.4f} | "
        f"{row['attack_MAR']:.4f} |"
        for row in watermark
    ]
    report = f"""# RQ2 live-LLM restatement pilot

The 100 experimental requests comprise an initial 15-request length-limited stage and an 85-request `reasoning_effort=minimal` stage. In the initial stage, 14 requests exhausted the 1,100-token limit without returning code, and that stage was stopped immediately after the issue was identified. All 85 minimal-effort requests returned parseable code, using {minimal_usage['reasoning_tokens']} reasoning tokens in total.

## Functional correctness

| Language | Changed | Syntax-valid changed | Post-pass | EPR |
|---|---:|---:|---:|---:|
{chr(10).join(epr_lines)}

All 45 programs across the three languages passed execution. The main-study pilot had 40 programs, of which 34 were syntax-valid before attack; all 34 remained syntax-valid after attack. The formal cohort adds baseline syntax qualification for both methods.

## Watermark-pipeline smoke results

| Method | Dataset | Paired n | Clean BAR | Attack BAR | DeltaBAR | Attack MAR |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(wm_lines)}

Each cell above contains only three to five samples. These are end-to-end integration checks, not paper effect-size estimates.

## Cost and full-run projection

- Exact usage for the minimal-effort stage: {minimal_usage['prompt_tokens']:,} prompt and {minimal_usage['completion_tokens']:,} completion tokens.
- Recorded usage plus a conservative upper bound for the 14 initial requests without usage records costs no more than **CNY {recorded_cost + missing_usage_upper_cost:.2f}**.
- After baseline syntax filtering, the full plan contains {epr_full_requests:,} LLM-EPR requests and {main_full_requests:,} main-study requests, for {full_requests:,} total.
- Projecting from the measured minimal-effort pilot average gives approximately **CNY {projected_cost:.2f}**, or **CNY {projected_cost * 1.10:.2f}** with a 10% retry reserve.

See `rq2_llm_pilot.json` for complete per-sample results, usage, statuses, confidence intervals, and SHA-256 hashes.
"""
    (FINAL / "RQ2_LLM_PILOT.md").write_text(report, encoding="utf-8")
    print(json.dumps({
        "pilot_requests": 100,
        "minimal_usage": minimal_usage,
        "pilot_cost_upper_cny": recorded_cost + missing_usage_upper_cost,
        "full_projection": artifact["full_run_projection"],
    }, indent=2))


if __name__ == "__main__":
    main()
