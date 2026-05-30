#!/usr/bin/env bash
set -euo pipefail

# ====== 可调参数 ======
CTR_NAME=${CTR_NAME:-CodeWM-DT}     # 你的长期运行容器名
WORKDIR=/workspace                  # 容器工作区
EXTRA_MVN_ARGS=${EXTRA_MVN_ARGS:-"-Djavafx.platform=linux"}  # OpenJFX 平台 classifier，可按需置空
EXTRA_JAVA_ARGS=${EXTRA_JAVA_ARGS:-""}   # 额外 JVM 参数（如 -Xmx512m）

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
if ! docker ps --format '{{.Names}}' | grep -q "^${CTR_NAME}$"; then
  echo "Container ${CTR_NAME} is not running."
  echo "Start it first (e.g. docker run -d --name ${CTR_NAME} maven-only:11)"
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
# 全局重定向：stdout + stderr -> 同时写到屏幕与 LOG
# 若宿主 bash 支持进程替换（大多数 Linux 均支持），这就是最简方案：
exec > >(tee -a "$LOG") 2>&1

echo "===== BEGIN @ ${STAMP} ====="
echo "[INFO] Project dir:     $PROJECT_DIR"
echo "[INFO] Java file:       $JAVA_FILE_PATH"
echo "[INFO] Container name:  $CTR_NAME"
echo "[INFO] In-container dir:$IN_CTR_DIR"
echo "[INFO] Output dir:      $OUT_DIR"
echo "[INFO] Log file:        $LOG"
echo

echo ">>> Copy project into container: $PROJECT_DIR -> ${CTR_NAME}:${IN_CTR_DIR}"
docker exec "$CTR_NAME" bash -lc "mkdir -p '$IN_CTR_DIR'"
docker cp "$PROJECT_DIR/." "$CTR_NAME:$IN_CTR_DIR/"

# 规范化源码布局（把单文件移到 src/main/java/<package>/）
echo ">>> Normalize source layout (src/main/java)"
docker exec \
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

echo ">>> Resolve deps & package via pom.xml"
docker exec "$CTR_NAME" bash -lc "
  set -e
  cd '$IN_CTR_DIR'
  mvn -q -B \$MAVEN_OPTS dependency:go-offline ${EXTRA_MVN_ARGS}
  mvn -q -B \$MAVEN_OPTS -DskipTests package ${EXTRA_MVN_ARGS}
  mvn -q -B \$MAVEN_OPTS dependency:copy-dependencies -DoutputDirectory=target/dependency ${EXTRA_MVN_ARGS} || true
"

