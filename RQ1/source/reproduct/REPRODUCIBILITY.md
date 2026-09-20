# RQ1 reproducibility boundary

## Reproduction targets

The experiment distinguishes two targets:

1. **Functional reproduction:** a retained repository builds, tests, and runs
   under the frozen evaluator. This is the mandatory acceptance criterion.
2. **Byte-identical replay:** regeneration with the same inputs produces the
   same canonical source-tree SHA-256. This stricter property is verified by
   the 42 released same-seed replays in the recorded environment.

## Fixed generation inputs

- task, language, and sampling parameters from `manifest.json`;
- serialized architecture state in `architecture/team/team.json`;
- initial repository and ordered `Engineer.code_todos` file list;
- exact Stage-1 rendered prompts and prior-file context;
- Qwen3-Coder-30B-A3B-Instruct model weights, tokenizer, and chat template;
- `temperature=0.7`, `top_p=1.0`, `max_tokens=4096`, and per-request RNG seed;
- frozen MetaGPT, `WriteCode`, model-server, and generation source;
- disabled watermark processors for the delta-zero baseline.

## Fixed runtime and evaluator

- Python, PyTorch, Transformers, CUDA, cuDNN, and driver versions;
- GPU model, dtype, device map, memory policy, and concurrency policy;
- Docker/Podman version and evaluator image identity;
- Java/Maven, Python/pytest, and CMake/GCC versions;
- evaluator scripts, timeouts, and dependency configuration.

The exact recorded environment is under `00_common/environment/` and
`00_common/hardware/`.

## Determinism boundary

The model service injects the request seed and serializes access to the global
CPU/CUDA RNG when the model path cannot accept a private generator. Strict
deterministic-algorithm mode is unavailable because the recorded Qwen3-MoE
stack uses CUDA operations without deterministic implementations. Therefore a
seed alone is not a cross-machine byte-identity guarantee.

The defensible portable claim is functional reproduction with the frozen
evaluator. Byte identity is an observed result for the released replays under
the recorded software and hardware fingerprint and is checked through source
tree hashes.

## Final evidence entry points

- `results/RQ1/05_baseline_qualification/ledger/`: final campaign state,
  result tables, and integrity audit;
- `results/RQ1/05_baseline_qualification/indexes/attempt_ledger.csv`: all 88
  completed attempts;
- `results/RQ1/05_baseline_qualification/indexes/accepted_ledger.csv`: 42
  accepted seeds and repositories;
- `results/RQ1/05_baseline_qualification/indexes/replay_ledger.csv`: 42 replay
  comparisons;
- `results/RQ1/05_baseline_qualification/units/*/*/`: generation reports,
  evaluator logs, accepted repositories, replay repositories, and hashes;
- `RQ1/02_prompts/`: exact rendered Stage-0 and accepted-run Stage-1 prompts;
- `RQ1/03_architecture_checkpoints/`: serialized architecture state and initial
  repositories.
