# RQ2 Robustness Revision Bundle

This bundle revises the supplied RQ2 attack archive for the TSE major revision.  It keeps the legacy scripts (`1_obfus_legacy.py`, `1_obfus_AI_legacy.py`) and adds a reproducible, validity-aware pipeline.

## What changed

1. **Reproducible attack RNG.** Every stochastic rule transformation receives a deterministic per-sample seed derived from `(global_seed, sample_uid, channel)`.
2. **No infeasible-key fallback.** A rule is accepted only if it changes the source and the final candidate passes Tree-sitter + MutableAST syntax checks. Failed/inapplicable rules are logged rather than forced.
3. **Missing Table-III rules added.** `DefaultParamTransformer` and `EquivalentFormsTransformer` implement conservative, language-aware versions of `indexOf(x) <-> indexOf(x,0)`, null-comparison operand swapping, and `isEmpty/empty <-> size()==0` when receiver evidence is sufficient.
4. **Safety guards for existing rules.** Update-form rewrites are restricted to standalone statements in safe mode; Java never emits `while(1)`; switch-to-if requires a side-effect-free selector; C++ declaration repositioning is restricted to scalar types and is disabled for JavaScript.
5. **Local hard-rule RAG.** `1_obfus_AI.py` now uses an archived hard-rule knowledge base + deterministic BM25 retrieval + a fixed prompt. This is genuine retrieval-augmented generation over local transformation rule cards, rather than file attachment being mislabeled as RAG.
6. **Validity bookkeeping.** Each row gets `_attack_uid` and `attack_meta` including channel, global/sample seed, applied/rejected operators, syntax validity, retrieved rules, and prompt hash.
7. **Detector handoff.** `run_watermark_detector.py` stages only valid attacks for the existing SrcMarker extractor and merges `obfus_extract` back without silently dropping invalid attacks.
8. **Correct metrics.** `3_analysis.py` reports clean/attacked BAR, MAR, **DeltaBAR = BAR_clean - BAR_attack**, the 4-bit chance MAR (`2^-4 = 6.25%` when `n_bits=4`), paired bootstrap 95% CIs, and validity coverage.
9. **MBXP validation.** `validate_mbxp_rq2.py` baseline-qualifies MBXP tasks, applies the same rule or LLM+RAG attack, reruns official-style executable tests, and reports attack coverage plus EPR among valid changed transformations.

## Table-III implementation map

| Channel | Table attribute | Revised implementation | Safety scope |
|---|---|---|---|
| Id | Naming Content | `IdRenameTransformer` | local variables/parameters; collision avoidance |
| Id | Naming Style | `VarNameStyleTransformer` | local bindings only |
| Expr | Update Ops | `UpdateTransformer` | standalone statements in safe mode |
| Expr | Predicate Rewrite | `LoopCondTransformer` | language-valid loop-condition variants |
| Expr | Default Params | `DefaultParamTransformer` | recognized built-in `indexOf`; unknown methods skipped |
| Expr | Equivalent Forms | `EquivalentFormsTransformer` | null swap; known-container empty/size equivalence |
| Block | Variable Decls | `ReposVarDeclTransformer` | JS disabled; C++ scalar-only safe mode |
| Block | Loop Stmt | `LoopStmtTransformer` | preserves same-loop continue updates |
| Block | If Flat/Nest | `IfFlatNestTransformer` | no-else cases only |
| Block | Conditionals | `ConditionTransformer` | no-fallthrough switch + pure selector; ternary assignment |
| Block | If Block Swap | `CondBlockSwapTransformer` | requires else branch |

## Environment

Use the existing SrcMarker environment.  The included MutableAST requires Tree-sitter 0.20/0.21 (matching the official SrcMarker guidance):

```bash
pip install -r requirements_revision.txt
```

If `languages.so` is not auto-detected, pass `--parser-lib /path/to/parser/languages.so` or set `RQ2_TREE_SITTER_LIB`.

## Rule-based attacks

Run each channel separately.  `all` composes all eligible channels in a fixed order.

