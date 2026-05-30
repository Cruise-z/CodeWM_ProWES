#!/usr/bin/env bash
set -euo pipefail

# ====== Configurable parameters ======
CTR_NAME="${CTR_NAME:-CodeWM-DT}"     # Long-running container name
WORKDIR="${WORKDIR:-/workspace}"      # Workspace inside container
TIME_LIMIT="${TIME_LIMIT:-300}"
KILL_AFTER="${KILL_AFTER:-5}"

# 分阶段超时。未显式指定时，继承 TIME_LIMIT。
INSTALL_TIME_LIMIT="${INSTALL_TIME_LIMIT:-${TIME_LIMIT}}"
BUILD_TIME_LIMIT="${BUILD_TIME_LIMIT:-${TIME_LIMIT}}"
TEST_TIME_LIMIT="${TEST_TIME_LIMIT:-${TIME_LIMIT}}"

# 产物运行检查；智能区分正常长运行与输出型死循环。
RUN_CHECK_SECONDS="${RUN_CHECK_SECONDS:-5}"
RUN_CHECK_KILL_AFTER="${RUN_CHECK_KILL_AFTER:-2}"
RUNTIME_MAX_OUTPUT_BYTES="${RUNTIME_MAX_OUTPUT_BYTES:-262144}"
RUNTIME_MAX_OUTPUT_LINES="${RUNTIME_MAX_OUTPUT_LINES:-200}"
RUNTIME_MAX_SAME_LINE="${RUNTIME_MAX_SAME_LINE:-30}"
RUNTIME_MAX_CONSECUTIVE_SAME_LINE="${RUNTIME_MAX_CONSECUTIVE_SAME_LINE:-10}"
RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR="${RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR:-1}"
RUNTIME_LOG_TAIL_LINES="${RUNTIME_LOG_TAIL_LINES:-40}"
RUNTIME_POLL_INTERVAL="${RUNTIME_POLL_INTERVAL:-0.2}"

# 可选增强：识别无输出 CPU 忙循环。默认关闭，避免误伤游戏渲染主循环。
RUNTIME_ENABLE_CPU_BUSY_CHECK="${RUNTIME_ENABLE_CPU_BUSY_CHECK:-0}"
RUNTIME_CPU_BUSY_THRESHOLD="${RUNTIME_CPU_BUSY_THRESHOLD:-95}"
RUNTIME_CPU_BUSY_MIN_SAMPLES="${RUNTIME_CPU_BUSY_MIN_SAMPLES:-6}"

# 外层硬超时：兜底防止 podman exec / tee 因残留 stdout 不退出。
EVAL_HARD_TIMEOUT="${EVAL_HARD_TIMEOUT:-420}"
EVAL_HARD_KILL_AFTER="${EVAL_HARD_KILL_AFTER:-10}"

# Evaluator path inside container
EVALUATOR="${EVALUATOR:-/usr/local/bin/eval_protocol.sh}"

# Java
EXTRA_MVN_ARGS="${EXTRA_MVN_ARGS:-}"
EXTRA_JAVA_RUN_ARGS="${EXTRA_JAVA_RUN_ARGS:-}"

# Python
EXTRA_PIP_ARGS="${EXTRA_PIP_ARGS:-}"
EXTRA_PYTEST_ARGS="${EXTRA_PYTEST_ARGS:--q}"
EXTRA_PYTHON_RUN_ARGS="${EXTRA_PYTHON_RUN_ARGS:-}"

# C++
CMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}"
CMAKE_GENERATOR="${CMAKE_GENERATOR:-}"
EXTRA_CMAKE_ARGS="${EXTRA_CMAKE_ARGS:-}"
EXTRA_CTEST_ARGS="${EXTRA_CTEST_ARGS:---output-on-failure}"

# ====== Proxy passthrough ======
HOST_HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-}}"
HOST_HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-}}"
HOST_NO_PROXY="${NO_PROXY:-${no_proxy:-}}"

HOST_PIP_INDEX_URL="${PIP_INDEX_URL:-${pip_index_url:-}}"
HOST_PIP_EXTRA_INDEX_URL="${PIP_EXTRA_INDEX_URL:-${pip_extra_index_url:-}}"
HOST_PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-${pip_trusted_host:-}}"

