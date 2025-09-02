# mioty Application Center für Homeassistant Add-on Dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Environment variables
ENV LANG=C.UTF-8

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

# Copy Python requirements
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Copy application files
COPY app/ /opt/
COPY run.sh /
RUN chmod a+x /run.sh

# Force cache bust for templates (version 1.0.4.5)
RUN echo "Template update: 1.0.4.5" > /opt/version.txt

# Set work directory
WORKDIR /opt

# Labels
LABEL \
    io.hass.name="mioty Application Center für Homeassistant" \
    io.hass.description="mioty Application Center für die Verwaltung von mioty IoT Sensoren" \
    io.hass.arch="armhf|aarch64|amd64|armv7|i386" \
    io.hass.type="addon" \
    io.hass.version="1.0.1"

# Run
CMD ["/run.sh"]