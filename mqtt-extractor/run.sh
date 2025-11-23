#!/bin/bash
set -e

# Progress indicator: Initializing
echo "[Startup 5%] Initializing MQTT Extractor add-on..."

# Source bashio if available
if [ -f /usr/lib/bashio/bashio.sh ]; then
    . /usr/lib/bashio/bashio.sh
    echo "[Startup 10%] Home Assistant integration loaded"
fi

# Read configuration from Home Assistant options
CONFIG_FILE="/data/config.yaml"
echo "[Startup 15%] Configuration file: ${CONFIG_FILE}"

# Helper function to get config with default
get_config() {
    local key=$1
    local default=$2
    if command -v bashio::config >/dev/null 2>&1; then
        local value=$(bashio::config "${key}" 2>/dev/null || echo "")
    else
        local value=""
    fi
    if [ -z "${value}" ]; then
        echo "${default}"
    else
        echo "${value}"
    fi
}

# Progress indicator: Reading MQTT configuration
echo "[Startup 20%] Reading MQTT configuration..."

# Get MQTT configuration (with error handling)
if command -v bashio::config >/dev/null 2>&1; then
    MQTT_HOSTNAME=$(bashio::config 'mqtt_hostname' 2>/dev/null || echo "homeassistant.local")
    MQTT_PORT=$(bashio::config 'mqtt_port' 2>/dev/null || echo "1883")
else
    MQTT_HOSTNAME="homeassistant.local"
    MQTT_PORT="1883"
fi
MQTT_USERNAME=$(get_config 'mqtt_username' '')
MQTT_PASSWORD=$(get_config 'mqtt_password' '')
MQTT_CLIENT_ID=$(get_config 'mqtt_client_id' 'mqtt-extractor')
MQTT_CLEAN_SESSION=$(get_config 'mqtt_clean_session' 'false')
echo "[Startup 30%] MQTT configuration loaded: ${MQTT_HOSTNAME}:${MQTT_PORT}"

# Get MQTT topics (can be array or comma-separated string)
if command -v bashio::config >/dev/null 2>&1; then
    MQTT_TOPICS=$(bashio::config 'mqtt_topics' 2>/dev/null || echo '["*"]')
else
    MQTT_TOPICS='["*"]'
fi
MQTT_QOS=$(get_config 'mqtt_qos' '1')

# Progress indicator: Reading CDF configuration
echo "[Startup 40%] Reading CDF configuration..."

# Get CDF configuration (with error handling)
if command -v bashio::config >/dev/null 2>&1; then
    CDF_URL=$(bashio::config 'cdf_url' 2>/dev/null || echo "")
    CDF_PROJECT=$(bashio::config 'cdf_project' 2>/dev/null || echo "")
    IDP_CLIENT_ID=$(bashio::config 'idp_client_id' 2>/dev/null || echo "")
    IDP_TOKEN_URL=$(bashio::config 'idp_token_url' 2>/dev/null || echo "")
    IDP_CLIENT_SECRET=$(bashio::config 'idp_client_secret' 2>/dev/null || echo "")
    IDP_SCOPES=$(bashio::config 'idp_scopes' 2>/dev/null || echo "")
else
    CDF_URL=""
    CDF_PROJECT=""
    IDP_CLIENT_ID=""
    IDP_TOKEN_URL=""
    IDP_CLIENT_SECRET=""
    IDP_SCOPES=""
fi

# Get other configuration
UPLOAD_INTERVAL=$(get_config 'upload_interval' '1')
EXTERNAL_ID_PREFIX=$(get_config 'external_id_prefix' 'mqtt:')
CREATE_MISSING=$(get_config 'create_missing' 'true')
LOG_LEVEL=$(get_config 'log_level' 'INFO')

# Get data model configuration
ENABLE_DATA_MODEL=$(get_config 'enable_data_model' 'false')
INSTANCE_SPACE=$(get_config 'instance_space' '')
DATA_MODEL_SPACE=$(get_config 'data_model_space' 'sp_enterprise_schema_space')
DATA_MODEL_VERSION=$(get_config 'data_model_version' 'v1')
TIMESERIES_VIEW=$(get_config 'timeseries_view_external_id' 'haTimeSeries')
SOURCE_SYSTEM_SPACE=$(get_config 'source_system_space' 'cdf_cdm')
SOURCE_SYSTEM_VERSION=$(get_config 'source_system_version' 'v1')

# Create config.yaml from Home Assistant options
cat > "$CONFIG_FILE" <<EOF
version: 1

mqtt:
  hostname: ${MQTT_HOSTNAME}
  port: ${MQTT_PORT}
  username: ${MQTT_USERNAME}
  password: ${MQTT_PASSWORD}
  client_id: ${MQTT_CLIENT_ID}
  clean_session: ${MQTT_CLEAN_SESSION}

subscriptions:
EOF

