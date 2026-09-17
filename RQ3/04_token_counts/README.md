# Reference-token counts

`token_counts.csv` is generated from the authoritative raw timing JSON and
contains one row per measured invocation. `tokenizer_manifest.json` identifies
the shared Qwen tokenizer and hashes its vocabulary assets.

For logits-bias rows, generated completion tokens normalize both embedding and
extraction. For semantic-preserving rows, input-source tokens normalize
embedding and watermarked-source tokens normalize extraction.
