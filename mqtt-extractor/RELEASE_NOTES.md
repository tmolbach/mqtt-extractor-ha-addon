# MQTT to CDF Extractor - Recent Updates Summary

## Version 0.6.4 - Major Feature Release

### Overview
This release series (0.4.4 through 0.6.4) introduces significant enhancements to the MQTT to CDF extractor, including a new Raw handler for CDF staging data, workflow automation, improved logging, and structured JSON support.

---

## 🆕 Major New Features

### 1. Raw Handler for CDF Staging (v0.4.4+)
- **New Handler**: `mqtt_extractor.raw` writes MQTT messages directly to CDF Raw service
- **Auto-Provisioning**: Automatically creates databases and tables based on MQTT topic structure
- **Topic Parsing**: Intelligent parsing of topics relative to subscription filters
  - Example: `eastham/75_nsunkenmeadow/registry/#` → Database: `registry`, Tables: `sites`, `houses`, etc.
- **Configuration**: New `mqtt_raw_topics` option to specify topics for raw handling

### 2. Workflow Automation (v0.6.0+)
- **Automatic Workflow Triggering**: Kick off CDF workflows when Raw data changes
- **Burst Detection**: Smart debouncing waits for message bursts to complete (default 5s)
- **Throttling**: Configurable minimum interval between workflow executions (default 5 min)
- **Delayed Triggers**: Ensures rare changes (daily or less) never get missed
- **Configuration Options**:
  - `trigger_workflows_on_raw_change`: Enable/disable workflow triggering
  - `workflow_external_id`: Workflow to trigger
  - `workflow_version`: Specific version (optional)
  - `workflow_min_trigger_interval`: Minimum seconds between triggers (300)
  - `workflow_debounce_seconds`: Wait time after last message (5)

### 3. Structured JSON Support (v0.5.0+)
- **CDF Datapoint Format**: Simple handler now accepts pre-formatted datapoints
- **Format**: `{"value": "on", "timestamp": 1234567890, "external_id": "path/to/sensor"}`
- **Value Conversion**: Still applies boolean/state conversions to values
- **Backward Compatible**: Works with existing simple payloads

---

## 🔧 Improvements

### Configuration (v0.6.1)
- **Better Naming**: `create_missing` → `create_missing_timeseries` (clearer purpose)
- **Logical Grouping**: Related settings grouped together
  - Time series settings grouped with view configuration
  - Workflow settings grouped under enable switch

### Logging (v0.4.6-0.4.9)
- **Reduced Noise**: Moved verbose messages from INFO to DEBUG
- **Concise Messages**: Shorter, more actionable INFO-level logs
- **Enhanced DEBUG**: Comprehensive payload, parsing, and upload details for troubleshooting
- **Key INFO Messages**:
  - "New topic: X" (time series creation)
  - "Matched: topic -> pattern" (routing)
  - "Creating TS: topic (type=X)" (resource creation)
  - Workflow trigger notifications

### Topic Handling (v0.4.8)
- **Clean External IDs**: Removes `states/` prefix from topics automatically
- **Example**: `states/switch.light` → External ID: `switch_light`
- **Metadata**: Original topic preserved in metadata

### Boolean Conversions (v0.5.1-0.5.2)
- **New Mappings Added**:
  - `locked` → 1, `unlocked` → 0
  - `cleaning` → 1, `returning` → 1 (Roomba active states)
  - `docked` → 0 (Roomba inactive)

---

## 🐛 Bug Fixes

### Workflow State Management (v0.6.3-0.6.4)
- **Fixed**: Workflow trigger state properly preserved between bursts
- **Fixed**: Delayed triggers now execute exactly at minimum interval
- **Fixed**: New bursts during delayed wait properly cancel and reschedule

---

## 📊 Configuration Examples

### Simple Time Series (Existing Functionality)
```yaml
mqtt_topics:
  - "homeassistant/#"

create_missing_timeseries: true
timeseries_view_external_id: "haTimeSeries"
```

### Raw Data to CDF with Workflow Automation
```yaml
mqtt_raw_topics:
  - "eastham/75_nsunkenmeadow/registry/#"

trigger_workflows_on_raw_change: true
workflow_external_id: "ha_ingestion"
workflow_version: "v1"
workflow_min_trigger_interval: 300  # 5 minutes
workflow_debounce_seconds: 5  # Wait 5s after burst
```

### Structured JSON Datapoints
```yaml
mqtt_topics:
  - "states/eastham/75_nsunkenmeadow/ts/#"

# Messages like:
# {"value": "on", "timestamp": 1764084466789, "external_id": "..."}
```

---

## 🔄 Workflow Automation Behavior

### Example Timeline:
```
T+0:00  First burst (10 messages) → Workflow triggers at T+0:05
T+0:30  Second burst (5 messages) → Scheduled for T+5:05 (delayed)
T+1:00  Third burst (3 messages)  → Rescheduled for T+6:05
T+6:05  Workflow executes → Processes all changes since T+0:05
```

### Key Benefits:
- ✅ Single workflow execution per logical batch of changes
- ✅ Never miss rare updates (even daily changes trigger workflows)
- ✅ Efficient: Multiple rapid changes = one workflow
- ✅ Predictable: Always triggers at exact minimum interval

---

## 📈 Version History Summary

| Version | Key Feature |
|---------|-------------|
| 0.6.4 | Delayed workflow triggering for rare changes |
| 0.6.3 | Fixed workflow state management |
| 0.6.2 | Debounce/burst detection for workflows |
| 0.6.1 | Improved configuration naming |
| 0.6.0 | Workflow automation for Raw changes |
| 0.5.2 | Roomba status conversions |
| 0.5.1 | Lock/unlock conversions |
| 0.5.0 | Structured JSON datapoint support |
| 0.4.9 | Enhanced DEBUG logging |
| 0.4.8 | Remove states/ prefix, shorter logs |
| 0.4.7 | Promoted key messages to INFO |
| 0.4.6 | Improved logging levels |
| 0.4.5 | Relative topic parsing for Raw |
| 0.4.4 | Raw handler introduction |

---

## 🚀 Migration Notes

### From v0.4.x to v0.6.x
1. **Configuration Changes** (optional but recommended):
   - Rename `create_missing` → `create_missing_timeseries` in existing configs
   
2. **New Features** (opt-in):
   - Add `mqtt_raw_topics` if you want to use Raw handler
   - Add `trigger_workflows_on_raw_change: true` and workflow settings to enable automation

3. **Backward Compatibility**:
   - All existing configurations continue to work
   - No breaking changes to existing functionality
   - New features are opt-in

---

## 📝 Next Steps

For detailed changelog, see [CHANGELOG.md](CHANGELOG.md)

For configuration reference, see the Home Assistant Add-on configuration UI or `config.json`

For issues or feature requests, visit the GitHub repository.

