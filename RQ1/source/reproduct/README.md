# MetaProjectDEV 42-unit campaign

This is the final RQ1 campaign implementation for 14 medium-size projects in
C++, Java, and Python. The released result ledger is under
`results/RQ1/05_baseline_qualification/`.

## Final qualification protocol

A seed is accepted only when every planned file finishes without truncation
and the frozen evaluator returns zero. Each accepted seed is replayed once with
the same generation inputs. A replay is verified only when it passes again and
its canonical repository-tree SHA-256 matches the accepted repository.

The final campaign contains:

- 42 project-language units;
- 88 completed generation attempts, including 42 passes and 46 failures;
- 42 accepted repositories;
- 42 successful same-seed, hash-identical replays.

The failed attempts are retained because they are part of the final baseline
qualification protocol.

## Frozen inputs

- `manifest.json`: tasks, model identifiers, sampling settings, and seed policy.
- `framework/`: frozen MetaGPT runtime used by architecture and code generation.
- `model_runtime/`: model server and watermark runtime.
- `evaluator/`: Docker/Podman build, test, and execution oracle.
- `tools/agentCodeGen.py`: exact code-generation action.
- `units`: link to the 42 reviewer-facing serialized checkpoints under
  `RQ1/03_architecture_checkpoints/`.

## Reproduction commands

From `RQ1/source/`:

```bash
export PYTHONPATH="$PWD/reproduct/framework:$PWD/reproduct/tools:$PWD/DT/codeGen"
python reproduct/campaign.py preflight
python reproduct/campaign.py status
```

The released serialized Stage-0 checkpoints allow downstream baseline
generation without calling the proprietary architecture model again. Start a
model server, then run seed search and replay workers:

```bash
CUDA_VISIBLE_DEVICES=0 CODEWM_MODEL_PORT=8000 reproduct/run_model_server.sh
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000 \
  reproduct/run_seed_worker_forever.sh
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000 \
  reproduct/run_replay_worker_forever.sh
python reproduct/campaign.py audit
```

All generation requests record the RNG seed, checkpoint hashes, generation
order, model/tokenizer identifiers, software/hardware fingerprint, evaluator
result, and canonical repository hash.

## Reviewer verification

From the Artifact root:

```bash
python tools/verify_rq1_evidence.py
./paper_reproduction/reproduce_rq1.sh
```

The verifier checks the complete 88/42/42 ledger, all evidence links, evaluator
logs, accepted/replay repository hashes, prompt bundles, strength-sweep data,
and detectability data.

See `REPRODUCIBILITY.md` for the exact determinism boundary.
