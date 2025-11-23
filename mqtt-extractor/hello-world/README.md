# Hello World Test Add-on

Simple test add-on to validate Home Assistant add-on structure and installation flow.

## Purpose

This add-on serves as a minimal example to test:
- Repository structure
- Dockerfile build process
- Configuration schema
- Add-on installation and startup

## Installation

1. Add repository: `https://github.com/tmolbach/mqtt-extractor-ha-addon`
2. Install "Hello World Test Add-on"
3. Configure (optional): Set custom message
4. Start the add-on

## What It Does

- Prints "Hello World" message every 10 seconds
- Logs to Home Assistant logs
- Validates that the add-on structure works correctly

## Configuration

- **message** (optional): Custom message to display (default: "Hello World from Home Assistant!")

## Testing

After installation, check the add-on logs to see the message being printed every 10 seconds. If you see the logs, the add-on structure is working correctly!

