# Table X reproduction

`reproduce_table_x.py` reads the three raw timing files, recomputes every
normalized point estimate from raw seconds and reference-token counts, parses
the canonical CSN-JavaScript training logs, and writes CSV, JSON, and LaTeX
versions of Table X. It also materializes reviewer-friendly flat ledgers in
`RQ3/02_raw_timings/raw_timings.csv` and `RQ3/04_token_counts/token_counts.csv`.
Before writing outputs it verifies per-row normalization, generated-text and
rendered-prompt hashes, one-to-one baseline linkage, paired subtraction, 5/5
within-method pair-order balance, run counts, and both released semantic
checkpoint digests. For SWEET it additionally requires the paper's `ET=0.5`
setting, positive scored-token counts, and independently recomputed
detector-entropy provenance. See `../TIMING_DESIGN_AUDIT.md` and
`../SWEET_TIMING_CORRECTION.md` for the correction audit.

From the artifact root:

```bash
./paper_reproduction/reproduce_rq3.sh
```

Normalization is ratio-of-sums:

```text
ms_per_1k = sum(elapsed_seconds) * 1,000,000 / sum(reference_tokens)
```

For logits-bias methods, Table X embedding is `watermarked generation time -
adjacent WM-OFF generation time`; the processor-only value remains a separate
diagnostic column in CSV/JSON. Both embedding and extraction use generated
completion tokens. For CodeMark and SrcMarker, embedding uses input-source
tokens and extraction uses tokens in the corresponding watermarked source. All
reference counts use the released Qwen3-Coder tokenizer manifest.
