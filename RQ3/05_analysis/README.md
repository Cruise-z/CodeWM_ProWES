# Table X reproduction

`reproduce_table_x.py` reads the three raw timing files, recomputes every
normalized point estimate from raw seconds and reference-token counts, parses
the canonical CSN-JavaScript training logs, and writes CSV, JSON, and LaTeX
versions of Table X. It also materializes reviewer-friendly flat ledgers in
`RQ3/02_raw_timings/raw_timings.csv` and `RQ3/04_token_counts/token_counts.csv`.
Before writing outputs it verifies schema-v2/v7 contracts, normalization,
hashes, one-to-one baseline linkage, paired subtraction, fixed lengths, 15/15
within-method pair balance, zero generation-time observation, standalone
detector state, internal semantic token counts, run counts, and both released
semantic checkpoint digests. SWEET must use `ET=0.5`, score positive tokens,
and report independent model-forward entropy provenance.

All 95% intervals are recomputed from raw rows with 10,000 replicates. Logits
methods use workload-cluster hierarchical bootstrap; semantic methods use
sample bootstrap. Embedded intervals are not used as Table X inputs.

From the artifact root:

```bash
./paper_reproduction/reproduce_rq3.sh
```

Normalization is ratio-of-sums:

```text
ms_per_1k = sum(elapsed_seconds) * 1,000,000 / sum(reference_tokens)
```

For logits-bias methods, Table X embedding is `watermarked generation time -
adjacent WM-OFF generation time`. Embedding uses completion tokens; extraction
uses independently tokenized final text. For CodeMark and SrcMarker, embedding
uses input-source tokens and extraction uses watermarked-source tokens. All
reference counts use the released Qwen3-Coder tokenizer manifest.
