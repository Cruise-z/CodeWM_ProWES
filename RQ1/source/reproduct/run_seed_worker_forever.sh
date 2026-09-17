#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
SHARD_COUNT="${CODEWM_SHARD_COUNT:-2}"
SHARD_INDEX="${CODEWM_SHARD_INDEX:?set CODEWM_SHARD_INDEX}"
MODEL_BASE_URL="${CODEWM_MODEL_BASE_URL:?set CODEWM_MODEL_BASE_URL}"
POLL_SECONDS="${CODEWM_POLL_SECONDS:-20}"
RESTART_DELAY_SECONDS="${CODEWM_RESTART_DELAY_SECONDS:-5}"
AUTO_REBUILD_STALE="${CODEWM_AUTO_REBUILD_STALE:-1}"
LOG_FILE="${CODEWM_WORKER_LOG_FILE:-$REPRODUCT_ROOT/logs/seed_worker_shard${SHARD_INDEX}.log}"

export CODEWM_MODEL_BASE_URL MODEL_BASE_URL PYTHONUNBUFFERED=1
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"
export no_proxy="127.0.0.1,localhost${no_proxy:+,$no_proxy}"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

printf '[supervisor] started_at=%s shard=%s/%s model=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SHARD_INDEX" "$SHARD_COUNT" "$MODEL_BASE_URL"

while true; do
    worker_args=(
        seed-worker
        --shard-count "$SHARD_COUNT"
        --shard-index "$SHARD_INDEX"
        --max-attempts-per-unit 0
        --poll-seconds "$POLL_SECONDS"
        --require-current-framework
    )
    if [[ "$AUTO_REBUILD_STALE" == "1" ]]; then
        worker_args+=(--auto-rebuild-stale)
    fi
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" "${worker_args[@]}"
    worker_rc=$?
    if [[ "$worker_rc" -eq 0 ]]; then
        exit 0
    fi
    printf '[supervisor] worker exited rc=%s; restarting in %ss\n' \
        "$worker_rc" "$RESTART_DELAY_SECONDS" >&2
    sleep "$RESTART_DELAY_SECONDS"
done
