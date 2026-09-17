# RQ1 — project-structured applicability and detectability

This directory contains the latest source and immutable inputs from
`CodeWM_ProWES_Logits` commit `9c647f9a8d4e9bd519aefac7c0a8b6dc501cafaa`.

Evidence map:

1. `01_task_specs/manifest.json`: 14 medium-size tasks × C++/Java/Python,
   generation parameters, architecture backend, and acceptance protocol.
2. `02_prompts/templates/`: language/task prompt source.
3. `03_architecture_checkpoints/`: 42 rendered `prompt.txt` files, serialized
   `team/team.json` agent state, architecture evidence/log, and corresponding
   `initial_repository` input. These checkpoints permit downstream generation
   without recalling the proprietary Stage-0 model.
4. `04_docker/`: frozen Docker/Podman evaluator and build/test/run protocol.
5. `06_watermark_configs/`: method registry and batch configuration schema.
6. `source/DT/codeGen/`: generation, watermark, detector, timing, and sweep code.
7. `source/reproduct/`: resumable campaign driver, frozen framework, model
   runtime, model identifiers, deterministic seed protocol, and audit logic.

`source/reproduct/units` is a relative link to the reviewer-facing checkpoint
tree, so `python RQ1/source/reproduct/campaign.py status` recognizes all 42
architectures without duplicating them.

The supplied result archives are expanded under `../results/RQ1/`. They add
9,141 point-level applicability rows, 298 batch summaries, four aggregate
detectability logs, and their analysis scripts. Run
`../paper_reproduction/reproduce_rq1.sh` to verify and regenerate the released
outputs.

The result archives do not contain the complete baseline-attempt/replay
ledger, accepted repository snapshots, per-point Docker logs, or per-sample
detector scores. The architecture checkpoints here are canonical inputs, but
they are not a substitute for those absent observations. The exact boundary is
recorded in `../ARTIFACT_COMPLETENESS.md` and `../results/RQ1/README.md`.
