# 基础：Maven 3.9.x + Eclipse Temurin JDK 11
FROM maven:3.9.6-eclipse-temurin-11

# 工作区与通用环境变量
ENV WORKDIR=/workspace \
    MAVEN_OPTS="-Dmaven.repo.local=/workspace/.m2" \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    DISPLAY=":99" \
    XVFB_ARGS="-screen 0 1280x800x24 -nolisten tcp -dpi 96" \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    CC=/usr/bin/gcc \
    CXX=/usr/bin/g++ \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# 基础工具 + Xvfb + Java GUI 常见依赖 + C/C++ 构建链 + SFML + SDL2 + Python
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.ustc.edu.cn/ubuntu|g' /etc/apt/sources.list || true && \
    sed -i 's|http://security.ubuntu.com/ubuntu|https://mirrors.ustc.edu.cn/ubuntu|g' /etc/apt/sources.list || true && \
    apt-get -o Acquire::Retries=5 update && \
    apt-get -o Acquire::Retries=5 \
            -o Acquire::http::No-Cache=true \
            -o Acquire::http::No-Store=true \
            install -y --no-install-recommends \
            ca-certificates tzdata locales \
            curl wget git nano vim less tree unzip zip rsync \
            xz-utils tar binutils file \
            xvfb xauth x11-apps x11-utils \
            libgtk-3-0 libasound2 fonts-dejavu fontconfig \
            libxtst6 libxrender1 libxext6 libxi6 libxrandr2 libgl1 \
            gstreamer1.0-tools gstreamer1.0-libav \
            gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
            build-essential cmake ninja-build pkg-config gdb \
            libsfml-dev libsdl2-dev \
            libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
            libfreetype6-dev libjpeg-dev libpng-dev libportmidi-dev \
            python3 python3-venv python3-pip python3-dev python-is-python3 && \
    rm -rf /var/lib/apt/lists/*

# 设定 UTF-8 本地化
RUN sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen

# 预装 Python 测试工具，避免项目未声明 pytest 时评测失败
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel pytest

# 工作区与 Maven 缓存目录
RUN mkdir -p "$WORKDIR" "$WORKDIR/.m2"
WORKDIR $WORKDIR

# 拷入脚本
COPY xvfb-entrypoint.sh /usr/local/bin/xvfb-entrypoint.sh
COPY eval_protocol.sh /usr/local/bin/eval_protocol.sh

RUN chmod +x /usr/local/bin/xvfb-entrypoint.sh /usr/local/bin/eval_protocol.sh

# 健康检查：确保虚拟显示可用
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || exit 1

# 入口：先起 Xvfb 并等待就绪，再执行传入命令
ENTRYPOINT ["/usr/local/bin/xvfb-entrypoint.sh"]

# 默认bash，方便调试和交互式使用；实际评测时会覆盖为 evaluate_project.sh
CMD ["bash"]