# Code-generation guide

## Agent architecture

The pipeline uses MetaGPT's Action/Role framework with separate model roles:

- architecture design uses the hosted model recorded in the RQ1 task manifest;
- code generation uses the local model recorded in
  `../../reproduct/model_runtime/MODEL_IDENTIFIERS.json`.

Reviewer-facing, credential-free configuration examples are provided in the
artifact. Put real API credentials only in local MetaGPT configuration files;
never commit them.

Task prompts are grouped under `prompts/`. Frequently changed generation and
watermark parameters are carried in the `xargs` mapping. The canonical batch
schema and method settings are documented in `batchConfig.multi.example.json`
and `method_specs.py`.

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

- `agent.py`: edit `xargs` and generate directly from a task prompt.
- `agentArchGen.py`: generate and serialize a reusable architecture.
- `agentCodeGen.py`: generate code from a serialized architecture with the
  configured local model.

The reproducibility campaign under `../reproduct/` is the preferred entry
point for the released 42-unit experiment because it pins identities, seeds,
and audit records.
