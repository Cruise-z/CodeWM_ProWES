# Historical prompt modules (not the formal RQ1 matrix)

These files are a byte-preserved source snapshot from the older
`RQ1/source/DT/codeGen/prompts/` tree. They contain 5 C++ task modules, 11 Java
task modules, and 4 Python task modules. That uneven coverage reflects the
historical development tree; it is not the 14-project × 3-language experiment
definition and is not consumed by the released `reproduct/campaign.py` flow.

The files were previously published under the ambiguous path
`RQ1/02_prompts/templates/`. They have been moved here so reviewers do not
mistake them for the complete formal prompt set. The authoritative campaign
inputs are:

- `../stage0/`: all 42 rendered architecture prompts; and
- `../stage1/`: all 480 accepted-run file-generation prompts and contexts.

They remain in the artifact solely to preserve the provenance of the legacy
DT source tree and are still tracked by Git.
