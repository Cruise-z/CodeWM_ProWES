#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <srcmarker|codemark> <physical_gpu_id>" >&2
    exit 2
fi

method="$1"
physical_gpu_id="$2"
if [[ "$method" != "srcmarker" && "$method" != "codemark" ]]; then
    echo "unknown method: $method" >&2
    exit 2
fi

root_dir="$(cd "$(dirname "$0")" && pwd)"
deps_dir="$(cd "$root_dir/../.." && pwd)/.deps"
run_log_dir="$root_dir/run_logs"
mkdir -p "$run_log_dir"
cd "$root_dir"

datasets=(github_c_funcs github_java_funcs csn_js csn_java)
languages=(cpp java javascript java)

for index in "${!datasets[@]}"; do
    dataset="${datasets[$index]}"
    language="${languages[$index]}"
    checkpoint_dir="ckpts/fresh_rq2_${method}_42_${dataset}"
    stdout_log="$run_log_dir/${method}_${dataset}.stdout.log"

    if [[ -e "$checkpoint_dir" ]]; then
        echo "refusing to overwrite existing checkpoint directory: $checkpoint_dir" >&2
        exit 3
    fi

    echo "START method=$method dataset=$dataset gpu=$physical_gpu_id utc=$(date -u +%FT%TZ)"
    start_seconds=$SECONDS
    CUDA_VISIBLE_DEVICES="$physical_gpu_id" \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="$deps_dir" \
    python train_main.py \
        --method "$method" \
        --device cuda \
        --lang "$language" \
        --dataset "$dataset" \
        --dataset_dir "./datasets/$dataset" \
        --n_bits 4 \
        --epochs 25 \
        --log_prefix fresh_rq2 \
        --batch_size 64 \
        --model_arch gru \
        --shared_encoder \
        --varmask_prob 0.5 \
        --seed 42 \
        --preprocess_workers 8 \
        >"$stdout_log" 2>&1
    elapsed_seconds=$((SECONDS - start_seconds))
    echo "DONE method=$method dataset=$dataset gpu=$physical_gpu_id seconds=$elapsed_seconds utc=$(date -u +%FT%TZ)"
done
