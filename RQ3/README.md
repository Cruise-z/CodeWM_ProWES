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
generations (five repetitions of two workloads), each capped at 256 completion
tokens. Embedding is method-owned logits-processor wall time and excludes model
forward time. Extraction is the complete detector invocation. The CodeIP row
uses the released random-message branch without the optional PDA/type predictor,
which is the variant represented in Table X.

The semantic-preserving experiment evaluates CodeMark and SrcMarker on all
3,150 samples in the CodeSearchNet JavaScript test split after 20 excluded
warm-ups. It uses the fresh seed-42 checkpoints from RQ2. Embedding includes
selector inference and the selected source transformation; extraction includes
the encoder, bit decoder, and threshold. CUDA is synchronized immediately
before and after every measured boundary.

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
