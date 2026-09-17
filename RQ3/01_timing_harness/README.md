# Timing harnesses

- `benchmark_logits_bias.py` drives the local OpenAI-compatible Qwen server,
  fixes method configurations and RQ1 EEI midpoint strengths, records every
  generated source, and preserves method-owned embedding and detector timing.
- `benchmark_semantic.py` loads the fresh RQ2 checkpoint and canonical
  CodeSearchNet JavaScript test split and records one row per sample.
- `workloads.json` and `workloads/` contain the two complete rendered-input
  components used by the logits-bias benchmark.

The associated source instrumentation is retained under
`../../RQ1/source/` and `../../RQ2/source/`. Timing uses `perf_counter`; CUDA is
synchronized immediately before and after each measured region. Warm-up rows
are retained in the raw JSON but excluded from summary statistics.

These scripts write raw evidence. Normalization and Table X generation are
implemented separately in `../05_analysis/reproduce_table_x.py`.
