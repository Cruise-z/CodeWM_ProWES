#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_PORT="${CODEWM_MODEL_PORT:-8000}"
RESTART_DELAY_SECONDS="${CODEWM_MODEL_RESTART_DELAY_SECONDS:-10}"
LOG_FILE="${CODEWM_MODEL_LOG_FILE:-$REPRODUCT_ROOT/logs/model_server_${MODEL_PORT}.log}"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

while true; do
    printf '[model-supervisor] starting_at=%s port=%s cuda_visible_devices=%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODEL_PORT" "${CUDA_VISIBLE_DEVICES:-unset}"
    CODEWM_MODEL_PORT="$MODEL_PORT" "$REPRODUCT_ROOT/run_model_server.sh"
    model_rc=$?
    printf '[model-supervisor] exited_at=%s rc=%s; restarting in %ss\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$model_rc" "$RESTART_DELAY_SECONDS"
    sleep "$RESTART_DELAY_SECONDS"
done
