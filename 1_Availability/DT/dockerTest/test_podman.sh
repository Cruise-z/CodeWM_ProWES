#!/usr/bin/env bash
set -euo pipefail

# ====== 可调参数 ======
CTR_NAME=${CTR_NAME:-CodeWM-DT}     # 你的长期运行容器名
WORKDIR=/workspace                  # 容器工作区
EXTRA_MVN_ARGS=${EXTRA_MVN_ARGS:-"-Djavafx.platform=linux"}  # OpenJFX 平台 classifier，可按需置空
EXTRA_JAVA_ARGS=${EXTRA_JAVA_ARGS:-""}   # 额外 JVM 参数(如 -Xmx512m). 不要加 -Djava.awt.headless=true

# 统一超时策略：若两分钟仍未退出，则强制结束并视为“成功”
TIME_LIMIT=${TIME_LIMIT:-120}       # 秒
KILL_AFTER=${KILL_AFTER:-5}         # 超时后再等多少秒发送 SIGKILL
# 说明：timeout 退出码 124 表示超时，这里把 124 当作 0（成功）

# ====== 宿主机代理 ======
HOST_HTTP_PROXY=${HTTP_PROXY:-}
HOST_HTTPS_PROXY=${HTTPS_PROXY:-}

# ====== 参数检查 ======
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 </path/to/File.java>"
  exit 1
fi

JAVA_FILE_PATH="$1"
if [[ ! -f "$JAVA_FILE_PATH" ]]; then
  echo "Java file not found: $JAVA_FILE_PATH"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$JAVA_FILE_PATH")" && pwd)"
BASE_JAVA_FILE="$(basename "$JAVA_FILE_PATH")"

if [[ ! -f "$PROJECT_DIR/pom.xml" ]]; then
  echo "pom.xml not found in: $PROJECT_DIR"
  exit 1
fi

# 容器是否在运行
if ! podman ps --format '{{.Names}}' | grep -q "^${CTR_NAME}$"; then
  echo "Container ${CTR_NAME} is not running."
  echo "Start it first (e.g. podman run -d --name ${CTR_NAME} codewm_dt_docker:11 sleep infinity)"
  exit 1
fi

# 确认容器里的 Xvfb 已就绪（需要镜像里有 xdpyinfo）
if ! podman exec "$CTR_NAME" sh -lc 'xdpyinfo -display "${DISPLAY:-:99}" >/dev/null 2>&1'; then
  echo "Xvfb is not ready inside container '${CTR_NAME}'."
  echo "Ensure you started it from the image with xvfb-entrypoint (codewm_dt_docker:11),"
  echo "e.g. podman run -d --name ${CTR_NAME} codewm_dt_docker:11 sleep infinity"
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
IN_CTR_DIR="${WORKDIR}/proj_${STAMP}"

# ====== 统一日志与产物目录（都放在 .java 同目录下）======
OUTPUT_DIR="${PROJECT_DIR}/DTResults"
OUT_DIR="${OUTPUT_DIR}/out_${STAMP}"
mkdir -p "$OUTPUT_DIR" "$OUT_DIR"

# 单一日志文件（所有阶段合并在一起）
LOG="${OUT_DIR}/full_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

echo "===== BEGIN @ ${STAMP} ====="
echo "[INFO] Project dir:     $PROJECT_DIR"
echo "[INFO] Java file:       $JAVA_FILE_PATH"
echo "[INFO] Container name:  $CTR_NAME"
echo "[INFO] In-container dir:$IN_CTR_DIR"
echo "[INFO] Output dir:      $OUT_DIR"
echo "[INFO] Log file:        $LOG"
echo "[INFO] Time limit:      ${TIME_LIMIT}s (kill-after ${KILL_AFTER}s)"
echo

# ====== Copy project into container =======
echo ">>> Copy project into container: $PROJECT_DIR -> ${CTR_NAME}:${IN_CTR_DIR}"
podman exec \
  -e HTTP_PROXY="$HOST_HTTP_PROXY" \
  -e HTTPS_PROXY="$HOST_HTTPS_PROXY" \
  "$CTR_NAME" bash -lc "mkdir -p '$IN_CTR_DIR'"
