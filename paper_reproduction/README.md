# Paper reproduction entry points

- `reproduce_rq1.sh` verifies the supplied applicability and detectability
  bundles and regenerates six applicability tables, 18 figures, and three
  detectability outputs.
- `reproduce_rq2.sh` verifies the formal per-sample evidence and regenerates
  the RQ2 paper-facing CSV/LaTeX tables and PNG/PDF figures.
- `reproduce_rq3.sh` is a guard until raw timing evidence is recovered.
- `reproduce_all.sh` runs every currently available reproduction stage and
  reports intentional skips.

Generated files are written to `tables/` and `figures/`. RQ2 outputs can be
compared with the frozen formal copies in
`../results/RQ2/08_statistics/paper_outputs/03_tables_figures/`; the RQ1
detectability wrapper performs its frozen-output comparison automatically.
