# Changelog

All notable changes to the MQTT Alarm Extractor for Cognite will be documented in this file.

## [1.0.6] - 2025-12-17

### Fixed
- Use NodeOrEdgeData wrapper for sources in NodeApply (not plain dict)
- Add detailed error logging showing full node payload on failure
- Fixes 'dict' object has no attribute 'dump' error

## [1.0.5] - 2025-12-17

### Fixed
- Fix run.sh shebang to use `#!/bin/bash` instead of `#!/usr/bin/with-contenv bashio`
- Source bashio manually like other working add-ons
- Add error handling for bashio commands
- Fixes s6-overlay-suexec and s6-envdir errors

## [1.0.4] - 2025-12-17

### Fixed
- Fix Dockerfile to match Home Assistant add-on pattern
- Change CMD to ENTRYPOINT (required for HA add-ons)
- Add BUILD_FROM default value
- Add `init: false` to config.json
- Add bash to installed packages

## [1.0.3] - 2025-12-17

### Fixed
- Rewrite schema to use Home Assistant's simple format (not JSON Schema)
- Schema now uses: `str`, `str?`, `int?`, `int(0,2)?`, `match(...)?` format
- Removed invalid JSON Schema fields: `type`, `title`, `description`, `enum`, `required`
- Add missing `ports`, `ports_description`, `host_network` fields

## [1.0.2] - 2025-12-17

### Fixed
- Update slug to match directory name for Home Assistant discovery

## [1.0.1] - 2025-12-17

### Fixed
- Support both `externalId` (camelCase) and `external_id` (snake_case) in payloads

### Changed
- Added detailed INFO-level logging for each alarm event and frame
- Log format shows: incoming message type, external ID, name, all properties, and write result

## [1.0.0] - 2025-12-17

### Added
- Initial release of the MQTT Alarm Extractor for Cognite
- Automatic attribute passthrough from MQTT to CDF data model views
- Smart node reference handling for attributes ending in `ExternalId`
  - Single values: `definitionExternalId: "had_xxx"` → `definition: {space, externalId}`
  - Array values: `assetsExternalId: ["haa_xxx"]` → `assets: [{space, externalId}]`
- Configurable MQTT topics for alarm events and alarm frames
- Configurable target CDF data model views (default: haAlarmEvent, haAlarmFrame)
- Statistics tracking and periodic logging
- Graceful shutdown handling

