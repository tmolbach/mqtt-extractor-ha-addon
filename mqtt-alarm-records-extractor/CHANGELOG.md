# Changelog

All notable changes to the Alarm Extractor to Records for Cognite add-on will be documented in this file.

## [1.0.2] - 2025-01-XX

### Fixed
- Accept HTTP 202 (Accepted) as success status for Records API writes
- Fixed regression where HTTP 202 responses were incorrectly treated as errors

## [1.0.1] - 2025-01-XX

### Changed
- Simplified logging and error handling in handler
- Removed verbose debug logging for cleaner output
- Improved error response handling

## [1.0.0] - 2025-12-18

### Added
- Initial release of Alarm Extractor to Records for Cognite
- Extract alarm events and frames from MQTT and write to Cognite Records
- Support for configurable Records containers and stream
- Automatic transformation of ExternalId fields to node references
- Statistics tracking for events and frames processed

