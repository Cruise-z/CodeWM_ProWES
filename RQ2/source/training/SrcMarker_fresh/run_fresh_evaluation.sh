#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <srcmarker|codemark> <physical_gpu_id>" >&2
    exit 2
fi

method="$1"
physical_gpu_id="$2"
root_dir="$(cd "$(dirname "$0")" && pwd)"
revision_dir="$(cd "$root_dir/../.." && pwd)"
deps_dir="$revision_dir/.deps"
run_log_dir="$root_dir/run_logs"
result_dir="$revision_dir/outputs/fresh/base"
mkdir -p "$run_log_dir" "$result_dir"
cd "$root_dir"

datasets=(github_c_funcs github_java_funcs csn_js csn_java)
languages=(cpp java javascript java)

for index in "${!datasets[@]}"; do
    dataset="${datasets[$index]}"
    language="${languages[$index]}"
    checkpoint="ckpts/fresh_rq2_${method}_42_${dataset}/models_best.pt"
    output="$result_dir/${method}_${dataset}.jsonl"
    stdout_log="$run_log_dir/eval_${method}_${dataset}.stdout.log"

    if [[ ! -f "$checkpoint" ]]; then
        echo "checkpoint not found: $checkpoint" >&2
        exit 3
    fi
    if [[ -s "$output" ]]; then
        echo "SKIP_EVAL completed_output=$output"
        continue
    elif [[ -e "$output" ]]; then
        echo "refusing to overwrite incomplete evaluation output: $output" >&2
        exit 4
    fi

    echo "START_EVAL method=$method dataset=$dataset gpu=$physical_gpu_id utc=$(date -u +%FT%TZ)"
    start_seconds=$SECONDS
    CUDA_VISIBLE_DEVICES="$physical_gpu_id" \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="$deps_dir" \
    python eval_main.py \
        --method "$method" \
        --device cuda \
        --lang "$language" \
        --dataset "$dataset" \
        --dataset_dir "./datasets/$dataset" \
        --checkpoint_path "$checkpoint" \
        --n_bits 4 \
        --model_arch gru \
        --shared_encoder \
        --varmask_prob 0.5 \
        --seed 42 \
        --preprocess_workers 8 \
        --write_output \
        --output_path "$output" \
        >"$stdout_log" 2>&1
    elapsed_seconds=$((SECONDS - start_seconds))
    echo "DONE_EVAL method=$method dataset=$dataset gpu=$physical_gpu_id seconds=$elapsed_seconds utc=$(date -u +%FT%TZ)"
done
