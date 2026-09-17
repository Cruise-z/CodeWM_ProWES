# Revision changelog

- Preserved legacy attack scripts as `1_obfus_legacy.py` and `1_obfus_AI_legacy.py`.
- Replaced hard-coded input/output paths with CLI arguments.
- Added stable per-sample attack seeds and metadata.
- Removed theoretical-key fallback from the revised driver.
- Added `DefaultParamTransformer` and `EquivalentFormsTransformer`.
- Added safety guards for update rewrites, Java loop predicates, switch selector duplication, declaration relocation, and identifier collisions.
- Added local BM25 hard-rule RAG and reproducible prompt templates.
- Added detector handoff wrapper preserving invalid attacks.
- Replaced legacy BFR calculation/terminology with paired DeltaBAR.
- Added 4-bit MAR chance baseline and paired bootstrap CI analysis.
- Added MBXP execution-preservation validator.
- Added explicit top-level `no_op`, `syntax_invalid`, `execution_invalid`, and
  `valid_attack` status labels.
- Added support for the workspace MBXP `original_string` schema.
- Added a portable CPU/CUDA detector that reuses one checkpoint across channel files.
- Vectorized the paired sample-level bootstrap while retaining 10,000 percentile-CI
  replicates and deterministic seeding.
- Added a final JSON/CSV/Markdown report builder with artifact checksums.
- Added secure resumable orchestration for the balanced 1,000-generation LLM-RAG run,
  including exact token/cost/model-snapshot accounting.
- Excluded unchanged LLM no-ops from watermark-effect estimates while retaining them in
  the audit trail.
- Added CUDA checkpoint extraction, method-paired contrast tables, applied-rule usage
  tables, paper/appendix context, LaTeX tables, and reproducible PNG/PDF figures.
