#!/usr/bin/env bash
set -euo pipefail

: "${DISPLAY:=:99}"
: "${XVFB_ARGS:=-screen 0 1280x800x24 -nolisten tcp -dpi 96}"

cleanup() {
  if [[ -n "${XVFB_PID:-}" ]] && kill -0 "${XVFB_PID}" >/dev/null 2>&1; then
    kill "${XVFB_PID}" >/dev/null 2>&1 || true
    wait "${XVFB_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# 启动 Xvfb
Xvfb "${DISPLAY}" ${XVFB_ARGS} &
XVFB_PID=$!

# 等待 Xvfb 就绪
ready=0
for i in {1..50}; do
  if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    ready=1
    break
  fi

  if ! kill -0 "${XVFB_PID}" >/dev/null 2>&1; then
    echo "[error] Xvfb exited unexpectedly"
    exit 1
  fi

  sleep 0.1
done

if [[ "${ready}" -ne 1 ]]; then
  echo "[error] Xvfb did not become ready on display ${DISPLAY}"
  exit 1
fi

# 刷新字体缓存，避免首次渲染缺字
fc-cache -f >/dev/null 2>&1 || true

# 执行传入命令；否则进入交互 shell
if [[ "$#" -gt 0 ]]; then
  exec "$@"
else
  exec bash
fi