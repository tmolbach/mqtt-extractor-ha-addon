# MQTT Extractor - Home Assistant OS Add-on Summary

## What Was Created

This Home Assistant OS add-on converts your Windows command-line MQTT extractor into a fully integrated Home Assistant add-on that can run in your VirtualBox VM with Home Assistant OS.

## Folder Structure

```
mqtt-extractor/
├── config.json              # Add-on manifest with UI configuration schema
├── Dockerfile               # Container build instructions
├── run.sh                   # Entrypoint script (generates config from HA options)
├── requirements.txt         # Python dependencies
├── extractor.py             # Main entry point (calls mqtt_extractor.main)
├── README.md                # Comprehensive user documentation
├── INSTALLATION.md          # Step-by-step installation guide
├── QUICKSTART.md            # 5-minute quick start guide
├── STRUCTURE.md             # Folder structure documentation
└── mqtt_extractor/          # Python package (copied from existing codebase)
    ├── __init__.py
    ├── main.py              # Core extractor logic (reused)
    ├── cdf.py               # CDF handler (reused)
    ├── simple.py            # Simple parser (reused)
    └── metrics.py           # Metrics (reused)
```

## Key Features

1. **Home Assistant Integration**
   - Native add-on with on/off switch
   - UI-based configuration (no manual YAML editing)
   - Automatic startup on boot
   - Integrated logging

2. **Configuration via UI**
   - MQTT broker settings (hostname, port, credentials)
   - Topic subscriptions (supports arrays and wildcards)
   - CDF authentication (OAuth credentials)
   - Data model settings (optional)
   - Logging level control

3. **Reuses Existing Code**
   - `mqtt_extractor/main.py` - Core extractor logic
   - `mqtt_extractor/simple.py` - Message parsing
   - `mqtt_extractor/cdf.py` - CDF integration
   - All existing functionality preserved

## How It Works

1. **Configuration Flow:**
   ```
   Home Assistant UI Options → run.sh → config.yaml → extractor.py → mqtt_extractor/main.py
   ```

2. **run.sh Script:**
   - Reads Home Assistant options using `bashio::config`
   - Generates `config.yaml` in `/data/config.yaml`
   - Handles array parsing for topics
   - Sets up environment

3. **extractor.py:**
   - Simple wrapper that imports `mqtt_extractor.main`
   - Passes config file path to `main()`
   - Maintains compatibility with existing code

4. **Docker Container:**
   - Base: Python 3.11 slim
   - Installs dependencies from `requirements.txt`
   - Copies application code
   - Runs `run.sh` as entrypoint

## Installation Methods

### Method 1: Local Add-on (Recommended)
1. Copy `mqtt-extractor` folder to `/config/addons/` on Home Assistant
2. Restart Home Assistant
3. Install via Add-ons UI
4. Configure and start

### Method 2: Git Repository
1. Push to GitHub/GitLab
2. Add repository URL in Home Assistant
3. Install via Add-ons UI

## Configuration Options

### Required
- `mqtt_hostname` - MQTT broker address
- `mqtt_port` - MQTT broker port
- `mqtt_topics` - Array of topics to subscribe
- `cdf_url` - CDF cluster URL
- `cdf_project` - CDF project name
- `idp_client_id` - OAuth client ID
- `idp_token_url` - OAuth token URL
- `idp_client_secret` - OAuth client secret
- `idp_scopes` - OAuth scopes

### Optional
- MQTT authentication (username/password)
- Data model integration
- Upload interval
- External ID prefix
- Log level

## Testing

1. **MQTT Connection:** Check logs for "Connected to..."
2. **Message Processing:** Publish test message via HA Developer Tools
3. **CDF Upload:** Verify time series in CDF web UI
4. **Data Model:** Check instance space if enabled

## Troubleshooting

- **Add-on won't start:** Check logs, verify configuration, check Docker
- **MQTT connection fails:** Verify broker hostname/port, check credentials
- **CDF authentication fails:** Verify all OAuth credentials, check URL formats
- **No data in CDF:** Check topic subscriptions, verify message format

## Documentation Files

- **README.md** - Complete user guide with all features
- **INSTALLATION.md** - Detailed installation steps
- **QUICKSTART.md** - 5-minute quick start
- **STRUCTURE.md** - Folder structure explanation

## Next Steps

1. **Install the add-on** following INSTALLATION.md
2. **Configure** using the Home Assistant UI
3. **Test** with sample MQTT messages
4. **Monitor** logs and CDF data
5. **Customize** topics and settings as needed

## Differences from Windows Version

1. **Configuration:** UI-based instead of YAML file editing
2. **Environment:** Runs in Docker container instead of native Windows
3. **Startup:** Managed by Home Assistant instead of manual script
4. **Logging:** Integrated with Home Assistant logs
5. **Deployment:** Single add-on package instead of separate files

## Compatibility

- **Home Assistant OS:** Full support
- **Home Assistant Supervised:** Should work (not tested)
- **Home Assistant Container:** May need adjustments
- **Architectures:** amd64, aarch64, armv7

## Support

For issues:
1. Check add-on logs in Home Assistant
2. Review README.md troubleshooting section
3. Verify configuration matches examples
4. Check Home Assistant system logs

