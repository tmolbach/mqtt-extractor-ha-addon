#!/usr/bin/with-contenv bashio
set -e

# Read configuration from Home Assistant options
MESSAGE=$(bashio::config 'message' 'Hello World from Home Assistant!')

# Log the message
bashio::log.info "=========================================="
bashio::log.info "${MESSAGE}"
bashio::log.info "Add-on is running successfully!"
bashio::log.info "=========================================="

# Keep the container running and print message every 10 seconds
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${MESSAGE}"
    sleep 10
done

