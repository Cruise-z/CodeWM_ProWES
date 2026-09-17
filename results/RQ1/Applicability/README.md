# Project-Level Watermark Detection Artifact

This package contains the final point-level dataset and the scripts needed to validate it, derive tables, regenerate figures, and reconstruct the dataset from the raw experiment directories. Derived tables, figures, build trees, `DTResults` directories, and evaluation products are intentionally not included.

## Package contents

```text
data/watermark_points.csv          Final master table; the only result-data file
scripts/validate_dataset.py        Integrity and schema checks
scripts/compute_statistics.py      Derived tables and pooled statistics
scripts/plot_results.py            Eighteen method-by-language figures
scripts/extract_detection_results.py  Reconstruction from raw experiment directories
metadata.json                      Version, counts, schema, and provenance
requirements.txt                   Optional plotting dependency
SHA256SUMS                         File-integrity checksums
```

## Dataset scope

- Projects: `brick_breaker`, `caro`, `flappy_bird`, `snake`, and `tank_battle`.
- Languages: C++, Java, and Python.
- Watermark methods: CodeIP, EWD, STONE, SWEET, Waterfall, and WLLM.
- One row represents one strength directory for which a direct child named `DTResults` exists.
- The master table has 9,141 embedded-response points from 302 parameter runs.
- The analysis denominator contains 9,068 classified outcomes. The remaining 73 rows are retained as `Excluded` for auditability.

Use `category`, not `log_category`, for reported statistics and figures. `category` is the batch-summary-aligned final label. The outcome order is always `Pass`, `BE`, `TE`, `RE`.

## Outcome definitions

- `Pass`: the generated project follows the interface protocol, completes the build and protocol-level tests, and starts normally in the short post-build execution check.
- `BE` (Build Error): the project fails during compilation, configuration, dependency resolution, packaging, or artifact construction before required protocol-level tests complete successfully.
- `TE` (Test Error): the project builds sufficiently to run the protocol-level automated test module but fails one or more required tests.
- `RE` (Runtime Error): the project passes build and protocol-level tests but crashes, exits abnormally, or fails during the short post-build execution check.
- `Excluded`: a `DTResults` point that is outside an available batch-summary total or belongs to a configuration without a batch summary. It is not an outcome category and is excluded from pass-rate denominators.

## Master-table columns

| Column | Meaning |
| --- | --- |
| `watermark_method` | Watermark method identifier. |
| `project` | Project repository identifier. |
| `language` | Implementation language: `cpp`, `java`, or `python`. |
| `seed_group` | Optional numeric grouping directory below `results`; blank when absent. |
| `method_config` | Full parameter-run directory name, including `rngS`. |
| `strength` | Watermark strength for the embedded response point. |
| `log_category` | Category inferred directly from the selected `evaluation.log`, before aggregate calibration. |
| `category` | Final analysis category aligned with the matching batch summary. |
| `classification_source` | Provenance of the final point label. |
| `embedded` | Always `yes`; only directories containing `DTResults` are included. |
| `evaluation_log` | Path relative to the raw workspace for the selected `evaluation.log`. |

`classification_source` has four values:

- `log_and_batch_summary`: the log-derived label already matches the batch-summary allocation.
- `batch_summary_calibrated`: the point label was reassigned so the parameter-run totals exactly match the batch summary.
- `excluded_by_batch_summary`: the response point exceeds the batch-summary outcome total.
- `no_batch_summary`: no matching batch summary was available.

The 212 `batch_summary_calibrated` labels are constrained by configuration-level totals. Their aggregate counts are reliable, but when several individual assignments satisfy the same totals, the batch summary cannot uniquely identify which specific strength produced each outcome. Point-level analyses should disclose this limitation.

## Validate the release

Python 3.9 or later is required. Validation uses only the standard library.

```bash
python3 scripts/validate_dataset.py
sha256sum -c SHA256SUMS
```

## Generate derived tables

The package stores no redundant summary CSV files. Generate them from the master table when needed:

```bash
python3 scripts/compute_statistics.py --output derived/tables
```

This creates:

- method-project-language, method-project, and method-level pooled summaries;
- one summary row per parameter run;
- the project-language RNG seed inventory;
- classification-provenance counts.

Each pooled summary reports both point-pooled and run-balanced pass rates. Point-pooled metrics give every response point equal weight. Run-balanced metrics first calculate each language/seed/parameter run and then average the runs, preventing long strength sweeps from dominating short sweeps.

## Generate figures

Install the optional dependency in the intended environment and generate six methods by three languages, for 18 figures total:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/plot_results.py --format pdf --output derived/figures
```

With the experiment environment used for this study:

```bash
conda run -n Code_Watermark python scripts/plot_results.py --format pdf --output derived/figures
```

Repeated parameter runs are separated horizontally inside each project position. The legend follows `Pass`, `BE`, `TE`, `RE`; excluded rows are not plotted.

## Reconstruct the master table

The raw workspace must contain the five project directories. The extractor visits only method configuration directories below each `<project>/<project>_<language>/results` directory and their immediate strength subdirectories; it does not recursively scan the complete repository.

```bash
python3 scripts/extract_detection_results.py \
  --workspace /path/to/project_level \
  --output /tmp/watermark_points.csv
```

For each parameter run, the extractor parses the newest `DTResults/*/evaluation.log`, reads the matching `*summary*.json`, and applies a deterministic maximum-score assignment so final category counts equal the external batch summary.
