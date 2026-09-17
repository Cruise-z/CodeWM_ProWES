#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
RETRY_SECONDS="${CODEWM_P09_REBUILD_RETRY_SECONDS:-20}"

export PYTHONUNBUFFERED=1
export CODEWM_ARCHITECTURE_REBUILD_REASON="epoch8_attempts2_3_5_prefix_checksum_mismatch_attempts4_6_invalid_default_package_imports_attempt1_private_min_size_access"
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"

while true; do
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
        --unit p09_qr_code_gen_det_java --force
    rebuild_rc=$?
    if [[ "$rebuild_rc" -eq 0 ]]; then
        break
    fi
    printf '[p09-rebuild] retry rc=%s after=%ss\n' "$rebuild_rc" "$RETRY_SECONDS"
    sleep "$RETRY_SECONDS"
done

export CODEWM_SHARD_COUNT=2
export CODEWM_SHARD_INDEX=1
export CODEWM_MODEL_BASE_URL=http://127.0.0.1:8001
export CODEWM_AUTO_REBUILD_STALE=1
exec "$REPRODUCT_ROOT/run_seed_worker_forever.sh"
