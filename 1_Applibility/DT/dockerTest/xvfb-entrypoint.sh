#!/usr/bin/env bash
set -euo pipefail

# Use the DISPLAY environment variable (default: :99) and XVFB_ARGS
: "${DISPLAY:=:99}"
: "${XVFB_ARGS:=-screen 0 1280x800x24 -nolisten tcp -dpi 96}"

# Start Xvfb
Xvfb "${DISPLAY}" ${XVFB_ARGS} &

# Wait for Xvfb to become ready
for i in {1..50}; do
  if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

# Optional: refresh the font cache to avoid missing glyphs on first render
fc-cache -f >/dev/null 2>&1 || true

# Run the provided command; otherwise enter an interactive shell
if [ "$#" -gt 0 ]; then
  exec "$@"
else
  exec bash
fi
