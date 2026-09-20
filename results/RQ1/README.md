# RQ1 final results

This directory exposes one final result tree for each released RQ1 stage:

```text
results/RQ1/
├── 05_baseline_qualification/
├── 07_strength_sweep/
└── 08_detectability/
```

## Baseline qualification

`05_baseline_qualification/` closes the released baseline path:

```text
42 architecture checkpoints
  -> 88 formal generation attempts and evaluator logs
  -> 42 accepted seeds and repository snapshots
  -> 42 same-seed replays
  -> canonical repository hashes and final campaign audit
```

The failed attempts among the 88 rows are retained because baseline
qualification is part of the final experimental protocol. Pre-final campaign
epochs, interrupted migrations, and recovery utilities are not included.

## Strength sweep

`07_strength_sweep/` contains the final 9,141-point table, 298 batch summaries,
validation script, statistics script, and plotting script. Of the 9,141 rows,
9,068 have an experimental outcome and 73 are explicitly `Excluded`.

## Detectability

`08_detectability/` contains the four released execution logs and the final
per-strength AUROC, pooled AUROC, and FNR@5% FPR derivation. Its verification
checks 120 numeric table cells with zero mismatches.

## Reproduce and verify

From the repository root:

```bash
python3 tools/verify_rq1_evidence.py
./paper_reproduction/reproduce_rq1.sh
```

The expanded result trees are authoritative. Redundant source archives and
superseded calculation packages are intentionally omitted.

## Scope boundary

The baseline qualification chain is complete. The strength-sweep evidence does
not contain the referenced per-point Docker logs or repository snapshots, and
the detectability evidence contains aggregate logs rather than per-sample
detector-score CSVs. These known boundaries are not filled with inferred data.
