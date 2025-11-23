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