# Process topics - handle both array format and comma-separated string
# Home Assistant passes arrays as JSON arrays, so we need to parse them
if echo "${MQTT_TOPICS}" | grep -q '^\['; then
    # Array format: ["topic1", "topic2"] or ["topic1","topic2"]
    # Extract topics using sed/awk, handling both formats
    echo "${MQTT_TOPICS}" | sed 's/\[//g' | sed 's/\]//g' | sed 's/"//g' | sed 's/,/\n/g' | while read -r topic; do
        topic=$(echo "${topic}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # Trim whitespace
        if [ -n "${topic}" ]; then
            # Use single quotes for wildcard characters to avoid YAML parsing issues
            if [ "${topic}" = "*" ] || [ "${topic}" = "+" ]; then
                # Use printf to write single-quoted wildcard to avoid YAML anchor issues
                printf "  - topic: '%s'\n" "${topic}" >> "$CONFIG_FILE"
                printf "    qos: %s\n" "${MQTT_QOS}" >> "$CONFIG_FILE"
                cat >> "$CONFIG_FILE" <<EOF
    handler:
      module: mqtt_extractor.simple
EOF
            else
                cat >> "$CONFIG_FILE" <<EOF
  - topic: "${topic}"
    qos: ${MQTT_QOS}
    handler:
      module: mqtt_extractor.simple
EOF
            fi
        fi
    done
else
    # Comma-separated or single topic (fallback for manual configuration)
    IFS=',' read -ra TOPIC_ARRAY <<< "${MQTT_TOPICS}"
    for topic in "${TOPIC_ARRAY[@]}"; do
        topic=$(echo "${topic}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # Trim whitespace
        if [ -n "${topic}" ]; then
            # Use single quotes for wildcard characters to avoid YAML parsing issues
            if [ "${topic}" = "*" ] || [ "${topic}" = "+" ]; then
                # Use printf to write single-quoted wildcard to avoid YAML anchor issues
                printf "  - topic: '%s'\n" "${topic}" >> "$CONFIG_FILE"
                printf "    qos: %s\n" "${MQTT_QOS}" >> "$CONFIG_FILE"
                cat >> "$CONFIG_FILE" <<EOF
    handler:
      module: mqtt_extractor.simple
EOF
            else
                cat >> "$CONFIG_FILE" <<EOF
  - topic: "${topic}"
    qos: ${MQTT_QOS}
    handler:
      module: mqtt_extractor.simple
EOF
            fi
        fi
    done
fi

# Add remaining configuration
cat >> "$CONFIG_FILE" <<EOF

upload-interval: ${UPLOAD_INTERVAL}
external-id-prefix: ${EXTERNAL_ID_PREFIX}
create-missing: ${CREATE_MISSING}

logger:
  console:
    level: ${LOG_LEVEL}

cognite:
  host: ${CDF_URL}
  project: ${CDF_PROJECT}
  idp-authentication:
    client-id: ${IDP_CLIENT_ID}
    token-url: ${IDP_TOKEN_URL}
    secret: ${IDP_CLIENT_SECRET}
    scopes:
      - ${IDP_SCOPES}
EOF

# Progress indicator: Adding data model configuration
echo "[Startup 70%] Configuring data model settings..."
# Add data model configuration if enabled
if [ "${ENABLE_DATA_MODEL}" = "true" ] && [ -n "${INSTANCE_SPACE}" ]; then
    cat >> "$CONFIG_FILE" <<EOF

target:
  instance-space: ${INSTANCE_SPACE}
  data-model-space: ${DATA_MODEL_SPACE}
  data-model-version: ${DATA_MODEL_VERSION}
  timeseries-view-external-id: ${TIMESERIES_VIEW}
  source-system-space: ${SOURCE_SYSTEM_SPACE}
  source-system-version: ${SOURCE_SYSTEM_VERSION}
EOF
    echo "[Startup 75%] Data model configuration added"
else
    echo "[Startup 75%] Data model disabled, skipping configuration"
fi

# Progress indicator: Finalizing configuration
echo "[Startup 80%] Finalizing configuration file..."

# Log configuration (without sensitive data)
if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "MQTT Extractor starting..."
    bashio::log.info "MQTT Broker: ${MQTT_HOSTNAME}:${MQTT_PORT}"
    bashio::log.info "Topics: ${MQTT_TOPICS}"
    bashio::log.info "CDF Project: ${CDF_PROJECT}"
    if [ "${ENABLE_DATA_MODEL}" = "true" ]; then
        bashio::log.info "Data Model: ENABLED (Instance Space: ${INSTANCE_SPACE})"
    else
        bashio::log.info "Data Model: DISABLED"
    fi
else
    echo "MQTT Extractor starting..."
    echo "MQTT Broker: ${MQTT_HOSTNAME}:${MQTT_PORT}"
    echo "Topics: ${MQTT_TOPICS}"
    echo "CDF Project: ${CDF_PROJECT}"
    if [ "${ENABLE_DATA_MODEL}" = "true" ]; then
        echo "Data Model: ENABLED (Instance Space: ${INSTANCE_SPACE})"
    else
        echo "Data Model: DISABLED"
    fi
fi

# Progress indicator: Starting extractor
echo "[Startup 90%] Starting MQTT Extractor..."
echo "[Startup 95%] Loading Python environment and dependencies..."

# Print version for verification
# Try environment variable first (set from BUILD_VERSION), then config.json, then unknown
if [ -n "${ADDON_VERSION}" ]; then
    VERSION="${ADDON_VERSION}"
elif [ -f "/app/config.json" ]; then
    VERSION=$(grep -o '"version": "[^"]*"' /app/config.json 2>/dev/null | cut -d'"' -f4 || echo "unknown")
else
    VERSION="unknown"
fi
echo "[Startup 97%] MQTT Extractor add-on version: ${VERSION}"
if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "MQTT Extractor add-on version: ${VERSION}"
fi

# Debug: Print first few lines of generated config (without sensitive data) for troubleshooting
if command -v bashio::log.debug >/dev/null 2>&1; then
    bashio::log.debug "Generated config preview (first 20 lines):"
    head -20 "$CONFIG_FILE" 2>/dev/null | sed 's/password:.*/password: [REDACTED]/' | while read line; do
        bashio::log.debug "$line"
    done
fi

echo "[Startup 100%] MQTT Extractor add-on started successfully!"

# Run the extractor (use python3 from venv which is in PATH)
exec python3 /app/extractor.py "$CONFIG_FILE"

