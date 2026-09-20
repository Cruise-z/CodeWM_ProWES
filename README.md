# ProWES Artifact

This repository is the reviewer-facing artifact for *Beyond Snippets: A
Project-Structured Empirical Study of Watermarking for LLM-Generated Code*.
It is organized around the paper's research questions and preserves the
evidence chain

```text
input/configuration -> intermediate artifact -> raw observation
                    -> statistical script -> paper table/figure
```

## Quick start

```bash
# Check the released RQ1 bundles and the formal RQ2 evidence.
python tools/verify_rq1_evidence.py
python tools/verify_rq2_evidence.py

# Regenerate all supported paper outputs, including Table X from raw timings.
./paper_reproduction/reproduce_all.sh

# Confirm reviewer-facing first-party source and documentation are English.
python tools/check_release_language.py

# Or run one RQ independently.
./paper_reproduction/reproduce_rq1.sh
./paper_reproduction/reproduce_rq2.sh
./paper_reproduction/reproduce_rq3.sh

# Verify every released payload against SHA256SUMS.txt.
python tools/artifact_manifest.py --verify
```

The reproduction steps do not call an LLM or retrain a model. They rebuild
paper outputs from released observations and statistical summaries. Full RQ2
experiment-rerun commands are documented in `RQ2/source/README_REVISION.md`.

## Layout

| Path | Purpose |
|---|---|
| `00_common/` | Environment, hardware, revisions, upstream repositories, and disclosure of known gaps. |
| `RQ1/` | Latest logits-bias implementation, task specifications, 42 Stage-0 prompts, 480 accepted-run Stage-1 prompts/contexts, serialized architecture checkpoints, initial repositories, and evaluator. |
| `RQ2/` | Fresh-training, rule attack, MBXP, LLM+RAG, detector, and statistics source code. |
| `RQ3/` | Counterbalanced paired WM-OFF timing harnesses, processor-only attribution records, detector timings, shared-tokenizer counts, training logs, normalization, and Table X reproduction. |
| `results/RQ1/` | Complete baseline qualification evidence plus expanded applicability and detectability evidence. |
| `results/RQ2/` | Formal RQ2 datasets/splits, checkpoints, logs, raw attacks, predictions, MBXP executions, LLM manifests/responses, statistics, tables, and figures. |
| `paper_reproduction/` | Reviewer entry points for rebuilding paper outputs. |
| `ARTIFACT_MANIFEST.csv/json` | Machine-readable file-to-RQ/evidence map. |
| `SHA256SUMS.txt` | Integrity digests for the released payload. |

See `ARTIFACT_COMPLETENESS.md` before release. It distinguishes present
evidence from material that was not found in the supplied workspaces. No
missing observation was synthesized.

## Scope and important boundaries

- RQ1 contains all 88 current-epoch baseline attempts, 42 accepted repository
  snapshots, 42 verified replays, 9,141 point-level applicability rows, 298
  batch summaries, four aggregate detectability logs, and reproducible derived
  tables/figures. The strength-sweep bundles do not contain their referenced
  per-point Docker logs/repository snapshots, and the detectability bundle does
  not contain per-sample detector scores; those portions remain explicitly
  incomplete.
- RQ2 is complete for the paper's formal fresh-checkpoint, rule-based, MBXP,
  and 1,000-request LLM+RAG analyses. The supplied CSN training corpora were
  not present in the release workspace; stable test observations and cohort
  UIDs are present, while the original CSN train/validation downloads must be
  obtained as documented by SrcMarker.
- API credentials are deliberately excluded. Formal LLM rows retain request
  parameters, per-sample seeds, response identifiers, returned model snapshot,
  token usage, retrieved rules, prompt digest, raw response-derived source,
  and validity status.
- Chinese text is absent from reviewer-facing first-party scripts and
  documentation checked by `tools/check_release_language.py`. Immutable raw
  observations, generated Stage-0 artifacts, and frozen third-party/upstream
  snapshots remain byte-faithful and may contain multilingual text; see
  `00_common/LANGUAGE_AUDIT.md`.

## Large files

Eight `models_best.pt` files are tracked with Git LFS. Together they are about
4.3 GB and are the exact checkpoints used for final RQ2 detection. Reviewers
who only need the reported tables can skip LFS checkout and use the already
released statistics; checkpoint verification and detector reruns require the
LFS objects.

## Facts checked by the verifiers

RQ1:

- 42 exact Stage-0 architecture payloads (14 per language) and 480 exact
  accepted-run Stage-1 file-generation prompts with checkpoint/source hashes.
- 88 baseline generation attempts: 42 accepted and 46 failed attempts.
- 42 accepted canonical repositories and 42 successful same-seed/hash replays.
- 9,141 applicability points: 9,068 evaluated and 73 explicitly excluded,
  across 302 parameter runs.
- 298 retained batch summaries.
- Four detectability repositories, five methods, 20 positive/20 negative
  samples at each of four strengths, and 120 audited numeric table cells with
  zero mismatches.

RQ2:

- 8 fresh random-initialization models, seed 42, 25 epochs, 4-bit payload.
- 32 method/dataset/channel rule-robustness cells.
- 9,444 post-transformation passes among 9,572 changed and syntax-valid MBXP
  programs (weighted EPR 98.66%).
- 1,000 LLM+RAG requests: 972 valid attacks, 23 no-ops, 5 syntax-invalid
  outputs, and no provider errors; returned snapshot `gpt-5-2025-08-07`.
- 45/45 post-pass programs in the independent LLM+RAG MBXP pilot.
- 10,000 sample-level paired bootstrap replicates per reported robustness cell.

## Source revisions

The RQ1 source was taken from `CodeWM_ProWES_Logits` commit
`1d4f0cbad7fb76a31684b615dfe4f880ca7ee176`. RQ2 was taken from the supplied
`RQ2_Final_Codex_Release` bundle dated 2026-09-16; its source archive manifest
is retained at `RQ2/source/SOURCE_MANIFEST.json`. Further provenance is in
`00_common/upstream_commits/METHODS.md`.