# ====== Optional Maven settings.xml proxy injection ======
ENABLE_MAVEN_PROXY_CONFIG="${ENABLE_MAVEN_PROXY_CONFIG:-0}"
MAVEN_PROXY_HOST="${MAVEN_PROXY_HOST:-}"
MAVEN_PROXY_PORT="${MAVEN_PROXY_PORT:-}"
MAVEN_PROXY_HTTP_HOST="${MAVEN_PROXY_HTTP_HOST:-${MAVEN_PROXY_HOST}}"
MAVEN_PROXY_HTTP_PORT="${MAVEN_PROXY_HTTP_PORT:-${MAVEN_PROXY_PORT}}"
MAVEN_PROXY_HTTPS_HOST="${MAVEN_PROXY_HTTPS_HOST:-${MAVEN_PROXY_HOST}}"
MAVEN_PROXY_HTTPS_PORT="${MAVEN_PROXY_HTTPS_PORT:-${MAVEN_PROXY_PORT}}"

usage() {
  cat <<EOF_USAGE
Usage: $0 <project_dir>

Run protocol-based evaluation, packaging, and smart run-check inside a running Podman container.

Arguments:
  project_dir   Path to the generated project root directory

Optional env:
  CTR_NAME=CodeWM-DT
  WORKDIR=/workspace
  EVALUATOR=/usr/local/bin/eval_protocol.sh
  TIME_LIMIT=300
  INSTALL_TIME_LIMIT=300
  BUILD_TIME_LIMIT=300
  TEST_TIME_LIMIT=300
  KILL_AFTER=5

  RUN_CHECK_SECONDS=5
  RUN_CHECK_KILL_AFTER=2
  RUNTIME_MAX_OUTPUT_BYTES=262144
  RUNTIME_MAX_OUTPUT_LINES=200
  RUNTIME_MAX_SAME_LINE=30
  RUNTIME_MAX_CONSECUTIVE_SAME_LINE=10
  RUNTIME_ENABLE_CPU_BUSY_CHECK=0

  EVAL_HARD_TIMEOUT=420
  EVAL_HARD_KILL_AFTER=10

  EXTRA_MVN_ARGS="..."
  EXTRA_JAVA_RUN_ARGS="..."
  EXTRA_PIP_ARGS="..."
  EXTRA_PYTEST_ARGS="-q"
  EXTRA_PYTHON_RUN_ARGS="..."

  CMAKE_BUILD_TYPE=Release|Debug
  CMAKE_GENERATOR=Ninja
  EXTRA_CMAKE_ARGS="..."
  EXTRA_CTEST_ARGS="--output-on-failure"

Proxy env passthrough:
  HTTP_PROXY / HTTPS_PROXY / NO_PROXY
  PIP_INDEX_URL / PIP_EXTRA_INDEX_URL / PIP_TRUSTED_HOST

Optional Maven proxy injection:
  ENABLE_MAVEN_PROXY_CONFIG=1
  MAVEN_PROXY_HOST=127.0.0.1
  MAVEN_PROXY_PORT=7897

or separately:
  MAVEN_PROXY_HTTP_HOST=127.0.0.1
  MAVEN_PROXY_HTTP_PORT=7897
  MAVEN_PROXY_HTTPS_HOST=127.0.0.1
  MAVEN_PROXY_HTTPS_PORT=7897
EOF_USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

PROJECT_DIR="$1"
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[error] Project directory not found: $PROJECT_DIR"
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

check_container_running() {
  if ! podman ps --format '{{.Names}}' | grep -q "^${CTR_NAME}$"; then
    echo "[error] Container ${CTR_NAME} is not running."
    echo "Start it first, for example:"
    echo "  podman run -d --name ${CTR_NAME} protocol-evaluator sleep infinity"
    exit 1
  fi
}

check_xvfb_ready() {
  if podman exec "$CTR_NAME" sh -lc 'xdpyinfo -display "${DISPLAY:-:99}" >/dev/null 2>&1'; then
    echo "[INFO] Xvfb is ready in container '${CTR_NAME}'."
  else
    echo "[WARN] Xvfb is not ready in container '${CTR_NAME}'."
    echo "[WARN] Non-GUI test paths may still work, but GUI-dependent runtime behavior could fail."
  fi
}

check_evaluator_exists() {
  if ! podman exec "$CTR_NAME" sh -lc "test -x '$EVALUATOR'"; then
    echo "[error] Evaluator script not found or not executable in container: $EVALUATOR"
    exit 1
  fi
}

copy_project_into_container() {
  echo ">>> Copy project into container: ${PROJECT_DIR} -> ${CTR_NAME}:${IN_CTR_DIR}"
  podman exec \
    -e HTTP_PROXY="$HOST_HTTP_PROXY" \
    -e HTTPS_PROXY="$HOST_HTTPS_PROXY" \
    -e NO_PROXY="$HOST_NO_PROXY" \
    "$CTR_NAME" bash -lc "mkdir -p '$IN_CTR_DIR'"
  podman cp "${PROJECT_DIR}/." "${CTR_NAME}:${IN_CTR_DIR}/"
}

write_maven_proxy_config() {
  if [[ "${ENABLE_MAVEN_PROXY_CONFIG}" != "1" ]]; then
    echo ">>> Skip Maven proxy config (ENABLE_MAVEN_PROXY_CONFIG != 1)"
    return 0
  fi

  if [[ -z "${MAVEN_PROXY_HTTP_HOST}" || -z "${MAVEN_PROXY_HTTP_PORT}" || -z "${MAVEN_PROXY_HTTPS_HOST}" || -z "${MAVEN_PROXY_HTTPS_PORT}" ]]; then
    echo "[error] Maven proxy config enabled, but proxy host/port is incomplete."
    echo "Set either:"
    echo "  MAVEN_PROXY_HOST and MAVEN_PROXY_PORT"
    echo "or separately:"
    echo "  MAVEN_PROXY_HTTP_HOST / MAVEN_PROXY_HTTP_PORT / MAVEN_PROXY_HTTPS_HOST / MAVEN_PROXY_HTTPS_PORT"
    exit 1
  fi

  echo ">>> Write Maven proxy config to container"
  podman exec \
    -e MAVEN_PROXY_HTTP_HOST="$MAVEN_PROXY_HTTP_HOST" \
    -e MAVEN_PROXY_HTTP_PORT="$MAVEN_PROXY_HTTP_PORT" \
    -e MAVEN_PROXY_HTTPS_HOST="$MAVEN_PROXY_HTTPS_HOST" \
    -e MAVEN_PROXY_HTTPS_PORT="$MAVEN_PROXY_HTTPS_PORT" \
    "$CTR_NAME" bash -lc '
      set -e
      mkdir -p /root/.m2
      cat > /root/.m2/settings.xml <<EOF
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              https://maven.apache.org/xsd/settings-1.0.0.xsd">
  <proxies>
    <proxy>
      <id>proxy-http</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>${MAVEN_PROXY_HTTP_HOST}</host>
      <port>${MAVEN_PROXY_HTTP_PORT}</port>
    </proxy>
    <proxy>
      <id>proxy-https</id>
      <active>true</active>
      <protocol>https</protocol>
      <host>${MAVEN_PROXY_HTTPS_HOST}</host>
      <port>${MAVEN_PROXY_HTTPS_PORT}</port>
    </proxy>
  </proxies>
</settings>
EOF
'
}

copy_results_back() {
  echo ">>> Copy evaluation results back to host"
  podman cp "${CTR_NAME}:${IN_CTR_DIR}/DTResults/." "${OUT_DIR}/" 2>/dev/null || true
}

cleanup_in_container() {
  echo ">>> Cleanup possible leftover processes in container"
  podman exec \
    -e IN_CTR_DIR="$IN_CTR_DIR" \
    "$CTR_NAME" bash -lc '
      set +e
      project_dir="${IN_CTR_DIR}"
      pids=""

      # Prefer cwd/cmdline-based cleanup, so we do not kill unrelated processes in the long-running container.
      for proc in /proc/[0-9]*; do
        pid="${proc#/proc/}"
        [ "$pid" = "$$" ] && continue

        cwd="$(readlink "$proc/cwd" 2>/dev/null || true)"
        cmd="$(tr "\0" " " < "$proc/cmdline" 2>/dev/null || true)"

        case "${cwd} ${cmd}" in
          *"${project_dir}"*) pids="${pids} ${pid}" ;;
        esac
      done

      if [ -n "${pids}" ]; then
        echo "[INFO] Cleanup TERM pids:${pids}"
        kill -TERM ${pids} 2>/dev/null || true
        sleep 2
        echo "[INFO] Cleanup KILL remaining pids:${pids}"
        kill -KILL ${pids} 2>/dev/null || true
      else
        echo "[INFO] No leftover project-scoped processes found."
      fi
    ' || true
}

