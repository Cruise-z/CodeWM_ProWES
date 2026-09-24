# RQ3 — performance overhead

This directory closes the Table X evidence chain:

```text
fixed workload + checkpoint + method configuration
  -> synchronized per-invocation timing
  -> raw seconds + shared-tokenizer counts
  -> ratio-of-sums normalization
  -> Table X CSV/JSON/LaTeX
```

The final logits-bias campaign uses six actual RQ1 Stage-1 prompts: two projects
crossed with C++, Java, and Python. Each method has 30 measured pairs (six
workloads times five repetitions) after one excluded warm-up per language.
Both members are forced to 256 completion tokens. Every watermarked generation
has its own adjacent, same-workload, same-seed WM-OFF generation; pair order is
exactly counterbalanced 15/15 and method order is shuffled per block. Table X
embedding is the synchronized paired generation difference.

This is the non-intrusive v2 protocol. No per-token clock, CUDA synchronization,
or detection-only cache runs during measured generation. CUDA synchronization
occurs only at outer request boundaries. Request-scoped switches leave the
default RQ1 path unchanged; the included same-seed regression test confirms
that disabling observation does not change the generated token sequence.

Extraction is a separate request through a freshly constructed processor. Its
timed boundary starts from final generated text and includes tokenization,
method-owned transfers, and the complete detector. It never reuses generation
state. SWEET therefore includes its independent causal-LM forward for entropy
gating. CodeIP uses the released random-message branch, and fixed length ensures
at least one complete configured message block.

The semantic-preserving experiment evaluates CodeMark and SrcMarker on all
3,150 samples in the CodeSearchNet JavaScript test split after 20 excluded
warm-ups, using the fresh seed-42 RQ2 checkpoints. Embedding starts from raw
source and includes tokenization, tensorization, device transfer, selector
inference, and transformation. Extraction independently starts from raw
watermarked source and includes tokenization, tensorization, transfer, encoder,
bit decoder, and threshold. Candidate metadata and model loading are offline
setup.

All normalization counts use
`Qwen/Qwen3-Coder-30B-A3B-Instruct`. Logits embedding uses completion tokens;
logits extraction uses independently tokenized final-text tokens. Semantic
embedding uses input-source tokens and extraction uses watermarked-source
tokens. Point estimates and 10,000-replicate intervals are recomputed from raw
rows.

Run:

```bash
./paper_reproduction/reproduce_rq3.sh
```

The command validates every raw row, recomputes point estimates and confidence
intervals, writes the flat raw-timing and token-count ledgers, parses the
training logs, and regenerates
`paper_reproduction/tables/RQ3/table_x.{csv,json,tex}`.
