#!/usr/bin/with-contenv bashio
# ==============================================================================
# HA MQTT Alarm Extractor for Cognite
# Generates config.yaml from Home Assistant add-on options and starts extractor
# ==============================================================================

set -e

CONFIG_FILE="/app/config.yaml"

# Read configuration from Home Assistant add-on options
COGNITE_PROJECT=$(bashio::config 'cognite_project')
COGNITE_CLUSTER=$(bashio::config 'cognite_cluster')
COGNITE_CLIENT_ID=$(bashio::config 'cognite_client_id')
COGNITE_CLIENT_SECRET=$(bashio::config 'cognite_client_secret')
COGNITE_TOKEN_URL=$(bashio::config 'cognite_token_url')
COGNITE_SCOPES=$(bashio::config 'cognite_scopes')

MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USERNAME=$(bashio::config 'mqtt_username')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')
MQTT_QOS=$(bashio::config 'mqtt_qos')

DATA_MODEL_SPACE=$(bashio::config 'data_model_space')
DATA_MODEL_VERSION=$(bashio::config 'data_model_version')

ALARM_EVENT_TOPIC=$(bashio::config 'alarm_event_topic')
ALARM_EVENT_VIEW=$(bashio::config 'alarm_event_view')
ALARM_FRAME_TOPIC=$(bashio::config 'alarm_frame_topic')
ALARM_FRAME_VIEW=$(bashio::config 'alarm_frame_view')

LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Starting MQTT Alarm Extractor for Cognite..."
bashio::log.info "  Project: ${COGNITE_PROJECT}"
bashio::log.info "  Cluster: ${COGNITE_CLUSTER}"
bashio::log.info "  Space: ${DATA_MODEL_SPACE}"
bashio::log.info "  Event topic: ${ALARM_EVENT_TOPIC} -> ${ALARM_EVENT_VIEW}"
bashio::log.info "  Frame topic: ${ALARM_FRAME_TOPIC} -> ${ALARM_FRAME_VIEW}"

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

bashio::log.info "Configuration generated successfully"

# Activate virtual environment and start extractor
cd /app
source /app/venv/bin/activate

bashio::log.info "Starting alarm extractor..."
exec python -m alarm_extractor.main