run_evaluation_in_container() {
  echo ">>> Run evaluator in container"
  timeout --signal=TERM --kill-after="${EVAL_HARD_KILL_AFTER}s" "${EVAL_HARD_TIMEOUT}s" \
  podman exec \
    -e TIME_LIMIT="$TIME_LIMIT" \
    -e KILL_AFTER="$KILL_AFTER" \
    -e INSTALL_TIME_LIMIT="$INSTALL_TIME_LIMIT" \
    -e BUILD_TIME_LIMIT="$BUILD_TIME_LIMIT" \
    -e TEST_TIME_LIMIT="$TEST_TIME_LIMIT" \
    -e RUN_CHECK_SECONDS="$RUN_CHECK_SECONDS" \
    -e RUN_CHECK_KILL_AFTER="$RUN_CHECK_KILL_AFTER" \
    -e RUNTIME_MAX_OUTPUT_BYTES="$RUNTIME_MAX_OUTPUT_BYTES" \
    -e RUNTIME_MAX_OUTPUT_LINES="$RUNTIME_MAX_OUTPUT_LINES" \
    -e RUNTIME_MAX_SAME_LINE="$RUNTIME_MAX_SAME_LINE" \
    -e RUNTIME_MAX_CONSECUTIVE_SAME_LINE="$RUNTIME_MAX_CONSECUTIVE_SAME_LINE" \
    -e RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR="$RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR" \
    -e RUNTIME_LOG_TAIL_LINES="$RUNTIME_LOG_TAIL_LINES" \
    -e RUNTIME_POLL_INTERVAL="$RUNTIME_POLL_INTERVAL" \
    -e RUNTIME_ENABLE_CPU_BUSY_CHECK="$RUNTIME_ENABLE_CPU_BUSY_CHECK" \
    -e RUNTIME_CPU_BUSY_THRESHOLD="$RUNTIME_CPU_BUSY_THRESHOLD" \
    -e RUNTIME_CPU_BUSY_MIN_SAMPLES="$RUNTIME_CPU_BUSY_MIN_SAMPLES" \
    -e EXTRA_MVN_ARGS="$EXTRA_MVN_ARGS" \
    -e EXTRA_JAVA_RUN_ARGS="$EXTRA_JAVA_RUN_ARGS" \
    -e EXTRA_PIP_ARGS="$EXTRA_PIP_ARGS" \
    -e EXTRA_PYTEST_ARGS="$EXTRA_PYTEST_ARGS" \
    -e EXTRA_PYTHON_RUN_ARGS="$EXTRA_PYTHON_RUN_ARGS" \
    -e CMAKE_BUILD_TYPE="$CMAKE_BUILD_TYPE" \
    -e CMAKE_GENERATOR="$CMAKE_GENERATOR" \
    -e EXTRA_CMAKE_ARGS="$EXTRA_CMAKE_ARGS" \
    -e EXTRA_CTEST_ARGS="$EXTRA_CTEST_ARGS" \
    -e HTTP_PROXY="$HOST_HTTP_PROXY" \
    -e HTTPS_PROXY="$HOST_HTTPS_PROXY" \
    -e NO_PROXY="$HOST_NO_PROXY" \
    -e PIP_INDEX_URL="$HOST_PIP_INDEX_URL" \
    -e PIP_EXTRA_INDEX_URL="$HOST_PIP_EXTRA_INDEX_URL" \
    -e PIP_TRUSTED_HOST="$HOST_PIP_TRUSTED_HOST" \
    "$CTR_NAME" bash -lc "
      set -euo pipefail
      mkdir -p '${IN_CTR_DIR}/DTResults'
      '${EVALUATOR}' '${IN_CTR_DIR}' 2>&1 | tee '${IN_CTR_DIR}/DTResults/evaluation.log'
    "
}

