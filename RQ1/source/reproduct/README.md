# MetaProjectDev 42-unit reproducibility campaign

This directory is the experiment ledger for the requested 14 projects × C++,
Java, and Python against `CodeWM_ProWES_Logits`. Because the requested total is
42 rather than 84, the campaign fixes the **Medium** tier. The supplied
file/function/LOC values are preserved as descriptive references. The realized
file count produced by each architecture run is authoritative; build/test
success remains mandatory.

## Acceptance and replay rules

A seed is accepted only when every planned file finishes without truncation and
the frozen `evaluator/test_podman.sh` returns 0. Final audit additionally
requires one independent replay with the same seed that:

- finishes generation and passes the evaluator again;
- produces the same canonical repository tree SHA-256;
- uses the same architecture `team.json`, generation order, settings, frozen
  framework, model runtime, weights, and recorded software/hardware class.

Attempts are scoped to an exact architecture epoch, identified jointly by the
SHA-256 of `architecture/team/team.json` and `initial_repository/`. Rebuilding
an architecture invalidates every seed tried against the previous pair. Those
attempts remain as audit evidence but are excluded from current statistics;
the replacement architecture starts again at attempt 1. An accepted seed is
valid only when its recorded architecture and initial-repository hashes match
the current epoch.

The protocol paths are:

- Java: `pom.xml`, `src/main/java/Main.java`, `src/test/java/MainTest.java`
- Python: `requirements.txt`, `Main.py`, `tests/test_main.py`
- C++: `CMakeLists.txt`, `src/Main.cpp`, `tests/test_main.cpp`

## Layout

Each unit is under `units/pNN_<project>/<language>/`:

```text
architecture/{prompt.txt,team/team.json,evidence.json,architecture.log}
initial_repository/<unit>/
attempts/NNNN_seed_<seed>/<unit>/<generated-unit>/
attempts/NNNN_seed_<seed>/{generation_report.json,evaluator.log,evidence.json}
accepted/{repository,seed.json,evidence.json}
replays/NNNN_seed_<seed>/{repository,generation_report.json,evaluator.log,evidence.json}
architecture_failures/<epoch>/{...,attempts/,initial_repository/,accepted/,replays/}
interrupted_attempts/<epoch>/NNNN_seed_<seed>/
```

Failed/replaced architecture snapshots, their initial repositories, seed
attempts, accepted repository, and exact replays are retained together under
`architecture_failures/`. Attempts
interrupted only to perform an epoch migration are retained separately and do
not count as completed seed tests. `evidence/attempt_epoch_migration_latest.json`
records the historical migration and renumbering.
`campaign_state.json` is a derived live index. `results.csv` and `results.json`
are the paper-friendly result tables. `audit.json` is authoritative only when
`complete` is true and reports 42 accepted plus 42 hash-identical replays.

## Running the campaign

Use the frozen source copies. For this final campaign, every current architecture
must use the remote OpenAI-compatible API endpoint and model pinned in
`manifest.json`. The audit records every unit's architecture endpoint/model and
cannot become complete while a local or missing architecture backend remains.
The architecture API is not needed to replay a retained snapshot.

```bash
export PYTHONPATH="$PWD/reproduct/framework:$PWD/reproduct/tools:$PWD/DT/codeGen"
PY=/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python

$PY reproduct/campaign.py preflight
$PY reproduct/campaign.py architecture --all
$PY reproduct/campaign.py status
```

An explicit local endpoint can be used for diagnostics, but such an epoch is not
eligible for the final audit. Its evidence still records an unambiguous backend:

```bash
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8001 \
CODEWM_ARCHITECTURE_BASE_URL=http://127.0.0.1:8001/v1 \
CODEWM_ARCHITECTURE_MODEL=/absolute/path/to/Qwen3-Coder-30B-A3B-Instruct \
CODEWM_ARCHITECTURE_API_KEY=local-not-secret \
CODEWM_ARCHITECTURE_MAX_TOKENS=8192 \
CODEWM_ARCHITECTURE_REBUILD_REASON='concise auditable reason' \
$PY reproduct/campaign.py architecture --unit <unit-id> --force
```

