#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
SHARD_COUNT="${CODEWM_ARCH_SHARD_COUNT:-2}"
SHARD_INDEX="${CODEWM_ARCH_SHARD_INDEX:?set CODEWM_ARCH_SHARD_INDEX}"
RESTART_DELAY_SECONDS="${CODEWM_ARCH_RESTART_DELAY_SECONDS:-30}"
LOG_FILE="${CODEWM_ARCH_LOG_FILE:-$REPRODUCT_ROOT/logs/architecture_worker_shard${SHARD_INDEX}.log}"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

printf '[architecture-supervisor] started_at=%s shard=%s/%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SHARD_INDEX" "$SHARD_COUNT"

while true; do
    "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
        --all \
        --force \
        --skip-accepted \
        --stale-inputs \
        --shard-count "$SHARD_COUNT" \
        --shard-index "$SHARD_INDEX"
    architecture_rc=$?
    if [[ "$architecture_rc" -eq 0 ]]; then
        printf '[architecture-supervisor] shard complete at %s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        exit 0
    fi
    printf '[architecture-supervisor] pass exited rc=%s; retrying incomplete units in %ss\n' \
        "$architecture_rc" "$RESTART_DELAY_SECONDS"
    sleep "$RESTART_DELAY_SECONDS"
done
