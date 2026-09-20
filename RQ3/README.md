# RQ3 — performance overhead

This directory closes the Table X evidence chain:

```text
fixed workload + checkpoint + method configuration
  -> synchronized per-invocation timing
  -> raw seconds + shared-tokenizer counts
  -> ratio-of-sums normalization
  -> Table X CSV/JSON/LaTeX
```

The logits-bias experiment measures six methods on two fixed metaProjectDEV
Java contexts. Each method receives one excluded warm-up and ten measured
generations (five repetitions of two workloads), each fixed at 256 completion
tokens. Every watermarked generation has its own adjacent, same-workload,
same-seed, same-length WM-OFF generation. Pair order is counterbalanced 5/5
within every method. Table X embedding is the synchronized paired generation
difference. The raw evidence also reports method-owned logits-processor time as
a lower-noise attribution diagnostic; it is not substituted for the paired
Table X estimator.

Extraction is the complete detector invocation on the generated continuation.
For previous-token seeding, one token supplies context and 255 positions are
scoreable. SWEET extraction includes a fresh model forward over the continuation
to reconstruct the per-token entropy gate and rejects runs with no scoreable
token. The CodeIP row uses the released random-message branch without the
optional PDA/type predictor, which is the variant represented in Table X.

The semantic-preserving experiment evaluates CodeMark and SrcMarker on all
3,150 samples in the CodeSearchNet JavaScript test split after 20 excluded
warm-ups. It uses the fresh seed-42 checkpoints from RQ2. Embedding includes
selector inference and the selected source transformation; extraction includes
the encoder, bit decoder, and threshold. CUDA is synchronized immediately
before and after every measured boundary, including both members of each
generation pair.

All normalization counts use
`Qwen/Qwen3-Coder-30B-A3B-Instruct`. Logits-bias rows use generated tokens for
both columns. Semantic-preserving embedding uses input-source tokens and
extraction uses the corresponding watermarked-source tokens.

Run:

```bash
./paper_reproduction/reproduce_rq3.sh
```

The command verifies the embedded aggregates against the raw records, writes
the flat raw-timing and token-count ledgers, parses the training logs, and
regenerates `paper_reproduction/tables/rq3/table_x.{csv,json,tex}`.
