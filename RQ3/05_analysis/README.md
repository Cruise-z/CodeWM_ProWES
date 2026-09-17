# Table X reproduction

`reproduce_table_x.py` reads the three raw timing files, recomputes every
normalized point estimate from raw seconds and reference-token counts, parses
the canonical CSN-JavaScript training logs, and writes CSV, JSON, and LaTeX
versions of Table X. It also materializes reviewer-friendly flat ledgers in
`RQ3/02_raw_timings/raw_timings.csv` and `RQ3/04_token_counts/token_counts.csv`.
Before writing outputs it verifies per-row normalization, generated-text and
rendered-prompt hashes, run counts, and both released semantic checkpoint
digests.

From the artifact root:

```bash
./paper_reproduction/reproduce_rq3.sh
```

Normalization is ratio-of-sums:

```text
ms_per_1k = sum(elapsed_seconds) * 1,000,000 / sum(reference_tokens)
```

For logits-bias methods, both embedding and extraction use generated completion
tokens. For CodeMark and SrcMarker, embedding uses input-source tokens and
extraction uses tokens in the corresponding watermarked source. All reference
counts use the released Qwen3-Coder tokenizer manifest.
