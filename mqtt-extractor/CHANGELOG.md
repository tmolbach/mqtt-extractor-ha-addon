### Changelog

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

