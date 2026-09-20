# RQ1 — project-structured applicability and detectability

This directory contains the final source and immutable inputs from
`CodeWM_ProWES_Logits` commit `1d4f0cbad7fb76a31684b615dfe4f880ca7ee176`.

Evidence map:

1. `01_task_specs/manifest.json`: 14 medium-size tasks × C++/Java/Python,
   generation parameters, architecture backend, and acceptance protocol.
2. `02_prompts/`: reviewer-facing prompt evidence. It contains 42 exact
   Stage-0 architecture payloads and 480 exact accepted-run Stage-1 `WriteCode`
   prompts/contexts, with per-request hashes and a deterministic builder.
3. `03_architecture_checkpoints/`: 42 canonical rendered `prompt.txt` files,
   serialized
   `team/team.json` agent state, architecture evidence/log, and corresponding
   `initial_repository` input. These checkpoints permit downstream generation
   without recalling the proprietary Stage-0 model.
4. `04_docker/`: frozen Docker/Podman evaluator and build/test/run protocol.
5. `05_baseline_qualification/`: baseline protocol and link to the complete
   final-epoch observations under `results/RQ1/05_baseline_qualification/`.
6. `06_watermark_configs/`: method registry and batch configuration schema.
7. `source/DT/codeGen/`: generation, watermark, detector, timing, and sweep code.
8. `source/reproduct/`: resumable campaign driver, frozen framework, model
   runtime, model identifiers, deterministic seed protocol, and audit logic.

`source/reproduct/units` is a relative link to the reviewer-facing checkpoint
tree, so `python RQ1/source/reproduct/campaign.py status` recognizes all 42
architectures without duplicating them.

The result evidence under `../results/RQ1/` includes 88 baseline attempts, 42
accepted repository snapshots, 42 verified replays, 9,141 point-level
applicability rows, 298 batch summaries, four aggregate detectability logs,
and the corresponding audit/analysis scripts. Run
`../paper_reproduction/reproduce_rq1.sh` to verify and regenerate the released
outputs.

The baseline qualification chain is complete. The separate strength-sweep and
detectability archives still do not contain per-point Docker logs/repository
snapshots or per-sample detector scores. The exact boundary is recorded in
`../ARTIFACT_COMPLETENESS.md` and `../results/RQ1/README.md`.
