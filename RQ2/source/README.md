# RQ2 robustness source

This directory is the final source release used for RQ2. It contains the
fresh-training pipeline for SrcMarker and CodeMark, deterministic rule-based
attacks, the LLM+RAG attack, MBXP validation, watermark extraction, paired
statistics, and paper-output builders.

## Environment

Install the pinned RQ2 dependencies:

```bash
python -m pip install -r requirements.txt
```

The MutableAST implementation requires Tree-sitter 0.20/0.21. If
`languages.so` is not auto-detected, set `RQ2_TREE_SITTER_LIB` or pass
`--parser-lib` to the relevant command.

## Final implementation map

| Experiment stage | Implementation |
|---|---|
| Fresh SrcMarker/CodeMark training | `training/SrcMarker_fresh/` |
| Rule-based attacks | `project/srcMarker/SrcMarker/1_obfus.py`, `pipeline/rule_attack.py` |
| LLM+RAG attacks | `project/srcMarker/SrcMarker/1_obfus_AI.py`, `pipeline/` |
| MBXP execution preservation | `project/srcMarker/SrcMarker/validate_mbxp_rq2.py` |
| Watermark extraction | `project/srcMarker/SrcMarker/run_watermark_detector.py` |
| BAR/MAR/DeltaBAR and bootstrap | `project/srcMarker/SrcMarker/3_analysis.py` |
| Final tables and figures | `build_rq2_deliverables.py`, `plot_rq2_results.py` |

The transformation channels are `id`, `expr`, `block`, and `all`. Every
stochastic rule attack uses a sample seed derived deterministically from the
global seed, sample UID, and channel. Inapplicable transformations are recorded
without fallback. Syntax validity and execution validity are separate fields.

## Rule-based attack

```bash
python project/srcMarker/SrcMarker/1_obfus.py \
  --input /path/to/clean_predictions.jsonl \
  --output /path/to/attacked.jsonl \
  --lang java --channel all --seed 42
```

## LLM+RAG attack

The final protocol uses the fixed prompts under `pipeline/prompts/`, the
12-card rule base at `pipeline/rules/hard_rules.json`, deterministic BM25
retrieval with top-k 6, temperature 0, and seed 42.

```bash
export OPENAI_API_KEY=...
python project/srcMarker/SrcMarker/1_obfus_AI.py \
  --input /path/to/clean_predictions.jsonl \
  --output /path/to/llm_attacked.jsonl \
  --lang java --channel all --seed 42 \
  --sample-size 125 --selection longest \
  --provider openai-compatible \
  --base-url https://api.openai.com/v1 --model gpt-5 \
  --temperature 0 --top-k 6
```

The released formal observations contain 1,000 calls. All returned model IDs
are `gpt-5-2025-08-07`; 972 outputs are valid attacks, 23 are no-ops, and five
are syntax-invalid. Credentials are never archived.

## MBXP validation

```bash
python project/srcMarker/SrcMarker/validate_mbxp_rq2.py \
  --dataset /path/to/mbjp_release_v1.2_filtered.jsonl \
  --lang java --channel all --attack rule --seed 42 \
  --output /path/to/mbjp_rule_all.jsonl \
  --summary /path/to/mbjp_rule_all_summary.json
```

The final rule-based matrix contains 9,572 changed and syntax-valid programs,
of which 9,444 pass after transformation. The separate LLM+RAG pilot passes
45/45 programs.

## Metrics and paper outputs

```bash
python project/srcMarker/SrcMarker/3_analysis.py \
  --input /path/to/evaluated_attack.jsonl \
  --bootstrap 10000 --seed 42 \
  --json-output /path/to/metrics.json
```

From the artifact root, the reviewer entry point is:

```bash
./paper_reproduction/reproduce_rq2.sh
```

It verifies the final per-sample evidence and writes the released tables and
figures only to `paper_reproduction/tables/RQ2/` and
`paper_reproduction/figures/RQ2/`.

## Tests

```bash
PYTHONPATH=$PWD/cStyleLang:$PWD pytest -q tests
bash tests/compiler_smoke.sh
```

See `VALIDATION.md` for the final validation status.
