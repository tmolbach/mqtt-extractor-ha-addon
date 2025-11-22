#!/bin/bash
set -e

# Source bashio if available
if [ -f /usr/lib/bashio/bashio.sh ]; then
    . /usr/lib/bashio/bashio.sh
fi

# Read configuration from Home Assistant options (with fallback)
MESSAGE=$(bashio::config 'message' 2>/dev/null || echo "Hello World from Home Assistant!")

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

# Keep the container running and print message every 10 seconds
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${MESSAGE}"
    sleep 10
done