podman cp "$PROJECT_DIR/." "$CTR_NAME:$IN_CTR_DIR/"

# ====== 写入 Maven 代理配置（按需修改/去掉） =======
echo ">>> Write Maven proxy config to container"
podman exec "$CTR_NAME" bash -lc '
  mkdir -p /root/.m2
  cat > /root/.m2/settings.xml <<EOF
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              https://maven.apache.org/xsd/settings-1.0.0.xsd">
  <proxies>
    <proxy>
      <id>proxy-https</id>
      <active>true</active>
      <protocol>https</protocol>
      <host>192.168.129.183</host>
      <port>7897</port>
    </proxy>
    <proxy>
      <id>proxy-http</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>192.168.129.183</host>
      <port>7897</port>
    </proxy>
  </proxies>
</settings>
EOF
'

# ====== Normalize source layout =======
echo ">>> Normalize source layout (src/main/java)"
podman exec \
  -e IN_CTR_DIR="$IN_CTR_DIR" \
  -e BASE_JAVA_FILE="$BASE_JAVA_FILE" \
  "$CTR_NAME" bash -lc '
    set -e
    cd "$IN_CTR_DIR"
    SRC_ROOT="src/main/java"
    if [[ ! -d "$SRC_ROOT" ]]; then
      mkdir -p "$SRC_ROOT"
    fi

    FOUND_FILE="$(find . -maxdepth 1 -type f -name "$BASE_JAVA_FILE" -print -quit || true)"
    if [[ -n "$FOUND_FILE" ]]; then
      PKG="$(grep -E "^[[:space:]]*package[[:space:]]+" "$FOUND_FILE" 2>/dev/null | sed -E "s/^[[:space:]]*package[[:space:]]+([^;]+);.*/\1/" | tr -d "\r\n" || true)"
      if [[ -n "$PKG" ]]; then
        DEST_DIR="$SRC_ROOT/$(echo "$PKG" | tr "." "/")"
      else
        DEST_DIR="$SRC_ROOT"
      fi
      mkdir -p "$DEST_DIR"
      mv "$FOUND_FILE" "$DEST_DIR/"
    fi
  '

# ====== Resolve deps & package via pom.xml =======
echo ">>> Resolve deps & package via pom.xml"
podman exec \
  -e HTTP_PROXY="$HOST_HTTP_PROXY" \
  -e HTTPS_PROXY="$HOST_HTTPS_PROXY" \
  "$CTR_NAME" bash -lc "
    set -e
    cd '$IN_CTR_DIR'
    echo '=== Checking Maven proxy ==='
    mvn -q help:effective-settings | grep proxy -A 5 || true
    echo '=== Start dependency resolution ==='
    mvn -q -B \$MAVEN_OPTS dependency:go-offline ${EXTRA_MVN_ARGS}
    mvn -q -B \$MAVEN_OPTS -DskipTests package ${EXTRA_MVN_ARGS}
    mvn -q -B \$MAVEN_OPTS dependency:copy-dependencies -DoutputDirectory=target/dependency ${EXTRA_MVN_ARGS} || true
"

