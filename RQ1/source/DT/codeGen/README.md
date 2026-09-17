# Code-generation guide

## Agent architecture

The pipeline uses MetaGPT's Action/Role framework with separate model roles:

- architecture design uses the hosted model recorded in the RQ1 task manifest;
- code generation uses the local model recorded in
  `../../reproduct/model_runtime/MODEL_IDENTIFIERS.json`.

Reviewer-facing, credential-free configuration examples are provided in the
artifact. Put real API credentials only in local MetaGPT configuration files;
never commit them.

Formal task inputs and rendered prompts are released under
`../../../01_task_specs/` and `../../../02_prompts/`. Frequently changed
generation and watermark parameters are carried in the `xargs` mapping. The
canonical batch schema and method settings are documented in
`batchConfig.multi.example.json` and `method_specs.py`.

## Batch records

`batchCodeGenDT.py` creates its statistics and progress records as soon as it
resolves the output directory:

- `*_batch_summary_rngS=<seed>.json` is initialized before generation and
  atomically refreshed after each strength completes. It contains counts,
  tested/skipped/unclassified totals, and all `wmS_results` collected so far.
- `*_batch_progress_rngS=<seed>.jsonl` is initialized at startup and appends
  one row after each strength, enabling live inspection with `tail -f`.
- `wm_off_reference_rngS=<seed>/<project_name>/` stores the watermark-disabled
  source reference used for zero-strength equivalence auditing whenever the
  strength sequence includes `0.0`.

Long parameter-derived directory names are shortened to at most 180 bytes and
receive a stable `h=<hash>` suffix derived from the complete parameter name.

## Entry points

- `agentCodeGen.py`: generate code from a serialized architecture with the
  configured local model.
- `batchCodeGenDT.py`: execute the configured strength sweep from serialized
  architecture state.

The reproducibility campaign under `../../reproduct/` is the architecture and
baseline entry point for the released 42-unit experiment because it pins task
inputs, model identities, seeds, checkpoints, and audit records. The older
incomplete DT prompt modules and their two direct-generation examples were
removed; they remain recoverable from Git tag
`artifact-backup-before-legacy-dt-removal-20260917`.
