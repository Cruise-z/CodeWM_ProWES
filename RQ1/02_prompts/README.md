# RQ1 prompt evidence

This directory is organized by the two prompt-bearing stages used by the
released 14-project × 3-language campaign. It is not a catalog of hand-written
project modules.

| Directory | Experimental meaning | Coverage |
|---|---|---:|
| `stage0/` | Exact architecture-synthesis user payloads | 42 units (14 C++, 14 Java, 14 Python) |
| `stage1/` | Exact accepted-run `WriteCode` system/user prompts and input contexts | 480 file-generation actions |

The formal campaign inventory is defined by
`../01_task_specs/manifest.json`. This directory contains only prompts that
define or participate in the released 42-unit campaign.

`build_prompt_bundle.py` deterministically rebuilds both prompt manifests and
all rendered prompt files from the immutable architecture checkpoints and
accepted baseline evidence:

```bash
python3 RQ1/02_prompts/build_prompt_bundle.py
```

The builder fails unless every Stage-0 prompt matches its recorded hash, every
checkpoint matches its recorded hash, all 480 Stage-1 actions align with their
accepted generation reports, and every pre-normalization source file is
restored uniquely to its experiment-time SHA-256.

See `stage0/README.md` and `stage1/README.md` for the precise evidence boundary
and reconstruction method. Aggregate counts and frozen implementation hashes
are in `bundle_summary.json`.
