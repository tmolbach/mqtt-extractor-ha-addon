import json
import logging
import time
from typing import Generator, Tuple, Union, Any

logger = logging.getLogger(__name__)


def sanitize_external_id(ext_id: str, prefix: str = "hal_") -> str:
    """
    Ensure external ID meets CDF naming requirements.
    Must start with a letter, contain only letters/numbers/underscores, and end with letter/number.
    Pattern: ^[a-zA-Z]([a-zA-Z0-9_]{0,253}[a-zA-Z0-9])?$
    
    Args:
        ext_id: The external ID to sanitize
        prefix: Prefix to use if needed (default: "hal_")
                - "hal_" for alarm events (Home Assistant aLarm)
                - "had_" for alarm definitions (Home Assistant alarm Definition)
                - "haa_" for assets/properties (Home Assistant Asset)
                - "has_" for source systems (Home Assistant Source)
                - "haf_" for alarm frames (Home Assistant alarm Frame)
    """
    if not ext_id:
        return ext_id
    
    # Convert to string if not already
    ext_id = str(ext_id)
    
    # Check if it already has the correct prefix
    already_has_correct_prefix = ext_id.startswith(prefix)
    
    # Strip any existing Home Assistant prefix (including the correct one)
    # We'll re-add the correct prefix later if needed
    ha_prefixes = ['hal_', 'had_', 'haa_', 'has_', 'haf_', 'ha_']
    original_had_prefix = False
    for ha_prefix in ha_prefixes:
        if ext_id.startswith(ha_prefix):
            ext_id = ext_id[len(ha_prefix):]
            original_had_prefix = True
            break
    
    # Replace dots and other invalid characters with underscores
    # CDF allows: letters, numbers, underscores only
    sanitized = ''
    for char in ext_id:
        if char.isalnum() or char == '_':
            sanitized += char
        else:
            sanitized += '_'
    
    # Add the prefix if:
    # 1. It starts with a number, OR
    # 2. It had an HA prefix originally (even if it was the wrong one)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"{prefix}{sanitized}"
    elif original_had_prefix:
        # It had a prefix, ensure it has the correct one
        sanitized = f"{prefix}{sanitized}"
    
    # Strip trailing underscores (CDF requires ending with letter or number)
    sanitized = sanitized.rstrip('_')
    
    # If somehow we ended up with an empty string or all underscores, provide fallback
    if not sanitized:
        sanitized = f"{prefix}unknown"
    
    return sanitized


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
            logger.debug(f"Parsed alarm event JSON: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON for topic %s: %s", topic, e)
            return

        if not isinstance(data, dict):
            logger.debug("Payload is not a JSON object for topic %s, skipping", topic)
            return

        # Extract required fields (support both 'type' and 'eventType')
        event_type = data.get('type') or data.get('eventType')
        if event_type not in ['ALARM_START', 'ALARM_END']:
            # This is expected for alarm frames or other non-event payloads
            logger.debug("Skipping non-event payload for topic %s: eventType=%s", topic, event_type)
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
        
        # Check for value at trigger (support multiple field names)
        value_raw = data.get('valueAtTrigger') or data.get('value_at_trigger') or data.get('valueRaw') or data.get('value_raw')
        
        # Check for trigger entity (support both root level and metadata)
        trigger_entity = data.get('triggerEntity') or data.get('trigger_entity', '')
        metadata = data.get('metadata', {})
        if not trigger_entity:
            trigger_entity = metadata.get('triggerEntity') or metadata.get('trigger_entity', '')
        
        # Log the raw data for debugging
        logger.debug(f"Raw alarm data: type={event_type}, definition={alarm_definition_id}, trigger_entity={trigger_entity}, value_raw={value_raw}")
        logger.debug(f"Metadata: {metadata}")
        
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

        # Check if payload provides a complete external_id
        if 'external_id' in data or 'externalId' in data:
            external_id = data.get('external_id') or data.get('externalId')
        else:
            # Generate external ID from prefix and timestamp
            # If it's an ALARM_START, create new occurrence with timestamp
            # If it's an ALARM_END, we need to find and update the existing occurrence
            if event_type == 'ALARM_START':
                external_id = f"{external_id_prefix}{start_time_ms}"
            else:
                # For ALARM_END, try to find the most recent open alarm
                external_id = f"{external_id_prefix}{start_time_ms}"
        
        # Sanitize external_id to meet CDF naming requirements (alarm event)
        external_id = sanitize_external_id(external_id, prefix="hal_")
        
        logger.debug(f"Processing {event_type}: {external_id}")
        logger.debug(f"Alarm definition: {alarm_definition_id}")
        logger.debug(f"Timestamps: start={start_time}, end={end_time}")
        logger.debug(f"Full payload: {json.dumps(data, indent=2, default=str)}")

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

        # Map ALARM_START/ALARM_END to CDF eventType values (mandatory field)
        cdf_event_type = "ACTIVATED" if event_type == "ALARM_START" else "CLEARED"
        
        # Prepare properties for the alarm event
        # Use name and description from payload if available
        event_name = data.get('name') or message or f"Alarm occurrence {external_id}"
        event_description = data.get('description') or (f"Alarm event from {trigger_entity}" if trigger_entity else "Alarm event")
        
        # Use source from payload for sourceContext (free-form string)
        source_context = data.get('source', 'MQTT')
        
        properties = {
            'name': event_name,
            'description': event_description,
            'eventType': cdf_event_type,  # Mandatory: ACTIVATED or CLEARED
            'sourceContext': source_context,
            'sourceId': external_id,
            'startTime': start_time,
        }
        
        # Add valueAtTrigger if available
        if value_raw is not None:
            properties['valueAtTrigger'] = str(value_raw)
        
        # Add triggerEntity if available
        if trigger_entity:
            properties['triggerEntity'] = trigger_entity

        # Add end time if this is an ALARM_END event
        if event_type == 'ALARM_END' and end_time:
            properties['endTime'] = end_time

        # Add reference to alarm definition if provided
        if alarm_definition_id:
            sanitized_def_id = sanitize_external_id(alarm_definition_id, prefix="had_")
            properties['definition'] = {
                'space': instance_space,
                'externalId': sanitized_def_id
            }
        
        # Add asset references if provided in payload
        asset_refs = []
        
        # Check for 'property' field (singular asset reference)
        if 'property' in data:
            property_id = data.get('property')
            if property_id:
                sanitized_property_id = sanitize_external_id(property_id, prefix="haa_")
                asset_refs.append({'space': instance_space, 'externalId': sanitized_property_id})
        
        # Also check for 'assets' array (for backward compatibility or multiple assets)
        assets = data.get('assets', [])
        if assets and isinstance(assets, list):
            for asset in assets:
                if isinstance(asset, str):
                    sanitized_asset_id = sanitize_external_id(asset, prefix="haa_")
                    asset_refs.append({'space': instance_space, 'externalId': sanitized_asset_id})
                elif isinstance(asset, dict) and 'externalId' in asset:
                    sanitized_asset_id = sanitize_external_id(asset['externalId'], prefix="haa_")
                    asset_refs.append({
                        'space': asset.get('space', instance_space),
                        'externalId': sanitized_asset_id
                    })
        
        if asset_refs:
            properties['assets'] = asset_refs

        # Add source system reference
        # Source externalId should always be "MQTT" (the actual source value goes in sourceContext)
        properties['source'] = {
            'space': instance_space,
            'externalId': 'MQTT'
        }

        # Add tags from metadata if available
        tags = []
        if 'source' in metadata:
            tags.append(f"source:{metadata['source']}")
        if trigger_entity:
            tags.append(f"entity:{trigger_entity}")
        if tags:
            properties['tags'] = tags

        # Create the alarm event node
        node = NodeApply(
            space=instance_space,
            external_id=external_id,
            sources=[
                NodeOrEdgeData(
                    source=view_id,
                    properties=properties
                )
            ],
        )

        logger.debug(f"Alarm event properties: {json.dumps(properties, indent=2, default=str)}")
        
        try:
            result = client.data_modeling.instances.apply(nodes=[node])
            logger.debug(f"Alarm event {cdf_event_type}: {external_id} written to CDF")
        except Exception as e:
            logger.error(f"Failed to write alarm event to CDF: {e}")
            logger.error(f"Failed for external_id: {external_id}")
            logger.error(f"Failed properties: {json.dumps(properties, indent=2, default=str)}")
            logger.debug("Full traceback:", exc_info=True)

    except Exception as e:
        logger.exception("Unexpected error in event handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)

