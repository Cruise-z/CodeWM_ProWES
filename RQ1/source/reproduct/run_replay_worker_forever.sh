#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
SHARD_COUNT="${CODEWM_SHARD_COUNT:-2}"
SHARD_INDEX="${CODEWM_SHARD_INDEX:?set CODEWM_SHARD_INDEX}"
MODEL_BASE_URL="${CODEWM_MODEL_BASE_URL:?set CODEWM_MODEL_BASE_URL}"
POLL_SECONDS="${CODEWM_POLL_SECONDS:-20}"
RESTART_DELAY_SECONDS="${CODEWM_RESTART_DELAY_SECONDS:-5}"
LOG_FILE="${CODEWM_REPLAY_LOG_FILE:-$REPRODUCT_ROOT/logs/replay_worker_shard${SHARD_INDEX}.log}"

export CODEWM_MODEL_BASE_URL MODEL_BASE_URL PYTHONUNBUFFERED=1
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"
export no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

printf '[replay-supervisor] started_at=%s shard=%s/%s model=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SHARD_INDEX" "$SHARD_COUNT" "$MODEL_BASE_URL"

while true; do
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" replay-worker \
        --shard-count "$SHARD_COUNT" \
        --shard-index "$SHARD_INDEX" \
        --poll-seconds "$POLL_SECONDS"
    replay_rc=$?
    if [[ "$replay_rc" -eq 0 ]]; then
        exit 0
    fi
    if [[ "$replay_rc" -eq 3 ]]; then
        printf '[replay-supervisor] deterministic replay mismatch; stopping for investigation\n'
        exit 3
    fi
    printf '[replay-supervisor] worker exited rc=%s; restarting in %ss\n' \
        "$replay_rc" "$RESTART_DELAY_SECONDS"
    sleep "$RESTART_DELAY_SECONDS"
done
