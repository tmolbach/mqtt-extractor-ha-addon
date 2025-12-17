ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip bash

# Create app directory
WORKDIR /app

# Create virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY alarm_extractor/ ./alarm_extractor/
COPY run.sh /run.sh

# Make run script executable
RUN chmod a+x /run.sh

# Set entrypoint (use ENTRYPOINT not CMD for HA add-ons)
ENTRYPOINT ["/run.sh"]

