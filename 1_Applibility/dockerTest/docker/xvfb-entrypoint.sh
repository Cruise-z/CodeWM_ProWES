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

# Start Xvfb
Xvfb "${DISPLAY}" ${XVFB_ARGS} &
XVFB_PID=$!

# Wait for Xvfb to become ready
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

# Refresh font cache to avoid missing glyphs on first render
fc-cache -f >/dev/null 2>&1 || true

# Execute the passed command; otherwise enter an interactive shell
if [[ "$#" -gt 0 ]]; then
  exec "$@"
else
  exec bash
fi