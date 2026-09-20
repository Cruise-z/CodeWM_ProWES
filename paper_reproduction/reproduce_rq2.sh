#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export SOURCE_DATE_EPOCH=1789538134
python "$ROOT/tools/verify_rq2_evidence.py" --output "$ROOT/paper_reproduction/tables/RQ2/rq2_evidence_check.json"
python "$ROOT/paper_reproduction/reproduce_rq2.py"
