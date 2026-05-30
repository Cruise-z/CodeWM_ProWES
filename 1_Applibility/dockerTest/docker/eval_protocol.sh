#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/workspace}"

# 可选参数
# TIME_LIMIT 保留为兼容旧协议；未显式设置分阶段超时时，会作为安装/构建/测试默认值。
TIME_LIMIT="${TIME_LIMIT:-300}"
KILL_AFTER="${KILL_AFTER:-5}"

# 分阶段超时：测试阶段超时应判失败，运行阶段单独智能判断。
INSTALL_TIME_LIMIT="${INSTALL_TIME_LIMIT:-${TIME_LIMIT}}"
BUILD_TIME_LIMIT="${BUILD_TIME_LIMIT:-${TIME_LIMIT}}"
TEST_TIME_LIMIT="${TEST_TIME_LIMIT:-${TIME_LIMIT}}"

# 产物运行验证时长（秒）
RUN_CHECK_SECONDS="${RUN_CHECK_SECONDS:-5}"
RUN_CHECK_KILL_AFTER="${RUN_CHECK_KILL_AFTER:-2}"

# 智能运行时检查：区分“正常长运行”和“输出型死循环”。
RUNTIME_MAX_OUTPUT_BYTES="${RUNTIME_MAX_OUTPUT_BYTES:-262144}"          # 256 KiB
RUNTIME_MAX_OUTPUT_LINES="${RUNTIME_MAX_OUTPUT_LINES:-200}"
RUNTIME_MAX_SAME_LINE="${RUNTIME_MAX_SAME_LINE:-30}"
RUNTIME_MAX_CONSECUTIVE_SAME_LINE="${RUNTIME_MAX_CONSECUTIVE_SAME_LINE:-10}"
RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR="${RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR:-1}"
RUNTIME_LOG_TAIL_LINES="${RUNTIME_LOG_TAIL_LINES:-40}"
RUNTIME_POLL_INTERVAL="${RUNTIME_POLL_INTERVAL:-0.2}"

# 可选增强：识别无输出但 CPU 忙循环。默认关闭，避免误伤游戏渲染主循环。
RUNTIME_ENABLE_CPU_BUSY_CHECK="${RUNTIME_ENABLE_CPU_BUSY_CHECK:-0}"
RUNTIME_CPU_BUSY_THRESHOLD="${RUNTIME_CPU_BUSY_THRESHOLD:-95}"          # 进程组 CPU 百分比阈值
RUNTIME_CPU_BUSY_MIN_SAMPLES="${RUNTIME_CPU_BUSY_MIN_SAMPLES:-6}"       # 至少多少次采样超过阈值才判定

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

