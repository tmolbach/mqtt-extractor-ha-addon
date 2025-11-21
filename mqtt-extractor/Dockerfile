ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install Python, pip, and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev \
    bash \
    curl \
    jq

# Install bashio (Home Assistant add-on helper)
RUN curl -L -f -s "https://github.com/hassio-addons/bashio/archive/v0.14.3.tar.gz" | tar -xzf - \
    && mv bashio-* bashio \
    && cd bashio \
    && mkdir -p /usr/lib/bashio \
    && mv lib/* /usr/lib/bashio/ \
    && cd .. \
    && rm -rf bashio

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies in virtual environment
COPY requirements.txt .
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Add venv to PATH
ENV PATH="/app/venv/bin:$PATH"

# Copy application code
COPY extractor.py .
COPY mqtt_extractor ./mqtt_extractor

# Copy entrypoint script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Set entrypoint (use sh to ensure proper execution)
ENTRYPOINT ["/run.sh"]

