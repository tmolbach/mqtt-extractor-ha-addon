### Changelog

**0.8.2** - 2025-12-16
- Fixed event handler to support `eventType` field in addition to `type` field
- Alarm payloads can now use either `"type": "ALARM_START"` or `"eventType": "ALARM_START"`
- Changed non-event payload warning to DEBUG level (e.g., when alarm frames are received by event handler)
- Eliminates "Invalid or missing event type" warnings when using new alarm payload format
- Both old and new payload formats now work with event.py handler
- Gracefully skips alarm frames and other non-event payloads without warnings
- Note: Consider migrating to `data_model_writes` for unified alarm handling (supports events and frames)

**0.8.1** - 2025-12-16
- **CRITICAL FIX:** Added validation to reject non-numeric values before uploading to CDF time series
- Now validates that values are `int` or `float` before buffering for data model uploads
- Added validation to reject `NaN` and `Infinity` float values
- Improved error logging to show which time series and values caused upload failures
- Prevents "Failed to parse parameter 'items[0].datapoints[0].value'" errors from CDF
- Added warning messages when skipping invalid values with details (value, type)

**0.8.0** - 2025-12-16
- **NEW: Generic Data Model Write Handler** - Flexible topic-to-view mapping for any CDF data model view
- Added `data_model_writes` configuration array for routing MQTT topics to specific views
- Each mapping specifies: topic pattern, view_external_id, instance_space, data_model_space, data_model_version
- Supports wildcard patterns (# and +) for flexible topic matching
- Built-in support for `haAlarmEvent` and `haAlarmFrame` views with proper field mapping
- Generic fallback for other views with automatic timestamp conversion and relationship handling
- Enables multiple alarm handlers (events, frames, logs) via configuration instead of code
- Examples:
  - `events/alarms/log → haAlarmEvent` for alarm occurrences
  - `events/alarms/frame → haAlarmFrame` for alarm summary periods
  - Extensible to any custom views in your data model
- Automatic external ID generation from topic + timestamp if not provided
- Comprehensive DEBUG logging for payload parsing and property mapping
- Supports both camelCase and snake_case field names in payloads
- Auto-conversion of timestamps to ISO 8601 format for CDF
- Asset relationship support (arrays of asset external IDs)

**0.7.3** - 2025-11-30
- Added support for asset references in alarm event payloads
- Fixed property handling to avoid sending null/None values to CDF
- Added comprehensive DEBUG logging for alarm event payloads and properties
- Log full parsed JSON payload and written properties at DEBUG level
- Only include triggerEntity and valueAtTrigger if they have actual values
- Support for both string asset IDs and object format with space/externalId

**0.7.2** - 2025-11-30
- Fixed timestamp format for CDF data model - must be ISO 8601 string, not milliseconds
- Convert numeric timestamps to ISO 8601 format: "2025-11-30T19:02:16.970Z"
- Keep string timestamps as-is if already in ISO format
- Use milliseconds timestamp only for external ID generation
- Fixed 400 error: "The value of property 'startTime' must be a string in the format 'YYYY-MM-DDTHH:MM:SS[.millis]...'"

**0.7.1** - 2025-11-30
- Fixed alarm event handler to support camelCase field names from MQTT payload
- Now handles both `externalIdPrefix` and `external_id_prefix`
- Now handles both `startTime` and `start_time`
- Now handles both `definition` and `alarm_definition_id`
- Added ISO 8601 timestamp parsing for string timestamps (e.g., "2025-11-30T23:46:16.005Z")
- Fixed issue where all alarm properties were showing as None

**0.7.0** - 2025-11-26
- Added alarm event handler for writing to CDF data model (haAlarmEvent view)
- New `mqtt_event_topics` configuration for alarm event subscriptions
- Supports ALARM_START and ALARM_END event types
- Auto-creates alarm event instances with proper relationships
- Configuration options:
  - `enable_alarm_events`: Enable/disable alarm event handling
  - `alarm_event_instance_space`: Instance space for alarm events
  - `alarm_event_view_external_id`: View to write to (default: haAlarmEvent)
  - `alarm_event_data_model_space`: Data model space (default: sp_enterprise_schema_space)
  - `alarm_event_data_model_version`: Data model version (default: v1)
  - `alarm_event_source_system`: Source system reference (default: MQTT)
- Extracts trigger entity, value, metadata from MQTT payload
- Links to alarm definitions via external ID reference

**0.6.4** - 2025-11-26
- Added delayed workflow triggering to ensure changes are never missed
- When a burst occurs too soon after the last trigger, automatically schedules a delayed trigger
- Delayed trigger executes exactly when the minimum interval has elapsed
- New bursts during a delayed trigger period will cancel the delay and start fresh debounce
- Ensures rare changes (daily or less frequent) always trigger workflows
- Example: Burst at T+0min triggers immediately, burst at T+1min schedules delayed trigger at T+5min

**0.6.3** - 2025-11-26
- Fixed workflow trigger state management to properly handle multiple bursts
- Improved workflow trigger logging to show time since last trigger and retry timing
- Fixed issue where `last_trigger` time wasn't properly preserved between bursts
- Now correctly schedules new workflows after the minimum interval has elapsed
- Added detailed debug logging for workflow trigger state transitions

**0.6.2** - 2025-11-26
- Implemented debounce/burst detection for workflow triggering
- Workflows now wait for message bursts to complete before triggering
- New configuration: `workflow_debounce_seconds` (default: 5 seconds)
- Each new message to the same database resets the debounce timer
- Workflow triggers only after no messages received for the debounce window
- Prevents multiple workflow executions during rapid message bursts
- Example: 10 messages in 3 seconds → single workflow trigger after 5 second quiet period

**0.6.1** - 2025-11-24
- Improved configuration naming and organization for clarity
- Renamed `create_missing` to `create_missing_timeseries` (more descriptive)
- Grouped `timeseries_view_external_id` with time series creation settings
- Added `trigger_workflows_on_raw_change` switch to explicitly enable workflow triggering
- Grouped workflow settings under the trigger switch:
  - `workflow_external_id`
  - `workflow_version`
  - `workflow_min_trigger_interval` (renamed from `workflow_trigger_interval`)
- Better logical grouping of related configuration options

**0.6.0** - 2025-11-24
- Added workflow triggering support for raw handler
- Automatically triggers CDF workflows after writing to Raw tables
- Configurable workflow external ID and version
- Throttling per database to avoid excessive workflow executions (default: 5 minutes)
- New configuration options:
  - `workflow_external_id`: External ID of workflow to trigger
  - `workflow_version`: Specific version of workflow (optional, uses latest if not specified)
  - `workflow_trigger_interval`: Minimum seconds between triggers per database (default: 300)
- Workflow receives input data with database name, trigger source, and timestamp

**0.5.2** - 2025-11-24
- Added Roomba/vacuum status conversions
  - "cleaning" → 1 (active)
  - "returning" → 1 (active)
  - "docked" → 0 (inactive)

**0.5.1** - 2025-11-24
- Added locked/unlocked to boolean conversion mappings
  - "locked" → 1 (true)
  - "unlocked" → 0 (false)

**0.5.0** - 2025-11-24
- Added support for structured JSON datapoint format in simple handler
- Can now parse messages with `value`, `timestamp`, and `external_id` fields
- Value conversion logic (on/off, boolean strings) still applied to structured format
- Uses provided timestamp and external_id from payload when available
- Example: `{"value": "on", "timestamp": 1764084466789, "external_id": "path/to/sensor"}`
- Backward compatible with existing simple payload formats

**0.4.9** - 2025-11-24
- Enhanced DEBUG logging for troubleshooting data issues
- Log every MQTT message received with topic and payload preview
- Log parsed values with their types (int, float, bool) before sending to CDF
- Log every datapoint queued/buffered with value and type information
- Log detailed CDF upload operations with datapoint counts
- Show full error tracebacks for upload failures

**0.4.8** - 2025-11-24
- Remove 'states/' prefix from topics when creating external IDs, names, and descriptions
- Shorten INFO log messages for better readability
  - "Matched: topic -> pattern" instead of verbose matching message
  - "Creating TS: topic (type=X)" instead of verbose creation message
  - "New topic: X" when discovering new topics
- Keep original full topic in metadata for reference

**0.4.7** - 2025-11-24
- Promoted topic pattern matching to INFO level for better visibility
- Promoted time series creation details to INFO level to track resource creation

**0.4.6** - 2025-11-24
- Improved logging levels across the codebase for better production use
- Changed skipped message logging in simple handler from INFO to DEBUG
- Reduced startup noise by removing redundant DEBUG echo statements in run.sh
- Changed "Topic discovered" and "Uploaded data points" messages from INFO to DEBUG
- Only log INFO when time series are created or during periodic status updates
- Consolidated startup progress messages for cleaner output

**0.4.5** - 2025-11-24
- Enhanced raw handler to parse DB and table names relative to subscription topic filter
- Database name is derived from the last segment of the subscription base path
- Table name is derived from the first segment after the base path
- Added debug logging to trace topic parsing in raw handler
- Example: filter `eastham/75_nsunkenmeadow/registry/#` with topic `eastham/75_nsunkenmeadow/registry/sites/site1` creates DB `registry` and table `sites`

**0.4.4** - 2025-11-24
- Added `raw` handler support for writing MQTT messages directly to CDF Raw service
- Added `mqtt_raw_topics` configuration option to specify topics for raw handling
- Raw handler automatically provisions Databases and Tables in CDF based on topic structure (db/table)
- Raw handler inserts JSON payloads as rows with auto-detected or provided keys

**0.4.3** - 2025-11-23
- Removed temporary debug logging for MQTT messages now that connectivity is verified

**0.4.2** - 2025-11-23
- Added INFO level logging for every received MQTT message to assist with debugging connectivity

**0.4.1** - 2025-11-23
- Fixed YAML parsing error by quoting configuration values (like external-id-prefix)
- Improved topic parsing to correctly handle newline-separated topics from UI input

**0.4.0** - 2025-11-23
- Fixed issue where only first topic was written when multiple topics configured
- Changed topic parsing to use array-based approach instead of pipe to avoid subshell issues
- Added debug output to show parsed topics

**0.3.9** - 2025-11-23
- Improved debug output to show full config file for troubleshooting

**0.3.8** - 2025-11-23
- Fixed YAML wildcard quoting by using quoted heredoc delimiter to preserve single quotes literally
- Added debug output to show generated subscriptions section

**0.3.7** - 2025-11-23
- Fixed version printing during startup by copying config.json and using BUILD_VERSION env var
- Changed changelog header formatting to use ### instead of #

**0.3.6** - 2025-11-23
- Fixed YAML wildcard quoting using printf instead of heredoc
- Added version number printing during startup for verification

**0.3.5** - 2025-11-23
- Fixed YAML wildcard quoting issue by using quoted heredoc in run.sh

**0.3.4** - 2025-11-23
- Changed changelog version headers to bold text for smaller font size