usage() {
  cat <<EOF_USAGE
Usage: $0 [PROJECT_DIR]

Evaluate, package, and briefly run-check a project according to the unified interface protocol.

Supported protocols:

  Java:
    - Build file: pom.xml
    - Runtime entry: src/main/java/Main.java
    - Test target: src/test/java/MainTest.java
    - Test command: mvn -q test
    - Packaged artifact: target/*.jar
    - Run check: mvn -q -DskipTests exec:java -Dexec.mainClass=Main

  Python:
    - Build file: requirements.txt
    - Runtime entry: Main.py
    - Test target: tests/test_main.py
    - Test command: pytest -q
    - Runnable artifact: .pyz zipapp
    - Run check: python <artifact>.pyz

  C++:
    - Build file: CMakeLists.txt
    - Runtime entry: src/Main.cpp
    - Test target: tests/test_main.cpp
    - Test command: ctest --test-dir build --output-on-failure
    - Runnable artifact: executable binary from build/
    - Run check: <binary>

Env:
  TIME_LIMIT=300
  INSTALL_TIME_LIMIT=
  BUILD_TIME_LIMIT=
  TEST_TIME_LIMIT=
  KILL_AFTER=5
  RUN_CHECK_SECONDS=5
  RUN_CHECK_KILL_AFTER=2
  RUNTIME_MAX_OUTPUT_BYTES=262144
  RUNTIME_MAX_OUTPUT_LINES=200
  RUNTIME_MAX_SAME_LINE=30
  RUNTIME_MAX_CONSECUTIVE_SAME_LINE=10
  RUNTIME_ENABLE_CPU_BUSY_CHECK=0
EOF_USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[error] Project directory not found: $PROJECT_DIR"
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
cd "$PROJECT_DIR"

ARTIFACT_DIR="${PROJECT_DIR}/DTResults/artifacts"
RUNTIME_DIR="${PROJECT_DIR}/DTResults/runtime"
mkdir -p "$ARTIFACT_DIR" "$RUNTIME_DIR"

json_escape() {
  local s="${1:-}"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

write_runtime_status() {
  local status_file="$1"
  local status="$2"
  local reason="$3"
  local exit_code="$4"
  local bytes="${5:-0}"
  local lines="${6:-0}"
  local max_same_line="${7:-0}"
  local max_consecutive_same_line="${8:-0}"
  local cpu_busy_samples="${9:-0}"

  local escaped_reason
  escaped_reason="$(json_escape "$reason")"

  cat > "$status_file" <<EOF_STATUS
{"phase":"runtime_check","status":"${status}","reason":"${escaped_reason}","exit_code":${exit_code},"output_bytes":${bytes},"output_lines":${lines},"max_same_line":${max_same_line},"max_consecutive_same_line":${max_consecutive_same_line},"cpu_busy_samples":${cpu_busy_samples}}
EOF_STATUS
}

print_runtime_status_to_evaluation_log() {
  local status_file="$1"
  if [[ -f "$status_file" ]]; then
    echo "[RUNTIME_STATUS] $(cat "$status_file")"
  fi
}

run_install_with_timeout() {
  local cmd="$1"
  echo "[INFO] Install timeout limit: ${INSTALL_TIME_LIMIT}s (kill-after ${KILL_AFTER}s)"
  set +e
  timeout --signal=TERM --kill-after="${KILL_AFTER}s" "${INSTALL_TIME_LIMIT}s" bash -lc "$cmd"
  local rc=$?
  set -e

  if [[ $rc -eq 124 || $rc -eq 137 ]]; then
    echo "[error] Install step timed out after ${INSTALL_TIME_LIMIT}s."
    return 124
  fi
  return "$rc"
}

run_build_with_timeout() {
  local cmd="$1"
  echo "[INFO] Build timeout limit: ${BUILD_TIME_LIMIT}s (kill-after ${KILL_AFTER}s)"
  set +e
  timeout --signal=TERM --kill-after="${KILL_AFTER}s" "${BUILD_TIME_LIMIT}s" bash -lc "$cmd"
  local rc=$?
  set -e

  if [[ $rc -eq 124 || $rc -eq 137 ]]; then
    echo "[error] Build step timed out after ${BUILD_TIME_LIMIT}s."
    return 124
  fi
  return "$rc"
}

run_test_with_timeout() {
  local cmd="$1"
  echo "[INFO] Test timeout limit: ${TEST_TIME_LIMIT}s (kill-after ${KILL_AFTER}s)"
  set +e
  timeout --signal=TERM --kill-after="${KILL_AFTER}s" "${TEST_TIME_LIMIT}s" bash -lc "$cmd"
  local rc=$?
  set -e

  if [[ $rc -eq 124 || $rc -eq 137 ]]; then
    echo "[error] Test step timed out after ${TEST_TIME_LIMIT}s. Possible infinite loop or hanging test."
    return 124
  fi
  return "$rc"
}

runtime_output_stats() {
  local log="$1"
  local bytes=0
  local lines=0
  local max_same_line=0
  local max_consecutive_same_line=0

  if [[ -f "$log" ]]; then
    bytes="$(wc -c < "$log" 2>/dev/null | tr -d ' ' || echo 0)"
    lines="$(wc -l < "$log" 2>/dev/null | tr -d ' ' || echo 0)"

    max_same_line="$({
      awk '
        length($0) > 0 { count[$0]++ }
        END {
          max = 0
          for (line in count) {
            if (count[line] > max) max = count[line]
          }
          print max + 0
        }
      ' "$log" 2>/dev/null || echo 0
    } | tail -n 1)"

    max_consecutive_same_line="$({
      awk '
        length($0) > 0 {
          if ($0 == prev) {
            current++
          } else {
            prev = $0
            current = 1
          }
          if (current > max) max = current
        }
        END { print max + 0 }
      ' "$log" 2>/dev/null || echo 0
    } | tail -n 1)"
  fi

  printf '%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
}

classify_runtime_log() {
  local log="$1"
  local stats
  stats="$(runtime_output_stats "$log")"

  local bytes lines max_same_line max_consecutive_same_line
  IFS=$'\t' read -r bytes lines max_same_line max_consecutive_same_line <<< "$stats"

  echo "[INFO] Runtime output stats: bytes=${bytes}, lines=${lines}, max_same_line=${max_same_line}, max_consecutive_same_line=${max_consecutive_same_line}" >&2

  if (( bytes > RUNTIME_MAX_OUTPUT_BYTES )); then
    printf 'output_loop_bytes\t%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
    return 10
  fi

  if (( lines > RUNTIME_MAX_OUTPUT_LINES )); then
    printf 'output_loop_lines\t%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
    return 11
  fi

  if (( max_same_line > RUNTIME_MAX_SAME_LINE )); then
    printf 'output_loop_repeated_line\t%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
    return 12
  fi

  if (( max_consecutive_same_line > RUNTIME_MAX_CONSECUTIVE_SAME_LINE )); then
    printf 'output_loop_consecutive_repeated_line\t%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
    return 13
  fi

  printf 'long_running_startup\t%s\t%s\t%s\t%s\n' "$bytes" "$lines" "$max_same_line" "$max_consecutive_same_line"
  return 0
}

sum_process_group_cpu() {
  local pgid="$1"
  ps -o %cpu= -g "$pgid" 2>/dev/null | awk '{sum += $1} END {printf "%.0f", sum + 0}' 2>/dev/null || echo 0
}

terminate_process_group() {
  local pid="$1"
  local kill_after="$2"

  kill -TERM -- "-$pid" >/dev/null 2>&1 || kill -TERM "$pid" >/dev/null 2>&1 || true
  sleep "$kill_after"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -KILL -- "-$pid" >/dev/null 2>&1 || kill -KILL "$pid" >/dev/null 2>&1 || true
  fi

  wait "$pid" >/dev/null 2>&1 || true
}

print_runtime_log_sample() {
  local log="$1"
  if [[ -s "$log" ]]; then
    echo "[INFO] Runtime log sample follows: $log"
    echo "----- BEGIN runtime log tail (${RUNTIME_LOG_TAIL_LINES} lines) -----"
    tail -n "$RUNTIME_LOG_TAIL_LINES" "$log" || true
    echo "----- END runtime log tail -----"
  else
    echo "[INFO] Runtime log is empty: $log"
  fi
}

run_artifact_smart_check() {
  local cmd="$1"
  local label="${2:-runtime}"

  local limit="${RUN_CHECK_SECONDS}"
  local kill_after="${RUN_CHECK_KILL_AFTER}"
  local runtime_log="${RUNTIME_DIR}/${label}.log"
  local runtime_status="${RUNTIME_DIR}/${label}_status.json"

  : > "$runtime_log"

  echo ">>> Running packaged artifact smart runtime check (${limit}s)"
  echo "[INFO] Runtime command: $cmd"
  echo "[INFO] Runtime output is captured in: $runtime_log"
  echo "[INFO] Runtime thresholds: max_bytes=${RUNTIME_MAX_OUTPUT_BYTES}, max_lines=${RUNTIME_MAX_OUTPUT_LINES}, max_same_line=${RUNTIME_MAX_SAME_LINE}, max_consecutive_same_line=${RUNTIME_MAX_CONSECUTIVE_SAME_LINE}, cpu_busy_check=${RUNTIME_ENABLE_CPU_BUSY_CHECK}"

  local escaped_cmd
  local launcher_cmd
  printf -v escaped_cmd '%q' "$cmd"
  launcher_cmd="export PYTHONUNBUFFERED=1; if command -v stdbuf >/dev/null 2>&1; then exec stdbuf -oL -eL bash -lc ${escaped_cmd}; else exec bash -lc ${escaped_cmd}; fi"

  set +e
  setsid bash -lc "$launcher_cmd" >"$runtime_log" 2>&1 < /dev/null &
  local pid=$!
  local rc=0
  local timed_out=0
  local early_output_loop=0
  local cpu_busy_samples=0
  local start_time now elapsed bytes stats
  start_time="$(date +%s)"

  while kill -0 "$pid" >/dev/null 2>&1; do
    now="$(date +%s)"
    elapsed=$(( now - start_time ))

    if [[ -f "$runtime_log" ]]; then
      bytes="$(wc -c < "$runtime_log" 2>/dev/null | tr -d ' ' || echo 0)"
      if (( bytes > RUNTIME_MAX_OUTPUT_BYTES )); then
        echo "[error] Runtime output exceeded byte threshold before ${limit}s: bytes=${bytes}, threshold=${RUNTIME_MAX_OUTPUT_BYTES}"
        early_output_loop=1
        break
      fi
    fi

    if [[ "${RUNTIME_ENABLE_CPU_BUSY_CHECK}" == "1" ]]; then
      local cpu_now
      cpu_now="$(sum_process_group_cpu "$pid")"
      if (( cpu_now >= RUNTIME_CPU_BUSY_THRESHOLD )); then
        cpu_busy_samples=$(( cpu_busy_samples + 1 ))
      fi
    fi

    if (( elapsed >= limit )); then
      timed_out=1
      break
    fi

    sleep "$RUNTIME_POLL_INTERVAL"
  done

  if [[ "$early_output_loop" -eq 1 ]]; then
    terminate_process_group "$pid" "$kill_after"
    local reason bytes_v lines_v max_same_v max_consec_v
    local classify_result
    classify_result="$(classify_runtime_log "$runtime_log")"
    IFS=$'\t' read -r reason bytes_v lines_v max_same_v max_consec_v <<< "$classify_result"

    echo "[error] RUNTIME_ERROR: output loop detected during startup/runtime. reason=${reason}"
    print_runtime_log_sample "$runtime_log"
    write_runtime_status "$runtime_status" "runtime_error" "$reason" 124 "$bytes_v" "$lines_v" "$max_same_v" "$max_consec_v" "$cpu_busy_samples"
    print_runtime_status_to_evaluation_log "$runtime_status"
    set -e
    return 124
  fi

  if [[ "$timed_out" -eq 0 ]]; then
    wait "$pid"
    rc=$?

    stats="$(runtime_output_stats "$runtime_log")"
    local bytes_v lines_v max_same_v max_consec_v
    IFS=$'\t' read -r bytes_v lines_v max_same_v max_consec_v <<< "$stats"

    if [[ "$rc" -eq 0 ]]; then
      echo "[INFO] Packaged artifact exited normally during runtime check."
      print_runtime_log_sample "$runtime_log"
      write_runtime_status "$runtime_status" "success" "normal_exit" 0 "$bytes_v" "$lines_v" "$max_same_v" "$max_consec_v" "$cpu_busy_samples"
      print_runtime_status_to_evaluation_log "$runtime_status"
      set -e
      return 0
    else
      echo "[error] RUNTIME_ERROR: packaged artifact exited with non-zero code during runtime check: $rc"
      print_runtime_log_sample "$runtime_log"
      write_runtime_status "$runtime_status" "runtime_error" "nonzero_exit" "$rc" "$bytes_v" "$lines_v" "$max_same_v" "$max_consec_v" "$cpu_busy_samples"
      print_runtime_status_to_evaluation_log "$runtime_status"
      set -e
      return "$rc"
    fi
  fi

  echo "[INFO] Packaged artifact is still running after ${limit}s. Classifying as normal long-running startup or runtime error."

  local reason bytes_v lines_v max_same_v max_consec_v
  local classify_rc=0
  local classify_result
  classify_result="$(classify_runtime_log "$runtime_log")"
  classify_rc=$?
  IFS=$'\t' read -r reason bytes_v lines_v max_same_v max_consec_v <<< "$classify_result"

  terminate_process_group "$pid" "$kill_after"

  if [[ "${RUNTIME_ENABLE_CPU_BUSY_CHECK}" == "1" && "$classify_rc" -eq 0 && "$cpu_busy_samples" -ge "$RUNTIME_CPU_BUSY_MIN_SAMPLES" ]]; then
    reason="busy_loop_cpu"
    classify_rc=20
    echo "[error] Runtime CPU busy-loop suspected: busy_samples=${cpu_busy_samples}, threshold=${RUNTIME_CPU_BUSY_THRESHOLD}, min_samples=${RUNTIME_CPU_BUSY_MIN_SAMPLES}"
  fi

  if [[ "$classify_rc" -ne 0 && "${RUNTIME_TREAT_OUTPUT_LOOP_AS_ERROR}" == "1" ]]; then
    echo "[error] RUNTIME_ERROR: runtime pattern indicates a likely infinite loop. reason=${reason}"
    print_runtime_log_sample "$runtime_log"
    write_runtime_status "$runtime_status" "runtime_error" "$reason" 124 "$bytes_v" "$lines_v" "$max_same_v" "$max_consec_v" "$cpu_busy_samples"
    print_runtime_status_to_evaluation_log "$runtime_status"
    set -e
    return 124
  fi

  echo "[INFO] Packaged artifact is long-running, but runtime output pattern is not abnormal. Treating as successful startup."
  print_runtime_log_sample "$runtime_log"
  write_runtime_status "$runtime_status" "success" "long_running_startup" 0 "$bytes_v" "$lines_v" "$max_same_v" "$max_consec_v" "$cpu_busy_samples"
  print_runtime_status_to_evaluation_log "$runtime_status"
  set -e
  return 0
}

detect_protocol() {
  if [[ -f "pom.xml" && -f "src/main/java/Main.java" ]]; then
    echo "java"
    return 0
  fi

  if [[ -f "requirements.txt" && -f "Main.py" ]]; then
    echo "python"
    return 0
  fi

  if [[ -f "CMakeLists.txt" && -f "src/Main.cpp" ]]; then
    echo "cpp"
    return 0
  fi

  echo "unknown"
}

validate_java_protocol() {
  test -f "pom.xml" || { echo "[error] Missing build file: pom.xml"; exit 1; }
  test -f "src/main/java/Main.java" || { echo "[error] Missing runtime entry: src/main/java/Main.java"; exit 1; }
  test -f "src/test/java/MainTest.java" || { echo "[error] Missing test target: src/test/java/MainTest.java"; exit 1; }
}

validate_python_protocol() {
  test -f "requirements.txt" || { echo "[error] Missing build file: requirements.txt"; exit 1; }
  test -f "Main.py" || { echo "[error] Missing runtime entry: Main.py"; exit 1; }
  test -f "tests/test_main.py" || { echo "[error] Missing test target: tests/test_main.py"; exit 1; }
}

validate_cpp_protocol() {
  test -f "CMakeLists.txt" || { echo "[error] Missing build file: CMakeLists.txt"; exit 1; }
  test -f "src/Main.cpp" || { echo "[error] Missing runtime entry: src/Main.cpp"; exit 1; }
  test -f "tests/test_main.cpp" || { echo "[error] Missing test target: tests/test_main.cpp"; exit 1; }
}

check_no_extra_java_tests() {
  local extra_tests
  extra_tests="$(find src/test/java -type f -name '*Test.java' ! -path 'src/test/java/MainTest.java' -print || true)"
  if [[ -n "$extra_tests" ]]; then
    echo "[error] Unexpected additional Java test files found:"
    echo "$extra_tests"
    exit 1
  fi
}

check_no_extra_python_tests() {
  local extra_tests
  extra_tests="$(find tests -type f -name 'test_*.py' ! -path 'tests/test_main.py' -print || true)"
  if [[ -n "$extra_tests" ]]; then
    echo "[error] Unexpected additional Python test files found:"
    echo "$extra_tests"
    exit 1
  fi
}

check_no_extra_cpp_tests() {
  local extra_tests
  extra_tests="$(find tests -type f \( -name '*Test.cpp' -o -name 'test_*.cpp' \) ! -path 'tests/test_main.cpp' -print || true)"
  if [[ -n "$extra_tests" ]]; then
    echo "[error] Unexpected additional C++ test files found:"
    echo "$extra_tests"
    exit 1
  fi
}

package_java_project() {
  echo ">>> Packaging Java project"
  run_build_with_timeout "mvn -q clean package -DskipTests ${EXTRA_MVN_ARGS}"

  local jar_candidates
  jar_candidates="$(find target -maxdepth 1 -type f -name '*.jar' ! -name '*sources.jar' ! -name '*javadoc.jar' -print || true)"
  if [[ -z "$jar_candidates" ]]; then
    echo "[error] No packaged jar found in target/ after successful packaging"
    exit 1
  fi

  echo ">>> Copy Java artifacts"
  while IFS= read -r jar; do
    [[ -n "$jar" ]] || continue
    cp "$jar" "$ARTIFACT_DIR/"
  done <<< "$jar_candidates"

  echo ">>> Java packaged artifacts:"
  ls -1 "$ARTIFACT_DIR"/*.jar
}

run_java_artifact_check() {
  echo ">>> Running Java project via Maven exec:java"
  run_artifact_smart_check \
    "mvn -q -DskipTests exec:java -Dexec.mainClass=Main ${EXTRA_MVN_ARGS} ${EXTRA_JAVA_RUN_ARGS}" \
    "java"
}

package_python_project() {
  echo ">>> Packaging Python project into zipapp"
  local project_name
  project_name="$(basename "$PROJECT_DIR")"
  local staging_dir
  staging_dir="$(mktemp -d)"

  mkdir -p "${staging_dir}/app"

  rsync -a \
    --exclude 'DTResults' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    ./ "${staging_dir}/app/"

  cat > "${staging_dir}/app/__main__.py" <<'EOF_MAIN'
import runpy
runpy.run_path("Main.py", run_name="__main__")
EOF_MAIN

  local pyz_path="${ARTIFACT_DIR}/${project_name}.pyz"
  python -m zipapp "${staging_dir}/app" -o "$pyz_path"

  if [[ ! -f "$pyz_path" ]]; then
    echo "[error] Failed to create Python zipapp artifact"
    exit 1
  fi

  echo ">>> Python packaged artifact:"
  ls -1 "$pyz_path"

  rm -rf "$staging_dir"
}

run_python_artifact_check() {
  local pyz
  pyz="$(find "$ARTIFACT_DIR" -maxdepth 1 -type f -name '*.pyz' | head -n 1 || true)"
  if [[ -z "$pyz" ]]; then
    echo "[error] No packaged Python artifact found for runtime check"
    exit 1
  fi

  run_artifact_smart_check \
    "PYTHONUNBUFFERED=1 python -u ${EXTRA_PYTHON_RUN_ARGS} '$pyz'" \
    "python"
}

package_cpp_project() {
  echo ">>> Packaging C++ runnable binary"

  local exe
  exe="$({
    find build -type f \
      -executable \
      ! -name 'CTestTestfile.cmake' \
      ! -name '*test*' \
      ! -name '*Test*' \
      ! -path '*/CMakeFiles/*' \
      -print | head -n 1 || true
  })"

  if [[ -z "$exe" ]]; then
    echo "[error] No runnable C++ executable found under build/"
    exit 1
  fi

  local project_name
  project_name="$(basename "$PROJECT_DIR")"
  cp "$exe" "${ARTIFACT_DIR}/${project_name}"
  chmod +x "${ARTIFACT_DIR}/${project_name}"

  echo ">>> C++ packaged artifact:"
  ls -l "${ARTIFACT_DIR}/${project_name}"
}

run_cpp_artifact_check() {
  local project_name
  project_name="$(basename "$PROJECT_DIR")"
  local exe="${ARTIFACT_DIR}/${project_name}"

  if [[ ! -x "$exe" ]]; then
    echo "[error] No packaged C++ executable found for runtime check: $exe"
    exit 1
  fi

  run_artifact_smart_check \
    "'$exe'" \
    "cpp"
}

run_java_project() {
  echo ">>> Protocol detected: JAVA"
  validate_java_protocol
  check_no_extra_java_tests

  echo ">>> Running Maven tests"
  run_test_with_timeout "mvn -q test ${EXTRA_MVN_ARGS}"

  package_java_project
  run_java_artifact_check
}

run_python_project() {
  echo ">>> Protocol detected: PYTHON"
  validate_python_protocol
  check_no_extra_python_tests

  echo ">>> Installing Python dependencies"
  run_install_with_timeout "python -m pip install --no-cache-dir -r requirements.txt ${EXTRA_PIP_ARGS}"

  echo ">>> Running pytest"
  run_test_with_timeout "PYTHONPATH=\"$(pwd):\${PYTHONPATH:-}\" python -m pytest ${EXTRA_PYTEST_ARGS}"

  package_python_project
  run_python_artifact_check
}

run_cpp_project() {
  echo ">>> Protocol detected: C++"
  validate_cpp_protocol
  check_no_extra_cpp_tests

  echo ">>> Configuring CMake project"
  if [[ -n "${CMAKE_GENERATOR}" ]]; then
    run_build_with_timeout "cmake -S . -B build -G '${CMAKE_GENERATOR}' -DCMAKE_BUILD_TYPE='${CMAKE_BUILD_TYPE}' ${EXTRA_CMAKE_ARGS}"
  else
    run_build_with_timeout "cmake -S . -B build -DCMAKE_BUILD_TYPE='${CMAKE_BUILD_TYPE}' ${EXTRA_CMAKE_ARGS}"
  fi

  echo ">>> Building C++ project"
  run_build_with_timeout "cmake --build build -j"

  echo ">>> Running CTest"
  run_test_with_timeout "ctest --test-dir build ${EXTRA_CTEST_ARGS}"

  package_cpp_project
  run_cpp_artifact_check
}

PROTO="$(detect_protocol)"
echo "[INFO] Detected protocol: ${PROTO}"

case "$PROTO" in
  java) run_java_project ;;
  python) run_python_project ;;
  cpp) run_cpp_project ;;
  *)
    echo "[error] Unknown project type or protocol files missing"
    exit 1
    ;;
esac

echo "[INFO] Evaluation, packaging, and smart runtime check finished successfully."
echo "[INFO] Packaged artifacts are stored in: ${ARTIFACT_DIR}"