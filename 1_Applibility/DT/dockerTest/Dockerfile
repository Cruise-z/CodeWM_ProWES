# Base image: Maven 3.9.x + Eclipse Temurin JDK 11 (can be switched to 17/21)
FROM maven:3.9.6-eclipse-temurin-11

# Workspace and local Maven repository cache path
ENV WORKDIR=/workspace \
    MAVEN_OPTS="-Dmaven.repo.local=/workspace/.m2" \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    DISPLAY=":99" \
    XVFB_ARGS="-screen 0 1280x800x24 -nolisten tcp -dpi 96"

# Common utilities + Xvfb + font/audio libraries (including x11-utils for readiness checks)
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

# Configure UTF-8 locale
RUN sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Workspace and Maven cache directories
RUN mkdir -p $WORKDIR $WORKDIR/.m2
WORKDIR $WORKDIR

# Copy and enable the entrypoint script (avoids heredoc compatibility issues)
COPY xvfb-entrypoint.sh /usr/local/bin/xvfb-entrypoint.sh
RUN chmod +x /usr/local/bin/xvfb-entrypoint.sh

# Health check: ensure the virtual display is available
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || exit 1

# Entrypoint: start Xvfb, wait until ready, then run the provided command
ENTRYPOINT ["/usr/local/bin/xvfb-entrypoint.sh"]

# Default to an interactive shell; append your command after podman/docker run if needed
CMD ["bash"]
