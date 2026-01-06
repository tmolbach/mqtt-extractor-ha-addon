#!/bin/bash
set -e

# Source bashio if available
if [ -f /usr/lib/bashio/bashio.sh ]; then
    . /usr/lib/bashio/bashio.sh
fi

CONFIG_FILE="/app/config.yaml"

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

# Read configuration from Home Assistant add-on options
COGNITE_PROJECT=$(bashio::config 'cognite_project' 2>/dev/null || echo "")
COGNITE_CLUSTER=$(get_config 'cognite_cluster' 'az-eastus-1')
COGNITE_CLIENT_ID=$(bashio::config 'cognite_client_id' 2>/dev/null || echo "")
COGNITE_CLIENT_SECRET=$(bashio::config 'cognite_client_secret' 2>/dev/null || echo "")
COGNITE_TOKEN_URL=$(bashio::config 'cognite_token_url' 2>/dev/null || echo "")
COGNITE_SCOPES=$(get_config 'cognite_scopes' 'https://az-eastus-1.cognitedata.com/.default')

MQTT_HOST=$(get_config 'mqtt_host' 'homeassistant.local')
MQTT_PORT=$(get_config 'mqtt_port' '1883')
MQTT_USERNAME=$(get_config 'mqtt_username' '')
MQTT_PASSWORD=$(get_config 'mqtt_password' '')
MQTT_QOS=$(get_config 'mqtt_qos' '1')

INSTANCE_SPACE=$(get_config 'instance_space' 'ha_instances')
DATA_MODEL_SPACE=$(get_config 'data_model_space' 'sp_enterprise_schema_space')
DATA_MODEL_VERSION=$(get_config 'data_model_version' 'v2.0.12')

ALARM_EVENT_TOPIC=$(get_config 'alarm_event_topic' 'events/alarms/log')
ALARM_EVENT_VIEW=$(get_config 'alarm_event_view' 'haAlarmEvent')
ALARM_FRAME_TOPIC=$(get_config 'alarm_frame_topic' 'events/alarms/frame')
ALARM_FRAME_VIEW=$(get_config 'alarm_frame_view' 'haAlarmFrame')

LOG_LEVEL=$(get_config 'log_level' 'INFO')

if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "Starting MQTT Alarm Extractor for Cognite..."
    bashio::log.info "  Project: ${COGNITE_PROJECT}"
    bashio::log.info "  Cluster: ${COGNITE_CLUSTER}"
    bashio::log.info "  Instance Space: ${INSTANCE_SPACE}"
    bashio::log.info "  Data Model Space: ${DATA_MODEL_SPACE}"
    bashio::log.info "  Event topic: ${ALARM_EVENT_TOPIC} -> ${ALARM_EVENT_VIEW}"
    bashio::log.info "  Frame topic: ${ALARM_FRAME_TOPIC} -> ${ALARM_FRAME_VIEW}"
else
    echo "Starting MQTT Alarm Extractor for Cognite..."
    echo "  Project: ${COGNITE_PROJECT}"
    echo "  Cluster: ${COGNITE_CLUSTER}"
    echo "  Instance Space: ${INSTANCE_SPACE}"
    echo "  Data Model Space: ${DATA_MODEL_SPACE}"
    echo "  Event topic: ${ALARM_EVENT_TOPIC} -> ${ALARM_EVENT_VIEW}"
    echo "  Frame topic: ${ALARM_FRAME_TOPIC} -> ${ALARM_FRAME_VIEW}"
fi

# Generate config.yaml
cat > "$CONFIG_FILE" <<EOF
# Auto-generated configuration file
# Do not edit - changes will be overwritten on restart

cognite:
  project: "${COGNITE_PROJECT}"
  cluster: "${COGNITE_CLUSTER}"
  client_id: "${COGNITE_CLIENT_ID}"
  client_secret: "${COGNITE_CLIENT_SECRET}"
  token_url: "${COGNITE_TOKEN_URL}"
  scopes: "${COGNITE_SCOPES}"

mqtt:
  host: "${MQTT_HOST}"
  port: ${MQTT_PORT}
  username: "${MQTT_USERNAME}"
  password: "${MQTT_PASSWORD}"
  qos: ${MQTT_QOS}

instance_space: "${INSTANCE_SPACE}"
data_model:
  space: "${DATA_MODEL_SPACE}"
  version: "${DATA_MODEL_VERSION}"

subscriptions:
  - topic: "${ALARM_EVENT_TOPIC}"
    view: "${ALARM_EVENT_VIEW}"
  - topic: "${ALARM_FRAME_TOPIC}"
    view: "${ALARM_FRAME_VIEW}"

log_level: "${LOG_LEVEL}"
EOF

if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "Configuration generated successfully"
else
    echo "Configuration generated successfully"
fi

# Activate virtual environment and start extractor
cd /app
source /app/venv/bin/activate

if command -v bashio::log.info >/dev/null 2>&1; then
    bashio::log.info "Starting alarm extractor..."
else
    echo "Starting alarm extractor..."
fi

exec python -m alarm_extractor.main

