# Add-on Folder Structure

This document describes the exact folder structure required for the Home Assistant OS add-on.

## Required Structure

```
mqtt-extractor/
├── config.json          # Add-on manifest and configuration schema
├── Dockerfile           # Container build instructions
├── run.sh              # Entrypoint script (must be executable)
├── requirements.txt     # Python dependencies
├── extractor.py        # Main entry point script
├── README.md           # User documentation
├── INSTALLATION.md     # Installation guide
├── STRUCTURE.md        # This file
└── mqtt_extractor/     # Python package
    ├── __init__.py     # Package initialization
    ├── main.py         # Main extractor logic
    ├── cdf.py          # CDF-specific handler
    ├── simple.py       # Simple MQTT payload parser
    └── metrics.py      # Prometheus metrics
```

## File Descriptions

### config.json
The add-on manifest file that defines:
- Add-on metadata (name, version, description)
- Configuration schema (options and schema)
- Supported architectures
- Startup behavior

### Dockerfile
Builds the Docker container that runs the add-on:
- Base image: Python 3.11 slim
- Installs system dependencies
- Installs Python packages from requirements.txt
- Copies application code
- Sets entrypoint to run.sh

### run.sh
Entrypoint script that:
- Reads configuration from Home Assistant options
- Generates config.yaml from options
- Handles topic array parsing
- Logs startup information
- Executes the Python extractor

### requirements.txt
Python package dependencies:
- cognite-extractor-utils (CDF integration)
- paho-mqtt (MQTT client)
- python-dotenv (environment variables)
- prometheus-client (metrics)

### extractor.py
Main entry point that:
- Imports the mqtt_extractor.main module
- Calls main() with the config file path
- Handles command-line arguments

### mqtt_extractor/
Python package containing the extractor logic:
- **main.py**: Core extractor with MQTT client, CDF integration, and data model support
- **simple.py**: Simple payload parser for numeric, string, and JSON values
- **cdf.py**: CDF-specific payload parser (for CDF-formatted messages)
- **metrics.py**: Prometheus metrics definitions

## Installation Location

The add-on should be placed in:
```
/config/addons/mqtt-extractor/
```

On Home Assistant OS, `/config` is typically mounted at:
- **VirtualBox VM**: Shared folder or mounted volume
- **Physical hardware**: SD card or internal storage
- **Docker**: Volume mount

## Permissions

Ensure `run.sh` is executable:
```bash
chmod +x /config/addons/mqtt-extractor/run.sh
```

## Verification

After copying files, verify the structure:
```bash
cd /config/addons/mqtt-extractor
ls -la
# Should show all files listed above

# Check run.sh is executable
ls -l run.sh
# Should show: -rwxr-xr-x ... run.sh
```

## Notes

- The `mqtt_extractor` folder must be a Python package (contains `__init__.py`)
- All Python files use relative imports within the package
- The Dockerfile copies the entire `mqtt_extractor` folder into the container
- Configuration is generated at runtime by `run.sh` from Home Assistant options

