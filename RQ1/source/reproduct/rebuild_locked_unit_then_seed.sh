#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
UNIT_ID="${CODEWM_REBUILD_UNIT:?set CODEWM_REBUILD_UNIT}"
SHARD_COUNT="${CODEWM_SHARD_COUNT:-2}"
SHARD_INDEX="${CODEWM_SHARD_INDEX:?set CODEWM_SHARD_INDEX}"
MODEL_BASE_URL="${CODEWM_MODEL_BASE_URL:?set CODEWM_MODEL_BASE_URL}"
RETRY_DELAY_SECONDS="${CODEWM_ARCH_RESTART_DELAY_SECONDS:-30}"
LOG_FILE="${CODEWM_REBUILD_LOG_FILE:-$REPRODUCT_ROOT/logs/rebuild_${UNIT_ID}.log}"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"
export no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

while true; do
    printf '[rebuild] starting_at=%s unit=%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$UNIT_ID"
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
        --unit "$UNIT_ID" \
        --force
    rebuild_rc=$?
    if [[ "$rebuild_rc" -eq 0 ]]; then
        break
    fi
    printf '[rebuild] failed rc=%s; retrying in %ss\n' \
        "$rebuild_rc" "$RETRY_DELAY_SECONDS"
    sleep "$RETRY_DELAY_SECONDS"
done

printf '[rebuild] complete_at=%s; resuming seed shard=%s/%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SHARD_INDEX" "$SHARD_COUNT"
exec env \
    CODEWM_MODEL_BASE_URL="$MODEL_BASE_URL" \
    CODEWM_SHARD_INDEX="$SHARD_INDEX" \
    CODEWM_SHARD_COUNT="$SHARD_COUNT" \
    "$REPRODUCT_ROOT/run_seed_worker_forever.sh"
