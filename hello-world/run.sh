#!/bin/bash
set -e

# Progress indicator: Initializing
echo "[Startup 10%] Initializing Hello World add-on..."

# Source bashio if available
if [ -f /usr/lib/bashio/bashio.sh ]; then
    . /usr/lib/bashio/bashio.sh
    echo "[Startup 30%] Home Assistant integration loaded"
fi

# Progress indicator: Reading configuration
echo "[Startup 50%] Reading configuration..."
MESSAGE=$(bashio::config 'message' 2>/dev/null || echo "Hello World from Home Assistant!")
echo "[Startup 70%] Configuration loaded: message='${MESSAGE}'"

# Progress indicator: Starting service
echo "[Startup 90%] Starting Hello World service..."

# Log the message
if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "=========================================="
    bashio::log.info "${MESSAGE}"
    bashio::log.info "Add-on is running successfully!"
    bashio::log.info "=========================================="
else
    echo "=========================================="
    echo "${MESSAGE}"
    echo "Add-on is running successfully!"
    echo "=========================================="
fi

echo "[Startup 100%] Hello World add-on started successfully!"

# Keep the container running and print message every 10 seconds
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${MESSAGE}"
    sleep 10
done

