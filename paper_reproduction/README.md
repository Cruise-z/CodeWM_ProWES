# Paper reproduction

This directory contains the final paper-output entry points. Each output type
is partitioned by research question:

```text
paper_reproduction/
├── figures/
│   ├── RQ1/
│   ├── RQ2/
│   └── RQ3/
└── tables/
    ├── RQ1/
    ├── RQ2/
    └── RQ3/
```

- `reproduce_rq1.sh` verifies the 88/42/42 baseline ledger and regenerates the
  final applicability and detectability outputs under `tables/RQ1/` and
  `figures/RQ1/`.
- `reproduce_rq2.sh` verifies the formal per-sample evidence and regenerates
  the final robustness tables and figures under `tables/RQ2/` and
  `figures/RQ2/`.
- `reproduce_rq3.sh` verifies the released timing records and regenerates
  Table X under `tables/RQ3/`. RQ3 has no paper figure, which is recorded in
  `figures/RQ3/README.md`.
- `reproduce_all.sh` runs all three final reproduction stages.

All committed files in these output directories are generated from the final
released observations.
