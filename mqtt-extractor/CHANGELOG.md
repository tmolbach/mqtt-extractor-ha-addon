### Changelog

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

