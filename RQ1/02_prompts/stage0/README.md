# Stage-0 architecture prompts

`rendered/<project>/<language>/user_prompt.txt` contains the exact user idea
payload passed to `Team.run(..., idea=prompt)` for each formal RQ1 unit. There
are 42 files: 14 projects in each of C++, Java, and Python.

`prompt_manifest.csv` and `prompt_manifest.json` bind every prompt to:

- its SHA-256 from the architecture evidence;
- the serialized `team/team.json` checkpoint and checkpoint SHA-256;
- the requested architecture model identifier and API base URL; and
- the canonical copy under `RQ1/03_architecture_checkpoints/`.

The renderer is `build_architecture_prompt` in
`RQ1/source/reproduct/campaign.py`; the project/language parameters are in
`RQ1/01_task_specs/manifest.json`.

## Evidence boundary

Stage 0 used a multi-role MetaGPT workflow, so the architecture idea was
expanded into several internal role/action turns. The experiment retained the
exact idea payload, generated documents, logs, serialized final agent state,
model/base-URL identity, and hashes. It did not retain every provider-level
HTTP request body for those internal turns. The artifact therefore releases
the exact outer user payload and the complete resulting checkpoint, while the
frozen framework under `RQ1/source/reproduct/framework/metagpt/` defines the
internal prompt construction. It does not invent missing provider requests.
