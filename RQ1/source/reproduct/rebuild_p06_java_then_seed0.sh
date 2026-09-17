#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
RETRY_SECONDS="${CODEWM_P06_REBUILD_RETRY_SECONDS:-20}"

export PYTHONUNBUFFERED=1
export CODEWM_ARCHITECTURE_REBUILD_REASON="epoch10_attempts1_5_reused_same_tank_copy_across_current_and_initial_maps"
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"

while true; do
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
        --unit p06_tank_battle_game_java --force
    rebuild_rc=$?
    if [[ "$rebuild_rc" -eq 0 ]]; then
        break
    fi
    printf '[p06-rebuild] retry rc=%s after=%ss\n' "$rebuild_rc" "$RETRY_SECONDS"
    sleep "$RETRY_SECONDS"
done

export CODEWM_SHARD_COUNT=2
export CODEWM_SHARD_INDEX=0
export CODEWM_MODEL_BASE_URL=http://127.0.0.1:8000
export CODEWM_AUTO_REBUILD_STALE=1
exec "$REPRODUCT_ROOT/run_seed_worker_forever.sh"