# ====== Find executable JAR =======
JAR_PATH="$(podman exec "$CTR_NAME" bash -lc "
  cd '$IN_CTR_DIR'
  CAND=\$(ls target/*-with-dependencies.jar 2>/dev/null | head -n1)
  if [[ -z \"\$CAND\" ]]; then CAND=\$(ls target/*.jar 2>/dev/null | head -n1); fi
  echo -n \"\$CAND\"
")"

# ====== Determine main class =======
CLASS_NAME="$(basename "$BASE_JAVA_FILE" .java)"
PKG_NAME="$(grep -E '^\s*package\s+' "$JAVA_FILE_PATH" 2>/dev/null | sed -E 's/^\s*package\s+([^;]+);.*/\1/' | tr -d '\r\n' | xargs || true)"
if [[ -n "$PKG_NAME" ]]; then
  MAIN_CLASS="${PKG_NAME}.${CLASS_NAME}"
else
  MAIN_CLASS="$CLASS_NAME"
fi

HAS_JAVAFX="$(podman exec "$CTR_NAME" bash -lc "
  cd '$IN_CTR_DIR'
  ls target/dependency/javafx-*.jar >/dev/null 2>&1 && echo yes || true
")"

# ====== helper: 执行 podman exec + timeout，并把 124 当作成功 ======
run_with_timeout() {
  # $1: container name
  # $2: command (string) — 在容器 bash -lc 中执行
  local _ctr="$1"
  local _cmd="$2"
  set +e
  podman exec \
    -e IN_CTR_DIR="$IN_CTR_DIR" \
    -e MAIN_CLASS="$MAIN_CLASS" \
    -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
    -e TIME_LIMIT="$TIME_LIMIT" \
    -e KILL_AFTER="$KILL_AFTER" \
    "$_ctr" bash -lc "$_cmd"
  local rc=$?
  set -e
  if [[ $rc -eq 124 ]]; then
    echo "[INFO] Reached TIMEOUT (${TIME_LIMIT}s). Force-stopped the app and treating as SUCCESS."
    return 0
  fi
  return $rc
}

# ====== Run =======
echo ">>> Run"
if [[ -n "$JAR_PATH" ]]; then
  echo "[INFO] Found JAR: $JAR_PATH"
  if ! run_with_timeout "$CTR_NAME" '
      set -e
      cd "$IN_CTR_DIR"
      echo "Running JAR with timeout ${TIME_LIMIT}s: $JAR_PATH"
      timeout --signal=TERM --kill-after=${KILL_AFTER}s ${TIME_LIMIT}s \
        java $EXTRA_JAVA_ARGS -jar "$JAR_PATH"
    '; then
    echo ">>> java -jar failed (non-timeout). Falling back to classpath/module-path..."
    if [[ -n "$HAS_JAVAFX" ]]; then
      run_with_timeout "$CTR_NAME" '
        set -e
        cd "$IN_CTR_DIR"
        echo "Running main (JavaFX, module-path) with timeout ${TIME_LIMIT}s: $MAIN_CLASS"
        timeout --signal=TERM --kill-after=${KILL_AFTER}s ${TIME_LIMIT}s \
          java $EXTRA_JAVA_ARGS \
            --module-path target/dependency \
            --add-modules javafx.controls,javafx.media,javafx.swing \
            -cp target/classes \
            "$MAIN_CLASS"
      '
    else
      run_with_timeout "$CTR_NAME" '
        set -e
        cd "$IN_CTR_DIR"
        echo "Running main (classpath) with timeout ${TIME_LIMIT}s: $MAIN_CLASS"
        timeout --signal=TERM --kill-after=${KILL_AFTER}s ${TIME_LIMIT}s \
          java $EXTRA_JAVA_ARGS -cp "target/classes:target/dependency/*" "$MAIN_CLASS"
      '
    fi
  fi
else
  echo "[INFO] No JAR produced; running classes directly."
  if [[ -n "$HAS_JAVAFX" ]]; then
    run_with_timeout "$CTR_NAME" '
      set -e
      cd "$IN_CTR_DIR"
      echo "Running main (JavaFX, module-path) with timeout ${TIME_LIMIT}s: $MAIN_CLASS"
      timeout --signal=TERM --kill-after=${KILL_AFTER}s ${TIME_LIMIT}s \
        java $EXTRA_JAVA_ARGS \
          --module-path target/dependency \
          --add-modules javafx.controls,javafx.media,javafx.swing \
          -cp target/classes \
          "$MAIN_CLASS"
    '
  else
    run_with_timeout "$CTR_NAME" '
      set -e
      cd "$IN_CTR_DIR"
      echo "Running main (classpath) with timeout ${TIME_LIMIT}s: $MAIN_CLASS"
      timeout --signal=TERM --kill-after=${KILL_AFTER}s ${TIME_LIMIT}s \
        java $EXTRA_JAVA_ARGS -cp "target/classes:target/dependency/*" "$MAIN_CLASS"
    '
  fi
fi

# ====== Collect artifacts =======
echo ">>> Collect artifacts"
podman cp "$CTR_NAME:$IN_CTR_DIR/target" "$OUT_DIR/target" 2>/dev/null || true

echo "===== DONE ====="
echo "Artifacts in: $OUT_DIR"
echo "Unified log : $LOG"
