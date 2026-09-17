# RQ2 source artifact

This credential-free archive contains the implementation required to train the two methods,
generate clean watermarked code, run deterministic rule attacks, execute the LLM-RAG attack,
validate transformations on MBXP, extract watermarks, compute paired metrics and confidence
intervals, and regenerate tables/figures.

The archive intentionally excludes datasets, API credentials, raw model checkpoints, runtime
logs, caches, and generated attack outputs. Checkpoint SHA-256 values and training provenance are
recorded in the delivered experiment report; `training_history.json` and `run_manifest.json` are
included. Reproduction requires obtaining the public datasets and supplying a local mode-600
credential file for the configured OpenAI-compatible provider.

Start with `README_REVISION.md`. Run unit tests with:

```bash
PYTHONPATH=.deps pytest -q
```

The complete source inventory and SHA-256 hashes are stored in `SOURCE_MANIFEST.json`.
