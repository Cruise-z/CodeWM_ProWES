# RQ2 Robustness Revision — Test Report

Packaging validation date: 2026-09-14.

## Tests completed in the packaging environment

1. Python bytecode compilation of the complete bundle:
   - `python -m compileall -q .`
   - Result: **PASS**.

2. Revision unit tests:
   - `PYTHONPATH=$PWD/cStyleLang:$PWD pytest -q tests`
   - Result: **10 passed**.
   - Coverage includes the newly added Default Params / Equivalent Forms rules, the safe update-expression guard, deterministic/channel-filtered BM25 retrieval, LLM prompt/output parsing, DeltaBAR/MAR chance arithmetic, and detector-wrapper dry-run behavior.

3. Compiler/runtime equivalence smoke tests:
   - `bash tests/compiler_smoke.sh`
   - Result: **PASS**.
   - Tested with Java 21 (`javac`), g++ 14/C++17, and Node 22.
   - Includes Java `indexOf(x) <-> indexOf(x,0)`, Java `isEmpty() <-> size()==0`, null-comparison operand swapping, C++ `empty() <-> size()==0` / `nullptr` swapping, and JavaScript `indexOf` / null swapping.

4. MBXP runtime-helper synthetic smoke test:
   - `execute_program()` in `validate_mbxp_rq2.py` was exercised with minimal passing Java, C++, and JavaScript programs.
   - Result: **PASS for all three languages**.

5. Zip archive integrity test (performed after packaging):
   - `unzip -t <archive>`.

## Environment limitation

The packaging container does **not** have the Python `tree_sitter` binding installed, and outbound package installation is unavailable. The provided compiled `parser/languages.so` alone is not sufficient to import the Python binding. Consequently, the full Tree-sitter/MutableAST attack pipeline and an end-to-end MBXP transformation run could not be executed in this container.

Run the full experiment in the existing SrcMarker environment using Tree-sitter 0.20/0.21, as documented in `README_REVISION.md`. The bundle intentionally records this limitation instead of treating parser-independent tests as an end-to-end validation.

## Workspace execution update (2026-09-15)

- Installed Tree-sitter 0.21.3 into the bundle-local `.deps` directory.
- Revision tests after the execution fixes: **13 passed**.
- Full deterministic rule transformation: **28 method/dataset/channel jobs completed**.
- SrcMarker CPU extraction: **58,780 rows processed**, **56,716 predictions**, **0
  tokenization errors**; syntax-invalid rows were retained and skipped explicitly.
- Paired sample-level bootstrap: **10,000 replicates** for every reported robustness
  cell.
- MBXP C++ sanity gate: **20/20 EPR for each of Id, Expr, Block, and ALL**.
- Determinism check: the repeated 20-row output was byte-identical to the corresponding
  full-run prefix.
- Final artifact checksum verification: **PASS**.

## Fresh-checkpoint completion update (2026-09-15)

- SrcMarker and CodeMark: **8/8 independent models trained from random initialization**
  (four datasets per method, 25 epochs each, seed 42).
- Independent clean generation: **8/8 outputs completed**.
- Rule robustness matrix: **32/32 cells completed** (`id`, `expr`, `block`, and `all`
  for every method/dataset pair).
- JSONL integrity: **264,510 rows parsed**, covering 8 clean, 32 attacked, and 32
  detector-output files; dataset row counts and attack status totals are consistent.
- Paired bootstrap: **10,000 replicates for all 32 cells**.
- Revision tests: **13/13 passed**; Python compilation and `git diff --check` passed.
- Final fresh artifacts: `outputs/fresh/final/RQ2_FRESH_RESULTS.md`,
  `rq2_fresh_results.json`, and `rq2_fresh_rule_metrics.csv`.

## Real LLM and final-deliverable update (2026-09-16)

- Real LLM generation: **1,000/1,000 rows completed**, with usage metadata for every
  request and no API errors.
- Generation validity: **972 valid attacks**, 23 no-ops, five syntax-invalid outputs.
- Server response snapshot: `gpt-5-2025-08-07` for all formal requests.
- Checkpoint extraction: **8/8 method/dataset cells completed** on CUDA; 972 valid
  attacked rows received predictions, with no tokenization errors.
- LLM robustness statistics: 10,000 paired bootstrap replicates for all eight cells.
- No-op exclusion regression: both detector implementations explicitly retain but do
  not extract unchanged rows.
- Final revision tests: **16/16 passed**.
- Delivery builders compile and generate Markdown, JSON, CSV, LaTeX, PNG, and PDF
  artifacts from the archived results.
