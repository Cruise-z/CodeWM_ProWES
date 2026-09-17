# Detectability

Reproducibility artifact for the per-strength watermark detectability table.

## Structure

```text
Detectability/
├── raw_logs/                 # Original supplied execution logs (unchanged)
├── scripts/
│   └── build_detectability_table.py
├── derived/
│   ├── all_metrics_long.csv
│   ├── detectability_values.csv
│   └── audit_summary.json
├── tables/
│   └── table_per_strength_auroc.tex
├── audit/
│   ├── AUDIT_REPORT.md
│   ├── reference_table_values.csv
│   ├── table_verification.json
│   ├── reproduction_stdout.txt
│   └── reproduction_stderr.txt
├── MANIFEST.json
└── SHA256SUMS.txt
```

## Reproduce

Requires Python 3 only; no third-party packages.

```bash
cd Detectability
python scripts/build_detectability_table.py
```

The script parses the original logs, validates repository/method coverage and
sample counts, checks pooled/per-strength AUROC consistency, computes FNR5, and
regenerates the CSV and LaTeX table.

## Integrity

Run:

```bash
sha256sum -c SHA256SUMS.txt
```

The outer archive checksum is distributed separately as `Detectability.zip.sha256`.
