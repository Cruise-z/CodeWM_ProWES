# Model and tokenizer identifiers

## RQ1

- Stage-0 requested model: `gpt-5` through the OpenAI-compatible endpoint
  recorded in `RQ1/01_task_specs/manifest.json`. Per-checkpoint evidence records
  the actual endpoint/model provenance. Reproduction proceeds from released
  serialized checkpoints and does not require Stage-0 API access.
- Stage-1 model: `Qwen/Qwen3-Coder-30B-A3B-Instruct`; the local resolved path,
  weight/config/tokenizer hashes, Transformers/PyTorch versions, dtype, GPU,
  and service fingerprint are recorded in `00_common/environment/preflight.json`,
  `model_weights.json`, and `model_replicas.json`.

## RQ2

- Fresh SrcMarker and CodeMark models use the released shared-GRU training
  implementation and its source-code tokenizer/vocabulary; exact vocabulary
  sizes and model capacities are in each `run_manifest.json`.
- Exact detector identity is the SHA-256 of each released `models_best.pt`.
- LLM attack requested alias: `gpt-5`; all 1,000 formal responses report
  snapshot `gpt-5-2025-08-07`. Temperature is 0, reasoning effort is `minimal`,
  completion cap is 1,100 tokens, and retrieval top-k is 6.
