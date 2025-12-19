# Alarm Extractor to Records for Cognite

A Home Assistant add-on that extracts alarm events and frames from MQTT and writes them directly to Cognite Data Fusion Records.

## Features

- **Automatic Attribute Mapping**: All MQTT payload attributes pass through directly to CDF Records
- **Smart Node References**: Attributes ending in `ExternalId` are automatically converted to CDF direct relations
- **Configurable Topics**: Map any MQTT topic to any CDF Records container
- **Pre-sanitized IDs**: Assumes external IDs in MQTT payloads are ready to use as-is

## Configuration

### Cognite Settings

| Option | Description |
|--------|-------------|
| `cognite_project` | CDF project name |
| `cognite_cluster` | CDF cluster (e.g., `az-eastus-1`) |
| `cognite_client_id` | OAuth2 client ID |
| `cognite_client_secret` | OAuth2 client secret |
| `cognite_token_url` | OAuth2 token endpoint |
| `cognite_scopes` | OAuth2 scopes |

### MQTT Settings

| Option | Description | Default |
|--------|-------------|---------|
| `mqtt_host` | MQTT broker hostname | `homeassistant.local` |
| `mqtt_port` | MQTT broker port | `1883` |
| `mqtt_username` | MQTT username | - |
| `mqtt_password` | MQTT password | - |
| `mqtt_qos` | Quality of Service level | `1` |

### Records Settings

| Option | Description | Default |
|--------|-------------|---------|
| `instance_space` | CDF space for node references | `ha_instances` |
| `records_space` | CDF space where Records containers are defined | `ha_records` |
| `stream_external_id` | Stream external ID for writing records | `ha_alarm_stream` |
| `alarm_event_topic` | MQTT topic for alarm events | `events/alarms/log` |
| `alarm_event_container` | Target container for events | `AlarmEventRecord` |
| `alarm_frame_topic` | MQTT topic for alarm frames | `events/alarms/frame` |
| `alarm_frame_container` | Target container for frames | `AlarmFrameRecord` |

## MQTT Payload Format

### Required Field

Every MQTT payload must include an `external_id` field:

```json
{
  "external_id": "hal_75_nsunkenmeadow_sensor_123",
  ...
}
```

### Automatic Attribute Passthrough

All attributes in the MQTT payload are passed directly to CDF Records:

```json
{
  "external_id": "hal_xxx",
  "name": "Alarm Start",
  "description": "Water leak detected",
  "startTime": "2025-12-17T04:25:30Z",
  "valueAtTrigger": "on"
}
```

### Node References (ExternalId Convention)

Attributes ending in `ExternalId` are automatically converted to CDF direct relations:

**Single Reference:**
```json
{
  "definitionExternalId": "had_75_nsunkenmeadow_alarmdef_xxx"
}
```
Becomes:
```json
{
  "definition": {"space": "ha_instances", "externalId": "had_75_nsunkenmeadow_alarmdef_xxx"}
}
```

**Array of References:**
```json
{
  "assetsExternalId": ["haa_75_nsunkenmeadow", "haa_other_asset"]
}
```
Becomes:
```json
{
  "assets": [
    {"space": "ha_instances", "externalId": "haa_75_nsunkenmeadow"},
    {"space": "ha_instances", "externalId": "haa_other_asset"}
  ]
}
```

## Example MQTT Payloads

### Alarm Event

```json
{
  "external_id": "hal_75_nsunkenmeadow_binary_sensor.water_leak_123",
  "name": "Alarm Start: Water Leak Sensor",
  "description": "Water leak detected in basement",
  "eventType": "ALARM_START",
  "startTime": "2025-12-17T04:25:30.382Z",
  "valueAtTrigger": "on",
  "triggerEntity": "binary_sensor.water_leak_sensor",
  "definitionExternalId": "had_75_nsunkenmeadow_alarmdef_water_leak",
  "assetsExternalId": ["haa_75_nsunkenmeadow"],
  "sourceExternalId": "has_mqtt"
}
```

### Alarm Frame

```json
{
  "external_id": "haf_75_nsunkenmeadow_binary_sensor.water_leak_123",
  "name": "Alarm Episode: Water Leak Sensor",
  "description": "Water leak episode lasting 5.6 seconds",
  "startTime": "2025-12-17T04:25:30.382Z",
  "endTime": "2025-12-17T04:25:36.030Z",
  "durationSeconds": 5.648,
  "triggerValue": "on",
  "definitionExternalId": "had_75_nsunkenmeadow_alarmdef_water_leak",
  "assetsExternalId": ["haa_75_nsunkenmeadow"]
}
```

## Records Structure

Records are written to CDF using the Records API. Each record has:

- `space`: The records space (e.g., `ha_records`)
- `externalId`: The record external ID (from MQTT payload)
- `sources`: Array containing one source with:
  - `source`: Container reference (`type: "container"`, `space`, `externalId`)
  - `properties`: Transformed MQTT payload properties

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "Alarm Extractor to Records for Cognite" add-on
3. Configure the add-on with your Cognite and MQTT settings
4. Ensure the Records containers (`AlarmEventRecord`, `AlarmFrameRecord`) and stream exist in CDF
5. Start the add-on

## Logs

The add-on logs statistics every 60 seconds:
```
Stats: Events: 45/45 | Frames: 22/22 | Errors: 0
```

Set `log_level` to `DEBUG` for detailed message logging.

