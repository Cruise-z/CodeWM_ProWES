# Reference-token counts

`token_counts.csv` is generated from the authoritative raw timing JSON and
contains one row per measured invocation. `tokenizer_manifest.json` identifies
the shared Qwen tokenizer and hashes its vocabulary assets.

For logits-bias rows, the ledger records both watermarked and paired WM-OFF
completion counts and output hashes. Both members are fixed at 256 tokens;
completion tokens normalize embedding, while independently tokenized final text
normalizes standalone extraction. Pair order is retained. Semantic rows use
input-source tokens for embedding and watermarked-source tokens for extraction;
they additionally retain pre-truncation internal tokens, 512-token model inputs,
and truncation flags.
