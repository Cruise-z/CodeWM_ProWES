# 基础：Maven 3.9.x + Eclipse Temurin JDK 11（可换 17/21）
FROM maven:3.9.6-eclipse-temurin-11

# 工作区 & Maven 本地仓库缓存位置
ENV WORKDIR=/workspace \
    MAVEN_OPTS="-Dmaven.repo.local=/workspace/.m2" \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    DISPLAY=":99" \
    XVFB_ARGS="-screen 0 1280x800x24 -nolisten tcp -dpi 96"

# 常用基础工具 + Xvfb + 字体/音频库（含 x11-utils 供就绪检测）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata locales \
    curl wget git nano vim less tree unzip zip \
    xz-utils tar binutils \
    xvfb xauth x11-apps x11-utils \
    libgtk-3-0 libasound2 fonts-dejavu \
    libxtst6 libxrender1 libxext6 libxi6 libxrandr2 libgl1 \
    gstreamer1.0-tools gstreamer1.0-libav \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
 && rm -rf /var/lib/apt/lists/*

# 设定 UTF-8 本地化
RUN sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# 工作区与 Maven 缓存目录
RUN mkdir -p $WORKDIR $WORKDIR/.m2
WORKDIR $WORKDIR

# 拷入并启用入口脚本（避免 heredoc 兼容性坑）
COPY xvfb-entrypoint.sh /usr/local/bin/xvfb-entrypoint.sh
RUN chmod +x /usr/local/bin/xvfb-entrypoint.sh

# 健康检查：确保虚拟显示可用
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || exit 1

# 入口：先起 Xvfb 并等待就绪，再执行传入命令
ENTRYPOINT ["/usr/local/bin/xvfb-entrypoint.sh"]

# 默认进入交互 shell；在 podman/docker run 后追加你的命令即可
CMD ["bash"]
