#!/usr/bin/env bash
set -euo pipefail

# 使用环境变量 DISPLAY（默认 :99）与 XVFB_ARGS
: "${DISPLAY:=:99}"
: "${XVFB_ARGS:=-screen 0 1280x800x24 -nolisten tcp -dpi 96}"

# 启动 Xvfb
Xvfb "${DISPLAY}" ${XVFB_ARGS} &

# 等待 Xvfb 就绪
for i in {1..50}; do
  if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

# 可选：刷新字体缓存（避免首次渲染缺字）
fc-cache -f >/dev/null 2>&1 || true

# 执行传入命令；否则进入交互 shell
if [ "$#" -gt 0 ]; then
  exec "$@"
else
  exec bash
fi
