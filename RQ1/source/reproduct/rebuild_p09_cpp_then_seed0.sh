#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
RETRY_SECONDS="${CODEWM_P09_CPP_REBUILD_RETRY_SECONDS:-20}"

export PYTHONUNBUFFERED=1
export CODEWM_ARCHITECTURE_REBUILD_REASON="epoch5_attempts1_2_3_header_self_containment_attempt4_finder_layout_mismatch"
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"

while true; do
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
        --unit p09_qr_code_gen_det_cpp --force
    rebuild_rc=$?
    if [[ "$rebuild_rc" -eq 0 ]]; then
        break
    fi
    printf '[p09-cpp-rebuild] retry rc=%s after=%ss\n' "$rebuild_rc" "$RETRY_SECONDS"
    sleep "$RETRY_SECONDS"
done

export CODEWM_SHARD_COUNT=2
export CODEWM_SHARD_INDEX=0
export CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000
export CODEWM_AUTO_REBUILD_STALE=1
exec "$REPRODUCT_ROOT/run_seed_worker_forever.sh"
