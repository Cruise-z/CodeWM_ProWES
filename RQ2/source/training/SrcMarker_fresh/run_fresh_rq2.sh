#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <srcmarker|codemark> <physical_gpu_id>" >&2
    exit 2
fi

method="$1"
physical_gpu_id="$2"
srcmarker_root="$(cd "$(dirname "$0")" && pwd)"
artifact_root="$(cd "$srcmarker_root/../.." && pwd)"
deps_dir="$artifact_root/.deps"
driver="$artifact_root/project/srcMarker/SrcMarker/1_obfus.py"
detector="$artifact_root/project/srcMarker/SrcMarker/run_watermark_detector_portable.py"
analysis="$artifact_root/project/srcMarker/SrcMarker/3_analysis.py"
parser_lib="$srcmarker_root/parser/languages.so"
fresh_root="$artifact_root/outputs/fresh"
log_root="$srcmarker_root/run_logs"
mkdir -p "$fresh_root/rule" "$fresh_root/rule_eval" "$fresh_root/metrics" "$log_root"

datasets=(github_c_funcs github_java_funcs csn_js csn_java)
languages=(cpp java javascript java)
channels=(id expr block all)

for index in "${!datasets[@]}"; do
    dataset="${datasets[$index]}"
    language="${languages[$index]}"
    base="$fresh_root/base/${method}_${dataset}.jsonl"
    checkpoint="$srcmarker_root/ckpts/fresh_rq2_${method}_42_${dataset}/models_best.pt"

    completed_metrics=0
    for channel in "${channels[@]}"; do
        if [[ -s "$fresh_root/metrics/${method}_${dataset}_${channel}.json" ]]; then
            completed_metrics=$((completed_metrics + 1))
        fi
    done
    if [[ "$completed_metrics" -eq "${#channels[@]}" ]]; then
        echo "SKIP_RQ2 method=$method dataset=$dataset"
        continue
    elif [[ "$completed_metrics" -ne 0 ]]; then
        echo "partial metrics already exist for $method/$dataset" >&2
        exit 5
    fi

    if [[ ! -f "$base" || ! -f "$checkpoint" ]]; then
        echo "DEFER_RQ2 missing_base_or_checkpoint=$method/$dataset"
        continue
    fi

    attack_inputs=()
    detector_outputs=()
    for channel in "${channels[@]}"; do
        attacked="$fresh_root/rule/${method}_${dataset}_${channel}.jsonl"
        evaluated="$fresh_root/rule_eval/${method}_${dataset}_${channel}.jsonl"
        attack_log="$log_root/attack_${method}_${dataset}_${channel}.stdout.log"
        if [[ -e "$attacked" || -e "$evaluated" ]]; then
            echo "refusing to overwrite RQ2 output for $method/$dataset/$channel" >&2
            exit 4
        fi
        echo "START_ATTACK method=$method dataset=$dataset channel=$channel utc=$(date -u +%FT%TZ)"
        PYTHONPATH="$deps_dir" python "$driver" \
            --input "$base" \
            --output "$attacked" \
            --lang "$language" \
            --channel "$channel" \
            --seed 42 \
            --parser-lib "$parser_lib" \
            >"$attack_log" 2>&1
        attack_inputs+=("$attacked")
        detector_outputs+=("$evaluated")
    done

    echo "START_DETECT method=$method dataset=$dataset gpu=$physical_gpu_id utc=$(date -u +%FT%TZ)"
    CUDA_VISIBLE_DEVICES="$physical_gpu_id" \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    PYTHONPATH="$deps_dir" \
    python "$detector" \
        --input "${attack_inputs[@]}" \
        --output "${detector_outputs[@]}" \
        --srcmarker-root "$srcmarker_root" \
        --checkpoint-path "$checkpoint" \
        --lang "$language" \
        --device cuda \
        --batch-size 64 \
        >"$log_root/detect_${method}_${dataset}.stdout.log" 2>&1

    for channel in "${channels[@]}"; do
        evaluated="$fresh_root/rule_eval/${method}_${dataset}_${channel}.jsonl"
        metric="$fresh_root/metrics/${method}_${dataset}_${channel}.json"
        PYTHONPATH="$deps_dir" python "$analysis" \
            --input "$evaluated" \
            --bootstrap 10000 \
            --seed 42 \
            --json-output "$metric" \
            >"$log_root/analysis_${method}_${dataset}_${channel}.stdout.log" 2>&1
    done
    echo "DONE_RQ2 method=$method dataset=$dataset utc=$(date -u +%FT%TZ)"
done
