#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
"$ROOT/paper_reproduction/reproduce_rq1.sh"
"$ROOT/paper_reproduction/reproduce_rq2.sh"
"$ROOT/paper_reproduction/reproduce_rq3.sh"
