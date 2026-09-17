# Reproduction boundary and environment granularity

## Summary

A fixed `rng_seed` fixes only the sampling random stream; it does not uniquely
determine a generated repository. Reconstructing identical content also
requires fixed prompts, architecture state, file-generation order, model and
tokenizer, sampling implementation and parameters, framework source, inference
software stack, and the hardware/driver conditions that affect floating-point
execution.

This experiment distinguishes two targets:

1. **Functional reproduction:** the repository still builds, tests, and runs
   under the frozen ProWES container protocol. This is the mandatory acceptance
   criterion for the 42 retained project-language inputs and is generally
   portable across machines.
2. **Byte-identical generation reproduction:** regenerating with the model
   yields identical SHA-256 values for every source file. This is substantially
   stricter. The current Qwen3-MoE/CUDA stack cannot guarantee it across
   arbitrary machines, so it is assessed empirically through replay and hashes.

## Architecture versions and attempt accounting

A seed is valid only for the architecture version against which it was tried.
An architecture version is jointly identified by the SHA-256 of
`architecture/team/team.json` and the tree hash of `initial_repository/`.
Changing either input invalidates all seeds tried against the previous pair;
those attempts cannot count toward a new architecture or serve as acceptance
evidence for it.

When an architecture is rebuilt, the old architecture, initial repository,
attempts, accepted repository, and replays move together to
`architecture_failures/<epoch>/`. Attempt numbering restarts from one for the
new architecture. An accepted seed from an older epoch remains historical
evidence only and is not copied into the new epoch or counted as a current
success. Individually interrupted attempts from early accounting migrations are
retained in `interrupted_attempts/`; attempts interrupted directly by an
architecture replacement are archived with the complete old epoch. Neither
counts as a seed trial for the new architecture. Migration details are recorded
in `evidence/attempt_epoch_migration_latest.json`.

## Conditions that must be fixed

### Generation inputs

- task, language, size, and sampling parameters in `manifest.json`;
- each unit's `architecture/prompt.txt`;
- the actual code-generation input `architecture/team/team.json`;
- the file list and order in `Engineer.code_todos`;
- the rule for appending previously generated files as later-file
  `Legacy Code`;
- ProWES first-line `## filename` normalization.

### Model and algorithm

- the remote OpenAI-compatible API endpoint and `gpt-5` model fixed by
  `manifest.json` for architecture generation; the realized endpoint/model
  for each current epoch is in `architecture/evidence.json`, and the final
  audit rejects local or missing provenance;
- the retained `team.json`, raw/normalized task documents, and their hashes as
  the canonical downstream input, because a hosted architecture response is
  not claimed to be byte-reconstructible from a seed alone; code-generation
  seed replay does not call the architecture API again;
- exact Qwen3-Coder-30B-A3B-Instruct weights, configuration, tokenizer, and
  chat template;
- `temperature=0.7`, `top_p=1.0`, `max_tokens=4096`, sampling switch, and
  `rng_seed`;
- watermark/logits-processor names, parameters, and registration order; all
  processors are disabled for baseline generation;
- the model service, Transformers `generate()` path, and MetaGPT/WriteCode
  source;
- explicit per-request seed injection and the server-side global RNG lock.

### Runtime environment

- Python, PyTorch, Transformers, CUDA runtime, cuDNN, and CUBLAS versions;
- NVIDIA driver, GPU model, compute capability, and preferably the same GPU
  SKU;
- dtype, device map, memory policy, deterministic environment variables, and
  concurrency policy;
- operating system, CPU architecture, locale, timezone, and thread-related
  environment variables.

### Acceptance environment

- Podman/Docker version and immutable evaluator image ID/digest;
- SHA-256 values for `evaluator/test_podman.sh` and
  `evaluator/docker/eval_protocol.sh`;
- Java/Maven, Python/pip/pytest, CMake/GCC, and dependency-source versions;
- network availability and dependency-cache state. The strongest replay setup
  preinstalls all dependencies in an immutable image and runs offline.

## Determinism limitations in the recorded environment

The model service first attempts to use a request-private
`torch.Generator`. The recorded Transformers/Qwen3-MoE path does not accept
that generator, so the implementation resets the global CPU/CUDA RNG under a
process-wide mutex before generation. This isolates concurrent requests within
one service process.

Strict deterministic-algorithm mode is unavailable for the recorded model:
Qwen3-MoE calls `_histc`, which lacks a deterministic CUDA implementation.
The same seed therefore is not a mathematical guarantee across GPU models,
drivers, or PyTorch versions. The retained repository and tree hash are the
canonical result; replay must compare file hashes rather than only checking
whether tests pass.

## Cross-machine expectations

- **Move and execute a retained repository:** high feasibility when using the
  same evaluator image and protocol.
- **Regenerate on the same GPU model with identical driver, CUDA, PyTorch,
  Transformers, weights, and source:** medium-to-high feasibility, but hashes
  must still be checked.
- **Demand byte-identical source across different GPUs or numerical stacks:**
  not a defensible guarantee. Floating-point reductions, kernel choice, or a
  tiny logits difference can change one sampled token and amplify into wholly
  different text.

The defensible paper claim is that retained repositories pass the frozen
evaluator. A claim that a fixed seed regenerates the same SHA-256 is limited to
the recorded hardware/software fingerprint and must report the observed replay
success rate separately.

## Evidence entry points

- `evidence/preflight.json`: model, framework, container, and environment
  fingerprints;
- `campaign_state.json`: progress index for all 42 units;
- `audit.json`: final integrity audit, architecture API provenance, seeds, and
  repository tree hashes by unit;
- `units/*/*/architecture/evidence.json`: architecture-input and snapshot
  hashes;
- `units/*/*/attempts/*/evidence.json`: every random attempt and failure
  stage;
- `evidence/attempt_epoch_migration_latest.json`: archived older-architecture
  attempts, current-architecture renumbering, and exclusions;
- `units/*/*/accepted/`: final seed, passing-log reference, and canonical
  repository.
