# Artifact completion audit

Status meanings: **present** is released and checksummed; **partial** is useful
but does not fully satisfy the paper claim; **missing** was not found in the
three supplied inputs and was not fabricated.

| Evidence item | Status | Location / action |
|---|---|---|
| Root instructions and evidence map | Present | `README.md`, `ARTIFACT_MANIFEST.*` |
| Exact source revisions | Present | `00_common/upstream_commits/METHODS.md` |
| Software/hardware records | Present | `00_common/environment/`, `00_common/hardware/` |
| Root project license | Missing | Choose an umbrella license before public release; third-party notices are retained. |
| RQ1 14-task specification | Present | `RQ1/01_task_specs/manifest.json` |
| RQ1 prompt templates and 42 rendered Stage-0 prompts | Present | `RQ1/02_prompts/`, `RQ1/03_architecture_checkpoints/` |
| RQ1 42 serialized architecture checkpoints | Present | Each unit has `architecture/team/team.json` and provenance evidence. |
| RQ1 current initial repositories | Present | Beside each architecture checkpoint. |
| RQ1 frozen generator/framework/evaluator | Present | `RQ1/source/`, `RQ1/04_docker/` |
| RQ1 baseline attempts, accepted repositories, replay logs | Present | `results/RQ1/05_baseline_qualification/` contains 88 attempts, 42 accepted snapshots, 42 verified replays, worker/evaluator logs, hashes, and reviewer indexes. |
| RQ1 applicability observations | Partial | `results/RQ1/Applicability/` has 9,141 point rows and 298 aggregate batch summaries, but not the referenced per-point Docker logs or repository snapshots. |
| RQ1 detectability observations | Partial | `results/RQ1/Detectability/` has four aggregate raw logs and audited values, but not per-sample detector-score CSVs. |
| RQ1 supplied-result reproduction | Present | `paper_reproduction/reproduce_rq1.sh` verifies the baseline plus both archives and regenerates three baseline ledgers, six applicability tables, 18 figures, and three detectability outputs. |
| RQ1 complete main-paper table reproduction | Partial | The archives cover the supplied medium-project applicability and aggregate detectability outputs; small-project rows and all paper bootstrap/sensitivity intermediates were not supplied. |
| RQ2 GitHub/MBXP splits and stable LLM cohort | Present | `results/RQ2/01_datasets/`, `results/RQ2/05_llm_rag/cohort/` |
| RQ2 CSN train/validation source files | Missing | Upstream download/preprocessing instructions are in the SrcMarker README; test observations and UIDs are present. |
| RQ2 fresh training configs/history/logs | Present | `results/RQ2/02_training/` |
| RQ2 exact best checkpoints | Present (Git LFS) | Eight `models_best.pt` files plus SHA-256 identities. |
| RQ2 clean per-sample predictions | Present | `results/RQ2/02_training/clean_predictions/` |
| RQ2 32 rule attack/evaluation cells | Present | `results/RQ2/03_rule_attacks/` |
| RQ2 full MBXP validity matrix | Present | `results/RQ2/04_mbxp_validation/` |
| RQ2 LLM cohort, rule base, prompts, calls and responses | Present | `RQ2/source/rq2_revision/`, `results/RQ2/05_llm_rag/` |
| RQ2 45-program LLM MBXP pilot | Present | `results/RQ2/06_llm_rag_mbxp_pilot/epr/` |
| RQ2 predictions/statistics/bootstrap/table/figures | Present | `results/RQ2/`, `RQ2/source/`, `paper_reproduction/` |
| RQ3 timing implementation hooks | Partial | `RQ3/01_timing_harness/README.md` points to retained code. |
| RQ3 raw timings/token counts/repetition statistics | Missing | Must be supplied before claiming reproducibility of main-paper Table X. |

Before public release, run:

```bash
python tools/verify_rq1_evidence.py
python tools/verify_rq2_evidence.py
./paper_reproduction/reproduce_all.sh
python tools/check_release_language.py
python tools/artifact_manifest.py --write
python tools/artifact_manifest.py --verify
git lfs ls-files
```

The missing/partial rows above are the remaining evidence-chain gaps. The
artifact intentionally does not infer per-run records from aggregates or
reconstruct absent RQ3 timings from paper point estimates.
