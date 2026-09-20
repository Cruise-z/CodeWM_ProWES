# Reference-token counts

`token_counts.csv` is generated from the authoritative raw timing JSON and
contains one row per measured invocation. `tokenizer_manifest.json` identifies
the shared Qwen tokenizer and hashes its vocabulary assets.

For logits-bias rows, the ledger records both watermarked and paired WM-OFF
completion counts and output hashes. Both members are fixed at 256 tokens;
generated completion tokens normalize embedding and extraction. Pair order is
also retained. For semantic-preserving rows, input-source tokens normalize
embedding and watermarked-source tokens normalize extraction.