# 寻找可执行 JAR
JAR_PATH="$(docker exec "$CTR_NAME" bash -lc "
  cd '$IN_CTR_DIR'
  CAND=\$(ls target/*-with-dependencies.jar 2>/dev/null | head -n1)
  if [[ -z \"\$CAND\" ]]; then CAND=\$(ls target/*.jar 2>/dev/null | head -n1); fi
  echo -n \"\$CAND\"
")"

# 判断 JAR 是否带 Main-Class
HAS_EXECUTABLE_JAR=""
if [[ -n "$JAR_PATH" ]]; then
  HAS_EXECUTABLE_JAR="$(docker exec "$CTR_NAME" bash -lc "
    set -e
    cd '$IN_CTR_DIR'
    if [[ -f '$JAR_PATH' ]] && jar tf '$JAR_PATH' 2>/dev/null | grep -q '^META-INF/MANIFEST.MF$'; then
      jar xf '$JAR_PATH' META-INF/MANIFEST.MF 2>/dev/null || true
      if [[ -f META-INF/MANIFEST.MF ]]; then
        grep -iq '^Main-Class:' META-INF/MANIFEST.MF && echo yes || true
        rm -f META-INF/MANIFEST.MF
      fi
    fi
  ")"
fi

# 从源文件推导主类（package + 类名）
CLASS_NAME="$(basename "$BASE_JAVA_FILE" .java)"
PKG_NAME="$(grep -E '^\s*package\s+' "$JAVA_FILE_PATH" 2>/dev/null | sed -E 's/^\s*package\s+([^;]+);.*/\1/' | tr -d '\r\n' | xargs || true)"
if [[ -n "$PKG_NAME" ]]; then
  MAIN_CLASS="${PKG_NAME}.${CLASS_NAME}"
else
  MAIN_CLASS="$CLASS_NAME"
fi

# 检测 JavaFX 依赖（决定 module-path 与 add-modules）
HAS_JAVAFX="$(docker exec "$CTR_NAME" bash -lc "
  cd '$IN_CTR_DIR'
  ls target/dependency/javafx-*.jar >/dev/null 2>&1 && echo yes || true
")"

echo ">>> Run"
if [[ -n "$HAS_EXECUTABLE_JAR" ]]; then
  # 先尝试 java -jar
  set +e
  docker exec \
    -e IN_CTR_DIR="$IN_CTR_DIR" \
    -e JAR_PATH="$JAR_PATH" \
    -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
    "$CTR_NAME" bash -lc '
      set -e
      cd "$IN_CTR_DIR"
      echo "Running JAR: $JAR_PATH"
      java $EXTRA_JAVA_ARGS -jar "$JAR_PATH"
    '
  JAR_RC=$?
  set -e

  if [[ $JAR_RC -ne 0 ]]; then
    echo ">>> java -jar failed (rc=$JAR_RC). Falling back to classpath/module-path..."
    if [[ -n "$HAS_JAVAFX" ]]; then
      docker exec \
        -e IN_CTR_DIR="$IN_CTR_DIR" \
        -e MAIN_CLASS="$MAIN_CLASS" \
        -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
        "$CTR_NAME" bash -lc '
          set -e
          cd "$IN_CTR_DIR"
          echo "Running main (JavaFX, module-path): $MAIN_CLASS"
          java $EXTRA_JAVA_ARGS \
            --module-path target/dependency \
            --add-modules javafx.controls,javafx.media,javafx.swing \
            -cp target/classes \
            "$MAIN_CLASS"
        '
    else
      docker exec \
        -e IN_CTR_DIR="$IN_CTR_DIR" \
        -e MAIN_CLASS="$MAIN_CLASS" \
        -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
        "$CTR_NAME" bash -lc '
          set -e
          cd "$IN_CTR_DIR"
          echo "Running main (classpath): $MAIN_CLASS"
          java $EXTRA_JAVA_ARGS -cp "target/classes:target/dependency/*" "$MAIN_CLASS"
        '
    fi
  fi

else
  # 没有可执行 JAR：直接按源码主类运行
  if [[ -n "$HAS_JAVAFX" ]]; then
    docker exec \
      -e IN_CTR_DIR="$IN_CTR_DIR" \
      -e MAIN_CLASS="$MAIN_CLASS" \
      -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
      "$CTR_NAME" bash -lc '
        set -e
        cd "$IN_CTR_DIR"
        echo "Running main (JavaFX, module-path): $MAIN_CLASS"
        java $EXTRA_JAVA_ARGS \
          --module-path target/dependency \
          --add-modules javafx.controls,javafx.media,javafx.swing \
          -cp target/classes \
          "$MAIN_CLASS"
      '
  else
    docker exec \
      -e IN_CTR_DIR="$IN_CTR_DIR" \
      -e MAIN_CLASS="$MAIN_CLASS" \
      -e EXTRA_JAVA_ARGS="$EXTRA_JAVA_ARGS" \
      "$CTR_NAME" bash -lc '
        set -e
        cd "$IN_CTR_DIR"
        echo "Running main (classpath): $MAIN_CLASS"
        java $EXTRA_JAVA_ARGS -cp "target/classes:target/dependency/*" "$MAIN_CLASS"
      '
  fi
fi

# 回收产物（target 保持原样拷回），日志已统一在 $LOG
echo ">>> Collect artifacts"
docker cp "$CTR_NAME:$IN_CTR_DIR/target" "$OUT_DIR/target" 2>/dev/null || true

echo "===== DONE ====="
echo "Artifacts in: $OUT_DIR"
echo "Unified log : $LOG"
