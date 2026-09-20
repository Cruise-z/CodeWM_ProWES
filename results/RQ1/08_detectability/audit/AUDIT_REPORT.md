# Detectability Data Audit

## Verdict

PASS for the requested LaTeX table.

The four supplied logs contain 20 complete repository-method evaluation blocks:
4 representative repositories x 5 detector-bearing watermarking methods.
Every block contains the four requested positive strengths (0.5, 1.0, 2.0, 3.0),
20 positive and 20 negative samples per strength, and a pooled result with
80 positives and 20 negatives.

The requested 20-row LaTeX table is fully reconstructible from the logs.
A cell-by-cell comparison against the user-supplied LaTeX values checks 120
numeric cells and reports PASS with zero mismatches.

## Derived quantities

- AUROC at each strength: read directly from the corresponding per-strength log block.
- Pool: read from the logged overall pooled AUROC.
- FNR5: computed as `1 - pooled TPR@FPR=5%`.
- Display values: percentages rounded with ROUND_HALF_UP to two decimals.

Because each positive-strength group has the same Npos=20 and is compared with
the same-sized Nneg=20 baseline set, the logged pooled AUROC is also exactly
equal to the arithmetic mean of the four per-strength AUROCs in all 20 runs.
This identity is checked automatically by the reproduction script.

## Statistical audit notes

1. AUROC and TPR values are all within [0,1].
2. Sample counts are internally consistent: 4 x 20 = 80 pooled positives.
3. No monotonicity is artificially assumed. Several methods exhibit non-monotonic
   strength behavior in some repositories; these values are retained exactly as logged.
4. With only Nneg=20 negatives, empirical FPR resolution is 1/20 = 5 percentage
   points. Therefore FPR=5% corresponds to one false positive and is directly
   interpretable. Targets below 5% are necessarily coarse/discrete; they are not
   used in the requested table.
5. This artifact reproduces reported point estimates from logs. It does not
   reconstruct detector scores because the original per-sample CSV files referenced
   in the logs were not supplied here. Consequently, score-level re-estimation or
   bootstrap confidence intervals cannot be independently recomputed from these
   four text logs alone.

## Reproduction

From the artifact root:

```bash
python scripts/build_detectability_table.py
```

This regenerates:
- `derived/detectability_values.csv`
- `derived/all_metrics_long.csv`
- `derived/audit_summary.json`
- `tables/table_per_strength_auroc.tex`

