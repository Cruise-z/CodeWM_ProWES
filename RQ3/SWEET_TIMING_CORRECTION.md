# SWEET timing correction

## Reason for the correction

The first RQ3 campaign reported 2.571476 ms/1K tokens for SWEET extraction.
All ten underlying detector records had `num_tokens_scored=0`,
`watermarking_fraction=0`, and `z_score=-100`. The value therefore measured
the detector's empty-gate early return rather than a complete SWEET extraction.

Two protocol defects were corrected before rerunning SWEET:

1. The entropy threshold was aligned with the paper configuration (`ET=0.5`).
2. Detection now performs a fresh causal-LM forward pass over the completed
   prompt and continuation. The resulting per-token logits are used to
   reconstruct entropy before green-list recovery and z-score calculation.

The timing harness now rejects a SWEET response unless it reports a positive
`num_tokens_scored`, `detector_model_forward` entropy provenance, and matching
continuation/entropy token counts.

## Corrected campaign

- Source commit: `fe55e272b9a9296a03639456180bc8e090eed59e`
- Timestamp: `2026-09-17T11:00:25.944695+00:00`
- Model/tokenizer: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- Hardware: four NVIDIA A800 80GB PCIe GPUs
- Driver: 595.58.03
- SWEET parameters: gamma=0.5, delta=1.785, ET=0.5
- Sampling: temperature=0.7, top-p=1.0
- Workloads: two fixed metaProjectDEV Java contexts
- Warm-up: one excluded invocation
- Measured invocations: ten
- Completion tokens: 2,560 total (256 per invocation)
- Entropy-qualified/scored tokens: 70 total (3--11 per invocation)

## Corrected result

| Quantity | Corrected value |
|---|---:|
| Embedding elapsed time | 10.575781868 s |
| Embedding | 4,131.164792 ms/1K tokens |
| Embedding 95% bootstrap CI | [4,062.294608, 4,200.126141] |
| Extraction elapsed time | 31.245590681 s |
| Extraction | 12,205.308860 ms/1K tokens |
| Extraction 95% bootstrap CI | [10,719.771008, 13,662.871277] |

The point estimates use the ratio-of-sums normalization:

```text
ms_per_1k = sum(elapsed_seconds) * 1,000,000 / sum(completion_tokens)
```

The standalone corrected evidence is in
`RQ3/02_raw_timings/sweet_rerun_raw.json`. The same rows replace the invalid
SWEET rows in `RQ3/02_raw_timings/logits_bias_raw.json`, from which the flat
timing ledger, token-count ledger, and Table X are regenerated.

Detection predictions and z-scores are retained in every raw row. RQ3 measures
runtime and does not filter timing samples by whether their z-score crosses the
detection threshold.
