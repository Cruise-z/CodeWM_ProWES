#!/usr/bin/env bash
# 任何一个命令失败就立刻停止
# set -euo pipefail
# 某个方法跑崩了也继续跑后面的
set -u pipefail

# ====== 统一参数（按需改） ======
PROJECT="tiny_snake_game"
SRCPATH="/home/zhaorz/project/CodeWM/srcRepo"
WSPATH="/home/zhaorz/project/CodeWM/MetaGPT/workspace"
RESPATH="/home/zhaorz/project/CodeWM/results"

SEEDS='range:100:120'
STRENGTHS='0.0,0.5,1.0,2.0,3.0'
BASELINE='0.0'

# 可选：每次命令之间加一点提示
run() {
  echo
  echo "================================================================"
  echo "[RUN] $*"
  echo "================================================================"
  "$@"
}

# ====== 1) WLLM ======
run python3 detection_eval.py \
  --project_name "$PROJECT" \
  --srcPath "$SRCPATH" \
  --workspacePath "$WSPATH" \
  --resPath "$RESPATH" \
  --method wllm \
  --seeds "$SEEDS" \
  --strengths "$STRENGTHS" \
  --baseline_strength "$BASELINE" \
  --score_field z_score \
  --method_args_json '{"gamma":0.5,"z_threshold":4.0}' \
  --save_csv

# ====== 2) SWEET ======
run python3 detection_eval.py \
  --project_name "$PROJECT" \
  --srcPath "$SRCPATH" \
  --workspacePath "$WSPATH" \
  --resPath "$RESPATH" \
  --method sweet \
  --seeds "$SEEDS" \
  --strengths "$STRENGTHS" \
  --baseline_strength "$BASELINE" \
  --score_field z_score \
  --method_args_json '{"gamma":0.5,"ET":0.5,"z_threshold":4.0}' \
  --save_csv

# ====== 3) EWD ======
run python3 detection_eval.py \
  --project_name "$PROJECT" \
  --srcPath "$SRCPATH" \
  --workspacePath "$WSPATH" \
  --resPath "$RESPATH" \
  --method ewd \
  --seeds "$SEEDS" \
  --strengths "$STRENGTHS" \
  --baseline_strength "$BASELINE" \
  --score_field score \
  --method_args_json '{"gamma":0.5,"hash_key":83782121,"z_threshold":4.0,"prefix_length":1}' \
  --save_csv

# ====== 4) STONE ======
run python3 detection_eval.py \
  --project_name "$PROJECT" \
  --srcPath "$SRCPATH" \
  --workspacePath "$WSPATH" \
  --resPath "$RESPATH" \
  --method stone \
  --seeds "$SEEDS" \
  --strengths "$STRENGTHS" \
  --baseline_strength "$BASELINE" \
  --score_field score \
  --method_args_json '{"gamma":0.5,"hash_key":83782121,"z_threshold":4.0,"prefix_length":1}' \
  --save_csv

# ====== 5) WATERFALL ======
run python3 detection_eval.py \
  --project_name "$PROJECT" \
  --srcPath "$SRCPATH" \
  --workspacePath "$WSPATH" \
  --resPath "$RESPATH" \
  --method waterfall \
  --seeds "$SEEDS" \
  --strengths "$STRENGTHS" \
  --baseline_strength "$BASELINE" \
  --score_field q_score \
  --strategy_key 'WaterfallLogitsProcessor[0]' \
  --method_args_json '{"id_mu":42,"k_p":1,"n_gram":2,"wm_fn":"fourier","auto_reset":true,"detect_mode":"batch"}' \
  --save_csv

echo
echo "[DONE] All evaluations finished successfully."
