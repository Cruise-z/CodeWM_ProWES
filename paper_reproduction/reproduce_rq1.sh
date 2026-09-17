#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BASE="$ROOT/results/RQ1/05_baseline_qualification"
APP="$ROOT/results/RQ1/Applicability"
DET="$ROOT/results/RQ1/Detectability"
TABLES="$ROOT/paper_reproduction/tables/rq1"
FIGURES="$ROOT/paper_reproduction/figures/rq1"
WORK=$(mktemp -d /tmp/prowes-rq1-reproduction-XXXXXX)

if [[ ! -d "$BASE" || ! -d "$APP" || ! -d "$DET" ]]; then
  echo "RQ1 evidence is missing; expected baseline qualification," \
    "Applicability, and Detectability." >&2
  exit 2
fi

mkdir -p \
  "$TABLES/baseline" \
  "$TABLES/applicability" \
  "$TABLES/detectability" \
  "$FIGURES/applicability"
mkdir -p "$WORK/matplotlib" "$WORK/cache"

python3 "$ROOT/tools/verify_rq1_evidence.py"
python3 "$ROOT/tools/build_rq1_baseline_ledgers.py" \
  --evidence-root "$BASE" \
  --output "$WORK/baseline"
for ledger in attempt_ledger.csv accepted_ledger.csv replay_ledger.csv; do
  cmp "$WORK/baseline/$ledger" "$BASE/indexes/$ledger"
  cp "$WORK/baseline/$ledger" "$TABLES/baseline/$ledger"
done
python3 "$APP/scripts/compute_statistics.py" \
  --input "$APP/data/watermark_points.csv" \
  --output "$WORK/applicability_tables"

export MPLCONFIGDIR="$WORK/matplotlib"
export XDG_CACHE_HOME="$WORK/cache"
export SOURCE_DATE_EPOCH=1789538134
python3 "$APP/scripts/plot_results.py" \
  --input "$APP/data/watermark_points.csv" \
  --format pdf \
  --output "$WORK/applicability_figures"

cp "$WORK/applicability_tables"/*.csv "$TABLES/applicability/"
cp "$WORK/applicability_figures"/*.pdf "$FIGURES/applicability/"

cp -a "$DET" "$WORK/Detectability"
python3 "$WORK/Detectability/scripts/build_detectability_table.py" >/dev/null
cmp "$WORK/Detectability/derived/detectability_values.csv" \
  "$DET/derived/detectability_values.csv"
cmp "$WORK/Detectability/tables/table_per_strength_auroc.tex" \
  "$DET/tables/table_per_strength_auroc.tex"
cp "$WORK/Detectability/derived/all_metrics_long.csv" "$TABLES/detectability/"
cp "$WORK/Detectability/derived/detectability_values.csv" "$TABLES/detectability/"
cp "$WORK/Detectability/tables/table_per_strength_auroc.tex" "$TABLES/detectability/"

printf 'RQ1 reproduction complete: 3 baseline ledgers, 6 applicability tables, 18 applicability figures, and 3 detectability outputs.\n'
