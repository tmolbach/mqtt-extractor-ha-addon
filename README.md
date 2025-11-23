# Home Assistant Add-ons Repository

This repository contains Home Assistant add-ons for integrating with Cognite Data Fusion and testing add-on functionality.

## Add-ons

### 🧪 Hello World Test Add-on

A simple test add-on to validate Home Assistant add-on structure and installation flow. This add-on serves as a minimal example to test repository structure, Dockerfile build process, configuration schema, and add-on installation.

**Features:**
- Minimal test add-on for validation
- Prints customizable messages
- Validates add-on structure

**Documentation:** See [`hello-world/README.md`](hello-world/README.md) for details.

---

### 📡 MQTT to Cognite Data Fusion Extractor

Home Assistant add-on that extracts MQTT messages and pushes them to Cognite Data Fusion (CDF) as time series data points.

**Features:**
- **MQTT Integration**: Connects to any MQTT broker (including Home Assistant's built-in MQTT broker)
- **Cognite Data Fusion**: Pushes time series data to CDF with automatic time series creation
- **Data Model Support**: Optional integration with Cognite Data Model for structured time series management
- **Flexible Topic Subscriptions**: Support for wildcard topics (`*` for all topics, `+` for single-level wildcards)
- **Automatic Type Detection**: Detects numeric, string, and JSON data types from MQTT payloads
- **Home Assistant Integration**: Native HA add-on with UI configuration

**Documentation:** See [`mqtt-extractor/README.md`](mqtt-extractor/README.md) for full documentation, configuration options, and troubleshooting.

---

## Installation

### Add Repository to Home Assistant

1. **Open Home Assistant** and navigate to **Settings → Add-ons → Add-on Store**
2. Click the **three dots menu** (⋮) in the top right corner
3. Select **Repositories**
4. Click **Add** and enter: `https://github.com/tmolbach/mqtt-extractor-ha-addon`
5. Click **Add** to save the repository

### Install Add-ons

After adding the repository, both add-ons will appear in your add-on store:

- **Hello World Test Add-on** - For testing and validation
- **MQTT to Cognite Data Fusion Extractor** - For MQTT to CDF integration

Click **Install** on any add-on you want to use, then configure and start it.

## Repository Structure

```
.
├── README.md              # This file
├── repository.yaml        # Home Assistant repository configuration
├── hello-world/           # Hello World test addon
│   ├── config.json
│   ├── Dockerfile
│   ├── README.md
│   └── run.sh
└── mqtt-extractor/        # MQTT to CDF extractor addon
    ├── config.json
    ├── Dockerfile
    ├── extractor.py
    ├── README.md
    ├── requirements.txt
    ├── run.sh
    └── mqtt_extractor/
        └── ...
```

## Quick Start

### Installing the MQTT Extractor Add-on

1. **Add the repository** (see Installation section above)
2. **Install** the "MQTT to Cognite Data Fusion Extractor" add-on
3. **Configure** MQTT and CDF settings in the add-on configuration
4. **Start** the add-on and check logs to verify it's running

## MQTT Extractor Configuration

The MQTT Extractor add-on can be configured entirely through the Home Assistant UI. Here's what each option means:

### MQTT Configuration

- **mqtt_hostname** (required): MQTT broker hostname or IP address
  - For Home Assistant's built-in broker: `homeassistant.local` or `core-mosquitto`
  - For external broker: Use the broker's IP or hostname
  
- **mqtt_port** (required): MQTT broker port (default: `1883` for non-TLS, `8883` for TLS)
  
- **mqtt_username** (optional): Username for MQTT authentication
  
- **mqtt_password** (optional): Password for MQTT authentication
  
- **mqtt_client_id** (optional): MQTT client ID (default: `mqtt-extractor`)
  
- **mqtt_clean_session** (optional): Whether to use clean session (default: `false`)
  
- **mqtt_topics** (required): Array of MQTT topics to subscribe to
  - Example: `["home/sensor/temperature", "home/sensor/humidity"]`
  - Use `["*"]` to subscribe to all topics
  - Supports wildcards: `home/+/temperature` (single-level), `home/#` (multi-level)
  
- **mqtt_qos** (optional): Quality of Service level (0, 1, or 2, default: `1`)

### Cognite Data Fusion Configuration

- **cdf_url** (required): CDF cluster URL
  - Format: `https://<cluster>.cognitedata.com`
  - Example: `https://az-eastus-1.cognitedata.com`
  
- **cdf_project** (required): Your CDF project name
  
- **idp_client_id** (required): OAuth client ID for CDF authentication
  
- **idp_token_url** (required): OAuth token URL
  - Format: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`
  
- **idp_client_secret** (required): OAuth client secret
  
- **idp_scopes** (required): OAuth scopes
  - Format: `https://<cluster>.cognitedata.com/.default`
  - Example: `https://az-eastus-1.cognitedata.com/.default`

### General Configuration

- **external_id_prefix** (optional): Prefix for CDF external IDs (default: `mqtt:`)
  
- **upload_interval** (optional): Interval in seconds between uploads to CDF (default: `1`)
  
- **create_missing** (optional): Automatically create missing time series in CDF (default: `true`)
  
- **log_level** (optional): Logging level - `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default: `INFO`)

### Data Model Configuration (Optional)

- **enable_data_model** (optional): Enable Cognite Data Model integration (default: `false`)
  
- **instance_space** (required if data model enabled): Instance space for CogniteTimeSeries
  
- **data_model_space** (optional): Data model space (default: `sp_enterprise_schema_space`)
  
- **data_model_version** (optional): Data model version (default: `v1`)
  
- **timeseries_view_external_id** (optional): Time series view external ID (default: `haTimeSeries`)
  
- **source_system_space** (optional): Source system space (default: `cdf_cdm`)
  
- **source_system_version** (optional): Source system version (default: `v1`)

## Example Configuration

### Basic Configuration (Classic Time Series)

```json
{
  "mqtt_hostname": "homeassistant.local",
  "mqtt_port": 1883,
  "mqtt_username": "",
  "mqtt_password": "",
  "mqtt_topics": ["*"],
  "mqtt_qos": 1,
  "cdf_url": "https://az-eastus-1.cognitedata.com",
  "cdf_project": "my-project",
  "idp_client_id": "your-client-id",
  "idp_token_url": "https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token",
  "idp_client_secret": "your-client-secret",
  "idp_scopes": "https://az-eastus-1.cognitedata.com/.default",
  "log_level": "INFO"
}
```

### Advanced Configuration (With Data Model)

```json
{
  "mqtt_hostname": "homeassistant.local",
  "mqtt_port": 1883,
  "mqtt_topics": ["home/sensor/#", "home/device/#"],
  "mqtt_qos": 1,
  "cdf_url": "https://az-eastus-1.cognitedata.com",
  "cdf_project": "my-project",
  "idp_client_id": "your-client-id",
  "idp_token_url": "https://login.microsoftonline.com/your-tenant-id/oauth2/v2.0/token",
  "idp_client_secret": "your-client-secret",
  "idp_scopes": "https://az-eastus-1.cognitedata.com/.default",
  "enable_data_model": true,
  "instance_space": "ha_instances",
  "data_model_space": "sp_enterprise_schema_space",
  "data_model_version": "v1",
  "timeseries_view_external_id": "haTimeSeries",
  "log_level": "INFO"
}
```

## Testing the MQTT Extractor

### Verify MQTT Connection

1. Check the add-on logs (Settings → Add-ons → mqtt-extractor → Log)
2. Look for: `Connected to <hostname>:<port> (<n> subscriptions)`
3. If you see connection errors, verify:
   - MQTT broker hostname and port are correct
   - MQTT credentials (if required) are correct
   - Network connectivity to the MQTT broker

### Test MQTT Message Publishing

**Using Home Assistant Developer Tools:**
1. Go to Developer Tools → MQTT
2. Publish a message:
   - Topic: `test/sensor/temperature`
   - Payload: `22.5`
   - Click "Publish"

**Using mosquitto_pub (if available):**
```bash
mosquitto_pub -h homeassistant.local -p 1883 -t "test/sensor/temperature" -m "22.5"
```

### Verify Data in Cognite Data Fusion

1. Log in to your CDF project
2. Navigate to **Time Series** → **Browse**
3. Search for time series with external ID starting with your prefix (e.g., `mqtt:test_sensor_temperature`)
4. Check that data points are being uploaded

## Troubleshooting

### MQTT Extractor Add-on Won't Start

1. **Check Logs**: Go to the Log tab and look for error messages
2. **Verify Configuration**: Ensure all required fields are filled in
3. **Check Docker**: The add-on runs in a Docker container - verify Docker is running
4. **Check Disk Space**: Ensure you have enough disk space on your Home Assistant system

### MQTT Connection Issues

**Error: "Connection refused"**
- Verify the MQTT broker hostname and port
- Check if the MQTT broker is running
- For Home Assistant's broker, ensure the Mosquitto add-on is installed and running

**Error: "Authentication failed"**
- Verify MQTT username and password are correct
- Check if the MQTT broker requires authentication

**Error: "No handler for topic"**
- Verify the topic matches your subscription patterns
- Check that wildcards are used correctly (`*` for all, `+` for single-level)

### CDF Connection Issues

**Error: "Authentication failed"**
- Verify all CDF credentials are correct:
  - `cdf_url` format: `https://<cluster>.cognitedata.com`
  - `idp_token_url` format: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`
  - `idp_scopes` format: `https://<cluster>.cognitedata.com/.default`
- Check that your OAuth client has the necessary permissions in CDF

**Error: "Project not found"**
- Verify the `cdf_project` name is correct
- Ensure your OAuth client has access to the project

**Error: "Time series creation failed"**
- Check that your OAuth client has permissions to create time series
- Verify the `create_missing` option is set to `true`

### Data Model Issues

**Error: "Instance space not found"**
- Verify the `instance_space` is correct
- Ensure the instance space exists in your CDF project
- Check that your OAuth client has access to the instance space

**Error: "View not found"**
- Verify the data model configuration:
  - `data_model_space`
  - `data_model_version`
  - `timeseries_view_external_id`
- Ensure the view exists in your CDF project

### Performance Issues

**High CPU Usage**
- Reduce the number of subscribed topics
- Increase `upload_interval` to batch more data points
- Set `log_level` to `WARNING` or `ERROR` to reduce logging overhead

**Memory Issues**
- Reduce the number of active subscriptions
- Check for memory leaks in the logs
- Restart the add-on periodically if needed

## Advanced Usage

### Custom Message Handlers

The add-on uses the `mqtt_extractor.simple` handler by default, which handles:
- Numeric values (integers and floats)
- Boolean strings (ON/OFF, true/false, etc.)
- Single-value JSON objects

To use a custom handler, you would need to modify the `run.sh` script to use a different handler module.

### Monitoring and Metrics

The add-on includes Prometheus metrics (if enabled):
- `messages`: Number of MQTT messages received
- `data_points`: Number of data points uploaded to CDF
- `requests_failed`: Number of failed CDF requests

### Backup and Restore

The configuration is stored in `/data/config.yaml` inside the add-on container. To backup:
1. Use the Home Assistant backup feature (includes add-on configurations)
2. Or manually copy the configuration from the Home Assistant UI

## Support

For issues related to:
- **Home Assistant OS**: Check [Home Assistant documentation](https://www.home-assistant.io/docs/)
- **Cognite Data Fusion**: Check [CDF documentation](https://docs.cognite.com/)
- **MQTT**: Check your MQTT broker documentation

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

See the LICENSE file in the repository root.

