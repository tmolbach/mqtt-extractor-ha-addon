# Changelog

All notable changes to this add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-11-23

### Fixed
- Fixed YAML parsing error when using wildcard topics (`*` or `+`) by using single quotes in generated config.yaml
- Restored progress indicators for hello-world addon

### Changed
- Improved progress indicators during Docker build and addon startup phases

## [0.3.0] - 2025-11-23

### Added
- Progress indicators during Docker build process (5%, 15%, 20%, 25%, 50%, 60%, 75%, 85%, 95%, 100%)
- Progress indicators during addon startup (5%, 10%, 15%, 20%, 30%, 40%, 70%, 75%, 80%, 90%, 95%, 100%)

### Changed
- Updated repository structure - moved addon to root level

## [0.2.9] - 2025-11-23

### Fixed
- Replace with-contenv wrapper with direct bashio sourcing to avoid s6 errors

## [0.2.8] - 2025-11-23

### Fixed
- Add init: false for s6-overlay v3 compatibility

## [0.2.7] - 2025-11-23

### Fixed
- Add error handling for bashio calls and wait for s6

## [0.2.6] - 2025-11-23

### Fixed
- Remove manual bashio install - use base image bashio

## [0.2.5] - 2025-11-23

### Fixed
- Install bashio for Home Assistant add-on support

## [0.2.4] - 2025-11-23

### Fixed
- Use python3 explicitly and ensure run.sh permissions

## [0.2.3] - 2025-11-23

### Fixed
- Use virtual environment for Python packages to avoid PEP 668 issue

## [0.2.2] - 2025-11-23

### Fixed
- Add --break-system-packages flag for Python 3.12 PEP 668

## [0.2.1] - 2025-11-23

### Changed
- Initial release with basic MQTT to CDF extraction functionality

