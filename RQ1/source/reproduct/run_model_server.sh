#!/usr/bin/env bash
set -euo pipefail

REPRODUCT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_RUNTIME="$REPRODUCT_ROOT/model_runtime/modelDeployer"
MODEL_PYTHON="${CODEWM_MODEL_PYTHON:-/home/zhaorz/software/anaconda3/envs/Code_Watermark/bin/python}"
MODEL_PORT="${CODEWM_MODEL_PORT:-8000}"

: "${GPU_MAX_MEMORY:=74GiB}"
: "${SERVER_DO_SAMPLE:=1}"
: "${SAMPLING_MODE:=lenient_openai}"
: "${RNG_SEED_FALLBACK:=none}"
: "${ALLOW_GENERATOR_FALLBACK:=1}"
: "${DETERMINISTIC:=0}"
: "${LOG_REQ_BODY:=0}"

export GPU_MAX_MEMORY SERVER_DO_SAMPLE SAMPLING_MODE
export RNG_SEED_FALLBACK ALLOW_GENERATOR_FALLBACK DETERMINISTIC LOG_REQ_BODY

cd "$MODEL_RUNTIME"
exec "$MODEL_PYTHON" -m uvicorn server:app --host 127.0.0.1 --port "$MODEL_PORT"
