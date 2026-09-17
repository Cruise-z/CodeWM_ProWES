#!/usr/bin/env bash
set -uo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN_PYTHON="${CODEWM_CAMPAIGN_PYTHON:-/home/zhaorz/software/anaconda3/envs/myMetagpt/bin/python}"
EXPECTED_API_BASE_URL="${CODEWM_EXPECTED_ARCHITECTURE_BASE_URL:-https://api.chatanywhere.tech/v1}"
EXPECTED_API_MODEL="${CODEWM_EXPECTED_ARCHITECTURE_MODEL:-gpt-5}"
RETRY_SECONDS="${CODEWM_API_REBUILD_RETRY_SECONDS:-20}"
LOG_FILE="${CODEWM_API_REBUILD_LOG_FILE:-$REPRODUCT_ROOT/logs/api_rebuild_queue.log}"
LOCK_FILE="$REPRODUCT_ROOT/worker_state/api_rebuild_queue.lock"

units=(
    p06_tank_battle_game_java
    p06_tank_battle_game_python
    p07_calculator_cpp
    p07_calculator_java
    p07_calculator_python
    p08_excel_data_processing_java
    p08_excel_data_processing_python
    p09_qr_code_gen_det_cpp
    p09_qr_code_gen_det_java
    p09_qr_code_gen_det_python
    p10_crud_system_cpp
    p10_crud_system_python
)

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    printf '[api-rebuild] another queue already holds %s\n' "$LOCK_FILE"
    exit 0
fi
exec >>"$LOG_FILE" 2>&1

export PYTHONUNBUFFERED=1
export CODEWM_ARCHITECTURE_REBUILD_REASON="replace_local_architecture_with_remote_api_after_refill"
export PYTHONPATH="$REPRODUCT_ROOT/framework:$REPRODUCT_ROOT/tools:$REPRODUCT_ROOT/../DT/codeGen${PYTHONPATH:+:$PYTHONPATH}"

printf '[api-rebuild] started_at=%s expected_base=%s expected_model=%s units=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$EXPECTED_API_BASE_URL" \
    "$EXPECTED_API_MODEL" "${#units[@]}"

for unit_id in "${units[@]}"; do
    evidence_path="$REPRODUCT_ROOT/units/${unit_id%_*}/${unit_id##*_}/architecture/evidence.json"
    project_language="${unit_id##*_}"
    project_stem="${unit_id%_${project_language}}"
    evidence_path="$REPRODUCT_ROOT/units/$project_stem/$project_language/architecture/evidence.json"

    while true; do
        if [[ -f "$evidence_path" ]] && jq -e \
            --arg base "$EXPECTED_API_BASE_URL" \
            --arg model "$EXPECTED_API_MODEL" \
            '.valid == true and .architecture_model.base_url == $base and .architecture_model.model == $model' \
            "$evidence_path" >/dev/null; then
            printf '[api-rebuild] already_valid unit=%s at=%s\n' \
                "$unit_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            break
        fi

        printf '[api-rebuild] rebuilding unit=%s at=%s\n' \
            "$unit_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        "$CAMPAIGN_PYTHON" "$REPRODUCT_ROOT/campaign.py" architecture \
            --unit "$unit_id" --force --replace-accepted
        rebuild_rc=$?
        if [[ "$rebuild_rc" -ne 0 ]]; then
            printf '[api-rebuild] retry unit=%s rc=%s after=%ss\n' \
                "$unit_id" "$rebuild_rc" "$RETRY_SECONDS"
            sleep "$RETRY_SECONDS"
            continue
        fi
    done
done

printf '[api-rebuild] complete_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
