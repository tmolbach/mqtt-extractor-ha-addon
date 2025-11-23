ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Progress indicator: Installing dependencies
RUN echo "[10%] Installing system dependencies..." && \
    apk add --no-cache bash && \
    echo "[30%] System dependencies installed successfully"

# Progress indicator: Copying files
RUN echo "[40%] Copying add-on files..."
COPY run.sh /run.sh
RUN chmod +x /run.sh && \
    echo "[60%] Add-on files copied and configured"

# Progress indicator: Finalizing
RUN echo "[80%] Finalizing add-on setup..." && \
    echo "[100%] Hello World add-on build complete!"

# Set entrypoint
ENTRYPOINT ["/run.sh"]