`architecture/evidence.json` stores the selected API type, endpoint, and model,
the optional rebuild reason, but never the API key. A backend change creates a
new architecture epoch; all
seed attempts from the replaced epoch are archived and excluded from current
attempt counts. For the local planner, the runner carries the complete normative
prompt through PRD, system-design, and task Full-API stages before the Engineer
constructs its ordered code todos; the evidence field
`architecture_requirement_propagation` records that transformation. The
QR/Python planner uses a deterministic compact binding in the system-design to
task transition because verbatim nested code literals repeatedly produced
invalid JSON; its PRD and downstream authoritative Full API still retain the
complete prompt, and the evidence records this exception. The
planner's pre-normalization task document is retained as
`architecture/model_task_raw.json` and its SHA-256 is recorded in evidence;
the task Full API used by downstream generation is the authoritative normative
prompt, so a shorter model summary cannot silently override the tested contract.

When an accepted local-backend epoch must be replaced after API service is
restored, use the explicit destructive-scope flag below. It requires `--force`
and archives the old architecture, all attempts, accepted repository, and
replays as one epoch before rebuilding; the new attempt count starts at 1.

```bash
$PY reproduct/campaign.py architecture --unit <unit-id> --force --replace-accepted
```

`run_api_rebuild_queue.sh` applies this operation only to the audited list of
local-backend units, skips units already valid on the pinned remote API, and
retries transient architecture failures without losing their evidence.

For Java units, unqualified class filenames in that generated task are mapped
to the evaluator's Maven source roots before Engineer todos are constructed;
`task_path_normalization` records this deterministic transformation while the
raw document remains available for comparison.

Start one local model server per available GPU. The example below is the exact
campaign mode; strict PyTorch determinism is deliberately off for the documented
Qwen3-MoE `_histc` limitation.

```bash
CUDA_VISIBLE_DEVICES=3 CODEWM_MODEL_PORT=8000 reproduct/run_model_server.sh
CUDA_VISIBLE_DEVICES=2 CODEWM_MODEL_PORT=8001 reproduct/run_model_server.sh
```

Seed search and replay can be sharded. Keep the same shard mapping for replay so
each unit returns to the same recorded GPU/model endpoint.

```bash
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000 CODEWM_SHARD_INDEX=0 reproduct/run_seed_worker_forever.sh
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8001 CODEWM_SHARD_INDEX=1 reproduct/run_seed_worker_forever.sh

CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000 $PY reproduct/campaign.py replay-worker --shard-count 2 --shard-index 0
CODEWM_MODEL_BASE_URL=http://127.0.0.1:8001 $PY reproduct/campaign.py replay-worker --shard-count 2 --shard-index 1

$PY reproduct/campaign.py fingerprint-model
$PY reproduct/campaign.py audit
```

The supervised seed workers lock onto one repository and draw fresh random
seeds without a per-unit limit until that repository passes. They advance only
after acceptance and restart automatically after an unexpected worker exit.
Before advancing past an accepted repository, the default supervisor waits for
its hash-identical replay. If the next repository's architecture was produced
from stale inputs, it archives that entire epoch, rebuilds the architecture,
sets the per-unit evidence reason to
`automatic_stale_input_rebuild_<unit-id>` (overriding any unrelated reason
inherited by the long-lived supervisor), and only then resumes seed search.
Set `CODEWM_AUTO_REBUILD_STALE=0` only when
architecture refreshes are intentionally managed by a separate worker.
The active repository is recorded in `worker_state/seed_shard_<i>_of_<n>.json`,
so a process or machine-session restart resumes that repository even when an
earlier manifest entry has become ready in the meantime.
For runs that must survive the calling shell, launch the model supervisors and
workers in detached `tmux` sessions. Runtime logs are appended under
`reproduct/logs/`. `run_model_server_forever.sh` restarts a crashed local model,
and `run_architecture_worker_forever.sh` retries only missing or stale
architectures while preserving failed architecture attempts.
`run_replay_worker_forever.sh` watches accepted repositories and performs one
same-seed replay. It stops on a deterministic mismatch so the mismatch remains
visible for investigation.
All commands are resumable. Valid architectures, accepted seeds, and verified
replays are skipped. See `REPRODUCIBILITY.md` for the exact reproducibility
boundary and cross-machine interpretation.
