# RQ3 timing design audit

## Audit outcome

The historical Artifact mixed two definitions of logits-bias embedding:

1. the manuscript method section defined overhead as watermarked generation
   minus watermark-free generation; and
2. the harness and Table X note measured only method-owned logits-processor
   time.

The historical record also lacked WM-OFF raw rows, WLLM rebuilt a Python set
from roughly half the vocabulary at every detector position, and EWD/STONE
included the prompt in detector work while normalizing only by completion
tokens. Those issues were large enough to require a complete rerun.

## Released estimators

The released Table X follows the manuscript definition. For every logits-bias
method row:

```text
embedding_seconds = synchronized_watermarked_generation_seconds
                  - synchronized_adjacent_WM_OFF_generation_seconds
```

The two members share workload, seed, sampling configuration, and a fixed
256-token completion length. Each method has ten pairs with order
counterbalanced 5/5. The point estimate is a ratio of sums and its interval is
a 10,000-replicate paired row bootstrap.

Method-owned synchronized logits-processor time is retained separately as
`processor_only_embedding_*`. It is useful for mechanism attribution, but it
is not the Table X embedding estimator. The two quantities need not be equal:
watermarking changes sampled tokens and can therefore change subsequent MoE
routing and model execution paths.

Extraction is the complete detector invocation on generated code only. WLLM,
EWD, SWEET, and STONE receive the 256-token continuation; previous-token
seeding makes 255 positions scoreable. CodeIP and Waterfall already used
continuation-only detectors. SWEET includes an independent detector model
forward.

## Corrected Table X values

| Method | Training (s) | Embedding (ms/1K tok.) | Extraction (ms/1K tok.) | Processor-only embedding (ms/1K tok.) |
|---|---:|---:|---:|---:|
| WLLM | -- | 7,101.26 | 3,778.55 | 4,185.16 |
| EWD | -- | 472.30 | 2,582.20 | 519.89 |
| SWEET | -- | 7,069.36 | 5,417.50 | 4,575.20 |
| STONE | -- | 803.96 | 451.36 | 724.38 |
| CodeIP | -- | 1,253.89 | 3,282.92 | 818.41 |
| Waterfall | -- | 5,051.25 | 2,529.60 | 1,297.14 |
| CodeMark | 11,604 | 79.23 | 59.32 | -- |
| SrcMarker | 13,017 | 74.56 | 48.01 | -- |

The EWD paired embedding 95% interval includes zero
([-259.44, 1,020.40] ms/1K tokens), which indicates that ten pairs do not
resolve its small end-to-end increment against generation variability. Its
processor-only timing remains positive and tightly estimated. Both facts are
retained rather than suppressing the noisy paired observation.

## Integrity checks

`RQ3/05_analysis/reproduce_table_x.py` rejects the release unless it can verify:

- one unique WM-OFF row for every measured method row;
- identical pair workload, seed, and completion-token count;
- exact generation subtraction and output hashes;
- five observations in each pair order for every method;
- continuation-only detector scope and token alignment;
- SWEET detector-forward provenance and positive score counts; and
- all per-row and aggregate normalizations.