STAMP="$(date +%Y%m%d_%H%M%S)"
IN_CTR_DIR="${WORKDIR}/proj_${STAMP}"
OUTPUT_DIR="${PROJECT_DIR}/DTResults"
OUT_DIR="${OUTPUT_DIR}/out_${STAMP}"
mkdir -p "$OUT_DIR"

LOG="${OUT_DIR}/host_wrapper_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

echo "===== BEGIN @ ${STAMP} ====="
echo "[INFO] Project dir:        $PROJECT_DIR"
echo "[INFO] Container name:    $CTR_NAME"
echo "[INFO] In-container dir:  $IN_CTR_DIR"
echo "[INFO] Output dir:        $OUT_DIR"
echo "[INFO] Wrapper log:       $LOG"
echo "[INFO] Time limit:        ${TIME_LIMIT}s (kill-after ${KILL_AFTER}s)"
echo "[INFO] Install limit:     ${INSTALL_TIME_LIMIT}s"
echo "[INFO] Build limit:       ${BUILD_TIME_LIMIT}s"
echo "[INFO] Test limit:        ${TEST_TIME_LIMIT}s"
echo "[INFO] Run check:         ${RUN_CHECK_SECONDS}s (kill-after ${RUN_CHECK_KILL_AFTER}s)"
echo "[INFO] Runtime output thresholds: bytes=${RUNTIME_MAX_OUTPUT_BYTES}, lines=${RUNTIME_MAX_OUTPUT_LINES}, same_line=${RUNTIME_MAX_SAME_LINE}, consecutive_same_line=${RUNTIME_MAX_CONSECUTIVE_SAME_LINE}"
echo "[INFO] CPU busy check:    ${RUNTIME_ENABLE_CPU_BUSY_CHECK}"
echo "[INFO] Hard eval timeout: ${EVAL_HARD_TIMEOUT}s (kill-after ${EVAL_HARD_KILL_AFTER}s)"
echo "[INFO] HTTP_PROXY:        ${HOST_HTTP_PROXY:-<empty>}"
echo "[INFO] HTTPS_PROXY:       ${HOST_HTTPS_PROXY:-<empty>}"
echo "[INFO] NO_PROXY:          ${HOST_NO_PROXY:-<empty>}"
echo "[INFO] PIP_INDEX_URL:     ${HOST_PIP_INDEX_URL:-<empty>}"
echo "[INFO] ENABLE_MAVEN_PROXY_CONFIG: ${ENABLE_MAVEN_PROXY_CONFIG}"
if [[ "${ENABLE_MAVEN_PROXY_CONFIG}" == "1" ]]; then
  echo "[INFO] MAVEN_PROXY_HTTP:  ${MAVEN_PROXY_HTTP_HOST:-<empty>}:${MAVEN_PROXY_HTTP_PORT:-<empty>}"
  echo "[INFO] MAVEN_PROXY_HTTPS: ${MAVEN_PROXY_HTTPS_HOST:-<empty>}:${MAVEN_PROXY_HTTPS_PORT:-<empty>}"
fi
echo

check_container_running
check_xvfb_ready
check_evaluator_exists
copy_project_into_container
write_maven_proxy_config

EVAL_RC=0
set +e
run_evaluation_in_container
EVAL_RC=$?
set -e

if [[ $EVAL_RC -eq 124 || $EVAL_RC -eq 137 ]]; then
  echo "[error] Evaluation hard timeout reached in host wrapper. exit_code=${EVAL_RC}"
elif [[ $EVAL_RC -ne 0 ]]; then
  echo "[WARN] Evaluation failed with exit code: ${EVAL_RC}"
fi

cleanup_in_container || true
copy_results_back || true

echo
echo "===== DONE ====="
echo "Artifacts in: $OUT_DIR"
echo "Packaged runnable artifacts should be under: $OUT_DIR/artifacts"
echo "Container evaluation log should be under: $OUT_DIR/evaluation.log"
echo "Wrapper log : $LOG"

exit "$EVAL_RC"