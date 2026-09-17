# Stage-1 file-generation prompts

This directory exposes the actual prompt inputs for the accepted unwatermarked
baseline generation. It contains 480 ordered `WriteCode` actions across the 42
formal RQ1 units.

For each action,
`rendered/<project>/<language>/<index>__<filename>/` contains:

- `user_prompt.txt`: the exact rendered `WriteCode` user message;
- `input_context.json`: the serialized design/task/code context from the
  architecture checkpoint; and
- `request_metadata.json`: hashes, seed, model/response metadata, visible
  earlier files, and links to the checkpoint and accepted generation report.

`system_prompt.txt` is the fixed Engineer system message installed by
`Role.set_actions`. `prompt_manifest.csv` and `prompt_manifest.json` index all
480 requests.

## Why the prompts are reconstructable

The campaign did not write a separate copy of each user message at request
time. It did retain all inputs needed by the frozen `WriteCode.run` path:

1. `Engineer.code_todos` stores the ordered file name plus complete design and
   task documents.
2. Each accepted `generation_report.json` stores the ordered file list and the
   SHA-256 of each generated source before evaluator cleanup.
3. Each accepted repository stores the source after cleanup. For 316 files it
   already matches the generation hash. For 164 files, restoring the exact
   leading line `## <filename>` produces the unique recorded generation hash;
   this reverses `remove_leading_h2_line`.
4. Earlier sources are inserted in the frozen task-list order using the exact
   `WriteCode.get_codes` separators.
5. Fresh baseline generation has empty debug-log, bug-feedback, and code-summary
   fields. The frozen `PROMPT_TEMPLATE` is then formatted with those values.

`../build_prompt_bundle.py` performs these checks before writing a prompt. The
result is labelled `exact_reconstruction_from_immutable_run_state` rather than
being misrepresented as a separately captured HTTP request body.

The response IDs, returned model names, finish reasons, usage counts, response
hashes, and generated-code hashes remain linked in each metadata record. Raw
provider response text was not retained and is not reconstructed.
