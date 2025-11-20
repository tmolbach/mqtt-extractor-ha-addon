ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install Python and pip
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY extractor.py .
COPY mqtt_extractor ./mqtt_extractor

# Copy entrypoint script
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Set entrypoint
ENTRYPOINT ["/run.sh"]