```bash
python project/srcMarker/SrcMarker/1_obfus.py \
  --input project/srcMarker/SrcMarker/testResult/4bit_gru_srcmarker_42_csn_java_test.jsonl \
  --output out/srcmarker_csn_java_id.jsonl \
  --lang java --channel id --seed 42

python project/srcMarker/SrcMarker/1_obfus.py \
  --input project/srcMarker/SrcMarker/testResult/4bit_gru_srcmarker_42_csn_java_test.jsonl \
  --output out/srcmarker_csn_java_all.jsonl \
  --lang java --channel all --seed 42
```

Use the same global seed for all methods/datasets.  The per-sample derived seed is recorded in `attack_meta.sample_seed`.

## LLM + rule-RAG attack

The knowledge base is `rq2_revision/rules/hard_rules.json`.  BM25 retrieves language/channel-compatible rules and injects the top-k rule cards into the archived prompt.

OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=...
python project/srcMarker/SrcMarker/1_obfus_AI.py \
  --input project/srcMarker/SrcMarker/testResult/4bit_gru_srcmarker_42_csn_java_test.jsonl \
  --output out/srcmarker_csn_java_llm_all.jsonl \
  --lang java --channel all --seed 42 \
  --sample-size 1000 --max-chars 1400 --selection longest \
  --provider openai-compatible \
  --base-url https://api.openai.com/v1 --model <exact-model-id> \
  --temperature 0 --top-k 6
```

Legacy `aiAPI` wrapper:

```bash
python project/srcMarker/SrcMarker/1_obfus_AI.py \
  ... \
  --provider legacy-aiapi \
  --legacy-config /path/to/config_aiAPI.ini \
  --legacy-profile paid --legacy-model-attr gpt4
```

For the paper, describe this as **LLM-based semantic restatement augmented by deterministic retrieval from a local transformation-rule knowledge base**.  Archive the exact model ID, endpoint/provider, temperature, global seed, rule KB, top-k, and prompt files.

### Exact archived prompt

- `rq2_revision/prompts/system_prompt.txt`
- `rq2_revision/prompts/user_prompt_template.txt`

Do not call the legacy file-upload call itself “RAG”; the revised script performs explicit retrieval before generation.

## SrcMarker extraction after attack

When this bundle is copied into the full SrcMarker repository:

```bash
python project/srcMarker/SrcMarker/run_watermark_detector.py \
  --attack-jsonl out/srcmarker_csn_java_all.jsonl \
  --merged-output out/srcmarker_csn_java_all_eval.jsonl \
  --evaluator ./2_eval_obfus.py \
  --checkpoint-path ./ckpts/4bit_gru_srcmarker_42_csn_java/models_best.pt \
  --lang java --dataset csn_java --model-arch gru --shared-encoder
```

The wrapper preserves invalid attacks and labels them `skipped_invalid_attack` instead of silently removing them from the experiment.

For environments without a working CUDA device, the portable extractor loads only the
trained encoder and watermark decoder and can process several channel files with one
checkpoint load:

```bash
PYTHONPATH=$PWD/.deps python project/srcMarker/SrcMarker/run_watermark_detector_portable.py \
  --input out/srcmarker_csn_java_id.jsonl out/srcmarker_csn_java_all.jsonl \
  --output out/srcmarker_csn_java_id_eval.jsonl out/srcmarker_csn_java_all_eval.jsonl \
  --srcmarker-root /path/to/full/SrcMarker \
  --checkpoint-path /path/to/models_best.pt \
  --lang java --device cpu --batch-size 32
```

## Robustness metrics + CI

```bash
python project/srcMarker/SrcMarker/3_analysis.py \
  --input out/srcmarker_csn_java_all_eval.jsonl \
  --bootstrap 10000 --seed 42 \
  --json-output out/srcmarker_csn_java_all_metrics.json
```

For a 4-bit message, the exact-message chance baseline is 6.25%.  The revised script uses paired sample-level bootstrap resampling rather than treating individual bits as independent samples.

## MBXP transformation-validity experiment

Run the same channel operators on the executable MBXP subsets:

```bash
python project/srcMarker/SrcMarker/validate_mbxp_rq2.py \
  --dataset /path/to/mbjp_release_v1.2_filtered.jsonl \
  --lang java --channel all --attack rule --seed 42 \
  --output out/mbjp_rule_all.jsonl \
  --summary out/mbjp_rule_all_summary.json
