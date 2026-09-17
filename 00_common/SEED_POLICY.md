# Seed policy

## RQ1

Stage-0 architecture generation used the pinned hosted model recorded in
`RQ1/01_task_specs/manifest.json`; hosted architecture responses are treated as
serialized inputs rather than claimed to be reproducible from a random seed.
The 42 retained `team.json` checkpoints are therefore the canonical downstream
inputs.

Stage-1 repository generation injects an explicit seed into the local model
service. A seed is scoped to the joint hash of the architecture checkpoint and
initial repository. The campaign resets CPU/CUDA RNG state behind a global
generation lock. Strict cross-hardware byte identity is not claimed because
the Qwen3-MoE `_histc` path lacks a deterministic CUDA implementation. The
released applicability bundle includes its realized seed inventory and seed
fields in the point table. The baseline campaign evidence is released
separately at `results/RQ1/05_baseline_qualification/`: all 88 final-epoch
attempt seeds, 42 accepted seeds and repository hashes, and 42 same-seed replay
records and logs are retained there.

## RQ2

- Fresh training seed: 42 for every method/dataset cell.
- Rule and LLM global seed: 42.
- Rule sample seed: the first 32 bits of
  `SHA256(global_seed || sample_uid || channel)` using the implementation's
  documented delimiter/encoding.
- LLM sample seed: first four bytes, big-endian unsigned, of
  `SHA256("42\0<sample_uid>\0llm-rag-all")`.
- Bootstrap: 10,000 paired sample-level replicates; seed 42 (with the archived
  deterministic per-comparison offsets for common-valid method contrasts).

Every realized sample seed is retained in the corresponding JSONL row.
