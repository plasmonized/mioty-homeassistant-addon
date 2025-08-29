# BSSCI mioty Home Assistant Add-on Dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Environment variables
ENV LANG C.UTF-8

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    gcc \
    musl-dev \
    linux-headers \
    curl \
    jq

# Set work directory
WORKDIR /data

# Copy Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./
COPY run.sh ./
RUN chmod a+x run.sh

# Labels
LABEL \
    io.hass.name="BSSCI mioty Sensor Manager" \
    io.hass.description="Verwaltet mioty IoT Sensoren über das BSSCI Service Center" \
    io.hass.arch="armhf|aarch64|amd64|armv7|i386" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

# Run
CMD ["./run.sh"]