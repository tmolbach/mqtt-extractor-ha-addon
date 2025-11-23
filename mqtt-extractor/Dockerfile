ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
ARG BUILD_VERSION
FROM ${BUILD_FROM}

# Progress indicator: Installing system dependencies
RUN echo "[5%] Installing system dependencies..." && \
    apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev \
    bash && \
    echo "[15%] System dependencies installed successfully"

# Set working directory
WORKDIR /app

# Progress indicator: Setting up Python environment
RUN echo "[20%] Setting up Python virtual environment..."
COPY requirements.txt .
RUN echo "[25%] Installing Python dependencies (this may take a few minutes)..." && \
    python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    echo "[50%] Python dependencies installed successfully"

# Add venv to PATH and set version
ENV PATH="/app/venv/bin:$PATH"
ENV ADDON_VERSION="${BUILD_VERSION}"

# Progress indicator: Copying application code
RUN echo "[60%] Copying application code..."
COPY extractor.py .
COPY mqtt_extractor ./mqtt_extractor
COPY config.json /app/config.json
RUN echo "[75%] Application code copied successfully"

# Progress indicator: Setting up entrypoint
RUN echo "[85%] Configuring entrypoint script..."
COPY run.sh /run.sh
RUN chmod a+x /run.sh && \
    echo "[95%] Entrypoint configured successfully" && \
    echo "[100%] MQTT Extractor add-on build complete!"

# Set entrypoint (use sh to ensure proper execution)
ENTRYPOINT ["/run.sh"]

