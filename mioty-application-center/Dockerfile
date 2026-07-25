# mioty Application Center für Homeassistant Add-on Dockerfile
ARG BUILD_ARCH=amd64
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base:3.19

ARG BUILD_ARCH
ARG TEMPIO_VERSION=2021.09.0

# OCI / HA Labels
LABEL \
    io.hass.name="mioty Application Center für Homeassistant" \
    io.hass.description="mioty Application Center für die Verwaltung von mioty IoT Sensoren" \
    io.hass.arch="armhf|aarch64|amd64|armv7|i386" \
    io.hass.type="addon" \
    io.hass.version="1.0.6.3" \
    org.opencontainers.image.title="mioty Application Center für Homeassistant" \
    org.opencontainers.image.description="mioty Application Center für die Verwaltung von mioty IoT Sensoren" \
    org.opencontainers.image.source="https://github.com/plasmonized/mioty-homeassistant-addon" \
    org.opencontainers.image.licenses="MIT"

# Environment variables
ENV LANG=C.UTF-8

# Install Python, Node.js and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    gcc \
    musl-dev \
    linux-headers \
    curl \
    jq \
    nodejs \
    npm

# Copy Python requirements
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Copy application files
COPY app/ /opt/
COPY run.sh /
RUN chmod a+x /run.sh

# Set work directory
WORKDIR /opt

# Run
CMD ["/run.sh"]
