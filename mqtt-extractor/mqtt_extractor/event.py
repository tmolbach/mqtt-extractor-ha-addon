import json
import logging
import time
from typing import Generator, Tuple, Union, Any

logger = logging.getLogger(__name__)


def parse(payload: bytes, topic: str, client: Any = None, subscription_topic: str = None) -> Generator[Tuple[str, int, Union[int, float, str]], None, None]:
    """
    Parse alarm event MQTT payloads and write to CDF data model (haAlarmEvent view).
    
    Expected payload format:
    {
        "type": "ALARM_START" | "ALARM_END",
        "start_time": timestamp_ms,
        "end_time": timestamp_ms (for ALARM_END),
        "external_id_prefix": "prefix_for_occurrence_",
        "alarm_definition_id": "definition_external_id",
        "message": "Human readable message",
        "value_raw": "on" | "off" | numeric,
        "metadata": {
            "source": "Home Assistant",
            "trigger_entity": "entity_id"
        }
    }
    
    Topic structure: events/{alarm_entity_id}
    """
    if not client:
        logger.error("CDF Client not provided to event handler")
        return

    try:
        # Decode payload
        try:
            payload_str = payload.decode('utf-8').strip()
        except UnicodeDecodeError:
            logger.warning("Failed to decode payload for topic %s", topic)
            return

        if not payload_str:
            return

        # Parse JSON
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON for topic %s: %s", topic, e)
            return

        if not isinstance(data, dict):
            logger.debug("Payload is not a JSON object for topic %s, skipping", topic)
            return

        # Extract required fields
        event_type = data.get('type')
        if event_type not in ['ALARM_START', 'ALARM_END']:
            logger.warning("Invalid or missing event type for topic %s: %s", topic, event_type)
            return

        # Get alarm event handler config (set by main.py)
        from . import main as main_module
        alarm_config = getattr(main_module, 'alarm_event_config', {})
        
        if not alarm_config.get('enabled'):
            logger.debug("Alarm event handler not enabled, skipping")
            return

        instance_space = alarm_config.get('instance_space')
        if not instance_space:
            logger.error("Instance space not configured for alarm events")
            return

        # Extract data from payload (support both camelCase and snake_case)
        start_time_raw = data.get('startTime') or data.get('start_time')
        end_time_raw = data.get('endTime') or data.get('end_time')
        external_id_prefix = data.get('externalIdPrefix') or data.get('external_id_prefix', '')
        alarm_definition_id = data.get('definition') or data.get('alarm_definition_id')
        message = data.get('message', '')
        value_raw = data.get('valueRaw') or data.get('value_raw')
        metadata = data.get('metadata', {})
        trigger_entity = metadata.get('triggerEntity') or metadata.get('trigger_entity', '')
        
        # Helper function to normalize timestamps to ISO 8601 string for CDF
        def normalize_timestamp(ts):
            """Convert timestamp to ISO 8601 string format required by CDF."""
            if ts is None:
                return None
            
            from datetime import datetime, timezone
            
            # If it's already a string, return as-is (assuming it's already ISO format)
            if isinstance(ts, str):
                return ts
            
            # If it's a number, treat as milliseconds since epoch
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                return dt.isoformat().replace('+00:00', 'Z')
            
            return None
        
        # Normalize timestamps for CDF (must be ISO 8601 strings)
        start_time = normalize_timestamp(start_time_raw)
        end_time = normalize_timestamp(end_time_raw)
        
        # For external ID generation, we need milliseconds
        # Extract numeric timestamp for external ID
        if isinstance(start_time_raw, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time_raw.replace('Z', '+00:00'))
                start_time_ms = int(dt.timestamp() * 1000)
            except Exception as e:
                logger.warning(f"Failed to parse start_time '{start_time_raw}': {e}")
                start_time_ms = int(time.time() * 1000)  # Fallback to now
        else:
            start_time_ms = start_time_raw or int(time.time() * 1000)

        # Generate external ID for this occurrence
        # If it's an ALARM_START, create new occurrence with timestamp
        # If it's an ALARM_END, we need to find and update the existing occurrence
        if event_type == 'ALARM_START':
            external_id = f"{external_id_prefix}{start_time_ms}"
        else:
            # For ALARM_END, try to find the most recent open alarm
            external_id = f"{external_id_prefix}{start_time_ms}"

        logger.info(f"Processing {event_type} for alarm: {alarm_definition_id}")
        logger.debug(f"External ID: {external_id}, start: {start_time}, end: {end_time}")

        # Import required CDF data classes
        from cognite.client.data_classes.data_modeling import NodeApply, ViewId, NodeOrEdgeData, NodeId

        # Get view configuration
        view_external_id = alarm_config.get('view_external_id', 'haAlarmEvent')
        data_model_space = alarm_config.get('data_model_space', 'sp_enterprise_schema_space')
        data_model_version = alarm_config.get('data_model_version', 'v1')

        view_id = ViewId(
            space=data_model_space,
            external_id=view_external_id,
            version=data_model_version
        )

        # Prepare properties for the alarm event
        properties = {
            'name': message or f"Alarm occurrence {external_id}",
            'description': f"Alarm event from {trigger_entity}",
            'sourceContext': 'MQTT',
            'sourceId': external_id,
            'startTime': start_time,
            'valueAtTrigger': str(value_raw) if value_raw is not None else None,
            'triggerEntity': trigger_entity,
        }

        # Add end time if this is an ALARM_END event
        if event_type == 'ALARM_END' and end_time:
            properties['endTime'] = end_time

        # Add reference to alarm definition if provided
        if alarm_definition_id:
            properties['definition'] = {
                'space': instance_space,
                'externalId': alarm_definition_id
            }

        # Add source system reference if configured
        source_system = alarm_config.get('source_system', 'MQTT')
        properties['source'] = {
            'space': instance_space,
            'externalId': source_system
        }

        # Add tags from metadata if available
        tags = []
        if 'source' in metadata:
            tags.append(f"source:{metadata['source']}")
        if trigger_entity:
            tags.append(f"entity:{trigger_entity}")
        if tags:
            properties['tags'] = tags

        # Create or update the alarm event node
        node = NodeApply(
            space=instance_space,
            external_id=external_id,
            sources=[
                NodeOrEdgeData(
                    source=view_id,
                    properties=properties
                )
            ]
        )

        try:
            result = client.data_modeling.instances.apply(nodes=[node])
            logger.info(f"Alarm event {event_type}: {external_id} written to CDF")
            logger.debug(f"Properties: {properties}")
        except Exception as e:
            logger.error(f"Failed to write alarm event to CDF: {e}")
            logger.debug("Full traceback:", exc_info=True)

    except Exception as e:
        logger.exception("Unexpected error in event handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)

