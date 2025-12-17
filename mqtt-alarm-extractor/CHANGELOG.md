# Changelog

All notable changes to the MQTT Alarm Extractor for Cognite will be documented in this file.

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

