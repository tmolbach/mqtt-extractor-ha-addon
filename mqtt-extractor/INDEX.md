# MQTT Extractor - Home Assistant Add-on Documentation Index

## Quick Links

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes ⚡
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation guide 📦
- **[README.md](README.md)** - Complete user documentation 📚
- **[STRUCTURE.md](STRUCTURE.md)** - Folder structure explanation 🗂️
- **[SUMMARY.md](SUMMARY.md)** - Overview of what was created 📋

## File Reference

### Core Add-on Files
- **config.json** - Add-on manifest and configuration schema
- **Dockerfile** - Container build instructions
- **run.sh** - Entrypoint script (generates config from HA options)
- **requirements.txt** - Python dependencies
- **extractor.py** - Main entry point

### Python Package
- **mqtt_extractor/** - Python package containing extractor logic
  - `__init__.py` - Package initialization
  - `main.py` - Core extractor with MQTT/CDF integration
  - `simple.py` - Simple MQTT payload parser
  - `cdf.py` - CDF-specific handler
  - `metrics.py` - Prometheus metrics

### Documentation
- **README.md** - Complete user guide (features, configuration, troubleshooting)
- **INSTALLATION.md** - Step-by-step installation instructions
- **QUICKSTART.md** - Quick start guide for fast setup
- **STRUCTURE.md** - Folder structure and file descriptions
- **SUMMARY.md** - Overview and key features
- **INDEX.md** - This file

## Getting Started

1. **New to this?** Start with [QUICKSTART.md](QUICKSTART.md)
2. **Installing?** Follow [INSTALLATION.md](INSTALLATION.md)
3. **Configuring?** See [README.md](README.md) Configuration section
4. **Troubleshooting?** Check [README.md](README.md) Troubleshooting section

## Installation Path

```
1. Copy mqtt-extractor folder → /config/addons/ on Home Assistant
2. Restart Home Assistant
3. Install add-on via UI
4. Configure in UI
5. Start add-on
6. Test with MQTT messages
```

## Configuration Flow

```
Home Assistant UI Options
    ↓
run.sh (generates config.yaml)
    ↓
extractor.py (entry point)
    ↓
mqtt_extractor/main.py (core logic)
    ↓
MQTT Broker ← → Cognite Data Fusion
```

## Key Features

✅ Native Home Assistant add-on  
✅ UI-based configuration  
✅ MQTT message extraction  
✅ Cognite Data Fusion integration  
✅ Data model support (optional)  
✅ Automatic time series creation  
✅ Wildcard topic support  
✅ Type detection (numeric/string/JSON)  

## Support Resources

- **Configuration Examples:** See README.md
- **Troubleshooting:** See README.md Troubleshooting section
- **File Structure:** See STRUCTURE.md
- **Installation Help:** See INSTALLATION.md

## Version Information

- **Add-on Version:** 0.2.0
- **Python Version:** 3.11
- **Base Image:** python:3.11-slim
- **Supported Architectures:** amd64, aarch64, armv7

