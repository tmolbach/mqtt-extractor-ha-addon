# Changelog

All notable changes to the MQTT Alarm Extractor for Cognite will be documented in this file.

## [1.0.15] - 2025-01-XX

### Added
- Retry queue mechanism for failed CDF writes during internet outages
- Messages that fail to write to CDF are automatically queued for retry
- Automatic retry when connectivity is restored (detected after successful writes)
- Periodic retry attempts even when no new messages arrive
- Queue size limit (10,000 messages) and timeout (24 hours) to prevent unbounded growth
- Statistics tracking for failed and retried writes

### Changed
- Update default data model version from v2.0.12 to v2.0.13

## [1.0.14] - 2025-01-XX

### Fixed
- Add buffering mechanism for AlarmEvents that reference non-existent AlarmFrames
- Events are automatically buffered when their referenced frame doesn't exist yet
- Buffered events are retried automatically when the corresponding AlarmFrame is written
- Prevents "Cannot auto-create a direct relation target" errors when events arrive before frames
- Added timeout mechanism (5 minutes) to prevent indefinite buffering
- Improved statistics tracking with buffered/retried event counts

## [1.0.13] - 2025-01-XX

### Changed
- Update default data model version from v1 to v2.0.12
- Support for AlarmEvent to AlarmFrame linking via `frameExternalId` property
- The `transform_payload` function automatically converts `frameExternalId` → `frame` direct relation

## [1.0.10] - 2025-12-17

### Fixed
- Fix shutdown summary formatting to match mqtt-extractor style
- Remove equals signs separator (was causing large fonts in HA log viewer)
- Use simple format matching existing extractor

## [1.0.9] - 2025-12-17

### Fixed
- Fix _on_disconnect callback signature to handle variable arguments (MQTTv5 compatibility)
- Add graceful shutdown summary showing events/frames received and written
- Prevent TypeError on disconnect

## [1.0.8] - 2025-12-17

### Changed
- Move most logging to DEBUG level for cleaner output
- Keep single polished INFO log line per alarm event/frame showing Name
- Format: "AlarmEvent: {name}" or "AlarmFrame: {name}"
- Reduces log verbosity while keeping essential visibility

## [1.0.7] - 2025-12-17

### Fixed
- Separate instance_space and data_model_space configuration
- Default instance_space: ha_instances (where nodes are stored)
- Default data_model_space: sp_enterprise_schema_space (where views are defined)
- ViewId uses data_model_space
- Node references (source, definition, assets) use instance_space
- NodeApply uses instance_space

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

