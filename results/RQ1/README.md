# RQ1 results

This directory contains the two author-supplied RQ1 result bundles and their
expanded, reviewer-readable payloads.

## Applicability

`Applicability/` closes the released applicability path:

```text
batch summaries + point-level observations
  -> data/watermark_points.csv
  -> scripts/validate_dataset.py
  -> scripts/compute_statistics.py and scripts/plot_results.py
  -> paper_reproduction/tables/rq1 and paper_reproduction/figures/rq1
```

The master table contains 9,141 strength points from 302 parameter runs across
five projects, three languages, and six watermark methods. Of these, 9,068
have an experimental outcome and 73 remain explicitly marked `Excluded`.

## Detectability

`Detectability/` closes the released detectability path:

```text
four original execution logs
  -> scripts/build_detectability_table.py
  -> per-strength AUROC, pooled AUROC, and FNR@5% FPR
  -> tables/table_per_strength_auroc.tex
```

The logs cover four repositories and five detector-bearing methods, with 20
positive and 20 negative samples at each of four positive strengths. The
released audit checks 120 reported numeric cells with zero mismatches.

## Reproduce and verify

From the repository root:

```bash
python3 tools/verify_rq1_evidence.py
./paper_reproduction/reproduce_rq1.sh
```

The original archives are retained as `Applicability.zip` and
`Detectability.zip`. Their immutable outer digests and the one integration
repair made to the expanded Applicability checksum ledger are documented in
`ARCHIVE_PROVENANCE.json`.

## Scope boundary

The Applicability bundle contains the final point-level table and 298 retained
batch summaries. It does not contain the 9,141 referenced Docker
`evaluation.log` files or repository snapshots. The point labels are therefore
auditable against the released aggregate summaries, but individual Docker
runs cannot be replayed from this bundle alone. The Detectability bundle
contains aggregate execution logs rather than per-sample detector-score CSVs;
score-level bootstrapping cannot be independently rerun. These limitations are
preserved here instead of being filled with synthetic evidence.
