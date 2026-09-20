# Timing harnesses

- `benchmark_logits_bias.py` drives the local OpenAI-compatible Qwen server,
  fixes method configurations and RQ1 EEI midpoint strengths, records every
  generated source, and preserves paired WM-OFF, method-owned processor, and
  detector timing. It creates one adjacent WM-OFF invocation per measured
  method row and counterbalances pair order 5/5 within each method.
- WLLM and SWEET preserve upstream tensor membership during green-list scoring;
  they do not rebuild a Python set from half the vocabulary for every token.
- WLLM, EWD, SWEET, and STONE extraction uses only the 256-token generated
  continuation and explicitly records 255 scoreable previous-token positions.
- SWEET extraction performs a fresh causal-LM forward pass over the generated
  continuation before entropy gating and z-score calculation. A run
  with zero entropy-qualified tokens is rejected instead of being recorded as
  a near-zero detector timing.
- `merge_logits_bias_rerun.py` is retained as a maintenance utility; the
  released authoritative record is a complete all-method campaign rather than
  a merged partial rerun.
- `benchmark_semantic.py` loads the fresh RQ2 checkpoint and canonical
  CodeSearchNet JavaScript test split and records one row per sample.
- `workloads.json` and `workloads/` contain the two complete rendered-input
  components used by the logits-bias benchmark.

The associated source instrumentation is retained under
`../../RQ1/source/` and `../../RQ2/source/`. Timing uses `perf_counter`; CUDA is
synchronized immediately before and after each measured region. Warm-up rows
are retained in the raw JSON but excluded from summary statistics. The harness
fails if a detector does no work, token scopes differ, or pair-order counts are
not counterbalanced.

These scripts write raw evidence. Normalization and Table X generation are
implemented separately in `../05_analysis/reproduce_table_x.py`.
