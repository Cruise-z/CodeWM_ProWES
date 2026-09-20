# RQ2 — robustness

`source/` is the exact curated source artifact from the 2026-09-16 final RQ2
release. The numbered directories are reviewer-oriented indexes; formal data
and observations are under `../results/RQ2/`.

| Stage | Implementation | Released evidence |
|---|---|---|
| Dataset/split/cohort | `source/training/SrcMarker_fresh/`, `source/prepare_fresh_llm_cohorts.py` | `results/RQ2/01_datasets/`, `results/RQ2/05_llm_rag/cohort/` |
| Fresh SrcMarker/CodeMark training | `source/training/SrcMarker_fresh/` | checkpoints, manifests, 25-epoch histories, clean predictions, logs |
| Rule attack | `source/pipeline/rule_attack.py`, `source/cStyleLang/` | 32 raw/evaluated JSONL cells |
| MBXP execution | `source/project/srcMarker/SrcMarker/validate_mbxp_rq2.py` | 12 complete per-sample matrices and summaries |
| LLM+RAG | `source/pipeline/`, `source/run_llm_full_1000.py` | fixed prompts/rules, cohort, 1,000 responses, usage, validity, predictions |
| LLM MBXP pilot | same implementation and validator | 45 per-sample execution records |
| Statistics | `source/project/srcMarker/SrcMarker/3_analysis.py`, builders | paired predictions, 10,000-bootstrap summaries, CSV/LaTeX/figures |

Run `python tools/verify_rq2_evidence.py` from the repository root for a fast,
streaming consistency audit, then `paper_reproduction/reproduce_rq2.sh` to
regenerate the paper-facing tables and figures.
