#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
"$ROOT/paper_reproduction/reproduce_rq1.sh"
"$ROOT/paper_reproduction/reproduce_rq2.sh"
if find "$ROOT/RQ3/02_raw_timings" "$ROOT/RQ3/04_token_counts" -type f ! -name '.gitkeep' -print -quit | grep -q .; then
  "$ROOT/paper_reproduction/reproduce_rq3.sh"
else
  echo "SKIP RQ3: raw timing/token-count records are unavailable."
fi
