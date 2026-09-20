# SWEET timing correction

## Why the historical value was invalid

The first RQ3 campaign reported 2.571476 ms/1K tokens for SWEET extraction.
All ten detector records had `num_tokens_scored=0`,
`watermarking_fraction=0`, and `z_score=-100`. That value measured an
empty-gate early return rather than a complete detector invocation.

An intermediate correction aligned `ET=0.5` and added an independent model
forward, but it still processed the prompt together with the continuation and
used the processor-only embedding timer as the paper's embedding result. That
intermediate campaign is superseded by the complete all-method rerun below.

## Final protocol

- Source commit: `37fe323bec78bf31ed6b2ee393c22a494652f1e6`
- Timestamp: `2026-09-20T03:35:51.723808+00:00`
- Model/tokenizer: `Qwen/Qwen3-Coder-30B-A3B-Instruct`
- Hardware: four NVIDIA A800 80GB PCIe GPUs
- SWEET parameters: gamma=0.5, delta=1.785, ET=0.5
- Sampling: temperature=0.7, top-p=1.0
- Workloads: two fixed metaProjectDEV Java contexts
- Warm-up: one excluded invocation
- Measured invocations: ten
- Completion tokens: 2,560 total (256 per invocation)
- Detector scope: generated continuation only
- Entropy-qualified/scored tokens: 358 total
- WM-OFF pairing: one adjacent same-workload, same-seed, same-length baseline
  per invocation; five baseline-first and five watermark-first pairs

Detection performs a fresh causal-LM forward over the 256-token continuation.
The first token supplies previous-token context, so entropy and green-list
scoring cover 255 candidate positions. The harness rejects zero-score runs and
requires `detector_model_forward` provenance.

## Final result

| Quantity | Final value |
|---|---:|
| Paired WM-OFF embedding elapsed difference | 18.097558864 s |
| Table X embedding | 7,069.358931 ms/1K tokens |
| Table X embedding 95% bootstrap CI | [6,489.191933, 7,631.070833] |
| Processor-only embedding elapsed time | 11.712504504 s |
| Processor-only embedding | 4,575.197072 ms/1K tokens |
| Processor-only embedding 95% bootstrap CI | [4,261.298199, 4,906.432380] |
| Extraction elapsed time | 13.868808662 s |
| Extraction | 5,417.503383 ms/1K tokens |
| Extraction 95% bootstrap CI | [5,280.290721, 5,567.802229] |

Point estimates use ratio-of-sums normalization:

```text
ms_per_1k = sum(elapsed_seconds) * 1,000,000 / sum(completion_tokens)
```

The authoritative evidence is the SWEET subset of
`RQ3/02_raw_timings/logits_bias_raw.json`; the standalone intermediate rerun
was removed to prevent two incompatible result files from appearing current.
Detection decisions and z-scores remain in every raw row. RQ3 measures runtime
and does not filter samples by whether the detector score crosses its decision
threshold.