```

For LLM+RAG validity:

```bash
python project/srcMarker/SrcMarker/validate_mbxp_rq2.py \
  --dataset /path/to/mbjp_release_v1.2_filtered.jsonl \
  --lang java --channel all --attack llm-rag --seed 42 \
  --provider openai-compatible --model <exact-model-id> \
  --output out/mbjp_llm_all.jsonl \
  --summary out/mbjp_llm_all_summary.json
```

The summary distinguishes:

- baseline-pass tasks;
- attacks that actually changed the function (`attack_coverage`);
- syntactically valid changed attacks;
- execution-preserving changed attacks (`EPR_given_valid_changed`).

This avoids inflating EPR with no-op/inapplicable transformations.

## Dataset labels

The supplied archive contains `csn_java`, `csn_js`, `github_c_funcs`, and `github_java_funcs`.  Therefore the corresponding main-table labels should be **CSN-Java, CSN-JavaScript, GitHub-C, and GitHub-Java** unless a different external dataset was actually used.

## Tests performed in this bundle

Run:

```bash
PYTHONPATH=$PWD/cStyleLang:$PWD pytest -q tests
```

The bundled tests cover the new hard rules, update-expression safety guard, deterministic BM25 retrieval, prompt/output contract, DeltaBAR/MAR math, and detector-wrapper dry-run behavior.

A separate compiler/runtime smoke test was also performed for the added equivalence examples with Java 21 (`javac`), g++ 14/C++17, and Node 22.

## Fresh-checkpoint experiment completed in this workspace

Tree-sitter 0.21.3 and the remaining Python dependencies were installed under the
bundle-local `.deps` directory. SrcMarker and CodeMark were each trained from random
initialization for 25 epochs on GitHub-C, GitHub-Java, CSN-JavaScript, and CSN-Java
(eight independent checkpoints total). The complete rule-attack matrix contains 32
method/dataset/channel cells, each analyzed with 10,000 paired bootstrap replicates.

The human-readable fresh-run report is `outputs/fresh/final/RQ2_FRESH_RESULTS.md`;
machine-readable results are in `rq2_fresh_results.json` and
`rq2_fresh_rule_metrics.csv` in the same directory.

## Real LLM-RAG experiment completed in this workspace

The archived main LLM experiment uses a balanced 2-method by 4-dataset design with 125
programs per cell (1,000 generations total). The exact provider alias was `gpt-5`; all
formal responses identified the server-side snapshot as `gpt-5-2025-08-07`. Generation
used temperature 0, seed 42, local BM25 retrieval with top-k 6, reasoning effort
`minimal`, and a 1,100 completion-token cap. The run produced 972 valid attacks, 23
no-ops, five syntax-invalid outputs, and no API errors. No-op/invalid rows remain in the
audit trail and are excluded from attacked watermark extraction.

Run and regenerate the formal outputs with:

```bash
PYTHONPATH=.deps python run_llm_full_1000.py \
  --env-file /secure/path/llm.env --workers 2
PYTHONPATH=.deps python run_llm_full_detection.py \
  --device cuda --gpus 0,1 --workers 2 --bootstrap 10000
PYTHONPATH=.deps python build_rq2_deliverables.py
PYTHONPATH=.deps python plot_rq2_results.py
```

The detailed paper/appendix input is
`deliverables/01_paper_report/RQ2_PAPER_AND_APPENDIX_REPORT.md`. Machine-readable
results, exact prompts/rule cards, tables, LaTeX, figures, usage/cost accounting, and
artifact hashes are under `deliverables/` and `outputs/fresh/llm_full_1000/`. API
credentials are never archived.

## Results generated in this workspace

After a completed run, `python build_final_report.py` consolidates the metrics, validity
metadata, environment hashes, MBXP sanity results, and archived-result reanalysis under
`outputs/final/`. The human-readable entry point is `outputs/final/RQ2_RESULTS.md`.

For the from-scratch model runs requested here, use `python build_fresh_report.py` and
the artifacts under `outputs/fresh/final/`.
