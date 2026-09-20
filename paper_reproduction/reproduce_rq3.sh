#!/usr/bin/env bash
set -euo pipefail
artifact_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$artifact_root/RQ3/05_analysis/reproduce_table_x.py" \
  --artifact-root "$artifact_root" \
  --output-dir "$artifact_root/paper_reproduction/tables/RQ3"
