#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
: "${PYTHON_BIN:=python}"
exec "$PYTHON_BIN" batchCodeGenDT.py "$@"
