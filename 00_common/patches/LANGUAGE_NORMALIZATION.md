# Release-language policy

Reviewer-facing first-party source, documentation, configuration, and report
builders are released in English. The final file identities are recorded by
`ARTIFACT_MANIFEST.json` and `SHA256SUMS.txt`.

The following provenance-bearing content remains byte-faithful and is excluded
from translation:

- raw RQ1 and RQ2 observations and execution logs;
- rendered prompts and generated architecture/repository content;
- frozen upstream MetaGPT, RAG, and watermark implementation snapshots;
- test fixtures whose Unicode values are part of accepted repository hashes.

The active RQ1 runtime, synchronized generation copy, RQ2 pipeline, release
documentation, and paper-reproduction entry points are covered by
`tools/check_release_language.py`. Language normalization does not alter raw
predictions, checkpoints, timing values, prompts, or statistical results.
