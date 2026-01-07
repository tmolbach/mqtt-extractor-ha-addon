"""
Generic Data Model Writer Handler

Flexible handler that maps MQTT topics to CDF Data Model views based on configuration.
Supports writing to any view by routing messages based on topic patterns.

Example configuration in extractor.yaml:
  data_model_writes:
    - topic: "events/alarms/log"
      view_external_id: "haAlarmEvent"
      instance_space: "sp_75_nsunkenmeadow"
      data_model_space: "sp_enterprise_schema_space"
      data_model_version: "v1"
    - topic: "events/alarms/frame"
      view_external_id: "haAlarmFrame"
      instance_space: "sp_75_nsunkenmeadow"
      data_model_space: "sp_enterprise_schema_space"
      data_model_version: "v1"
"""

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Generator, Tuple, Union, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration for data model writes - will be set by main.py
# Structure: { "topic_pattern": { "view_external_id": ..., "instance_space": ..., ... } }
data_model_writes_config: Dict[str, Dict] = {}

# Retry queue for failed CDF writes (internet outage, etc.)
# List of (timestamp, topic, payload_bytes, view_config_dict)
_failed_writes_queue: deque = deque()

# Maximum time to retry failed writes (seconds) - default 24 hours
_failed_write_timeout = 86400

# Maximum size for failed writes queue - prevent unbounded growth
_max_failed_queue_size = 10000

# Track last successful write time to detect connectivity restoration
_last_successful_write = time.time()


def normalize_timestamp(ts) -> Optional[str]:
    """Convert timestamp to ISO 8601 string format required by CDF."""
    if ts is None:
        return None
    
    # If it's already a string, return as-is (assuming it's already ISO format)
    if isinstance(ts, str):
        return ts
    
    # If it's a number, treat as milliseconds since epoch
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
        return dt.isoformat().replace('+00:00', 'Z')
    
    return None


def timestamp_to_ms(ts) -> int:
    """Convert various timestamp formats to milliseconds since epoch."""
    if ts is None:
        return int(time.time() * 1000)
    
    if isinstance(ts, (int, float)):
        # Assume it's already milliseconds if it's a large number
        if ts > 1e12:
            return int(ts)
        # Otherwise assume seconds
        return int(ts * 1000)
    
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except Exception:
            return int(time.time() * 1000)
    
    return int(time.time() * 1000)


def find_matching_config(topic: str) -> Optional[Dict]:
    """
    Find the configuration that matches the given topic.
    Supports exact matches and wildcard patterns.
    """
    # First try exact match
    if topic in data_model_writes_config:
        return data_model_writes_config[topic]
    
    # Then try pattern matching (simple prefix matching for now)
    for pattern, config in data_model_writes_config.items():
        if pattern.endswith('/#'):
            prefix = pattern[:-2]
            if topic.startswith(prefix + '/') or topic == prefix:
                return config
        elif pattern.endswith('/+'):
            # Single level wildcard
            prefix = pattern[:-2]
            if topic.startswith(prefix + '/'):
                suffix = topic[len(prefix) + 1:]
                if '/' not in suffix:  # Only match single level
                    return config
    
    return None


def build_node_properties(data: Dict, view_config: Dict) -> Dict:
    """
    Build properties dictionary for a node based on the payload and view configuration.
    Maps payload fields to view properties.
    """
    instance_space = view_config.get('instance_space')
    view_external_id = view_config.get('view_external_id', '')
    
    properties = {}
    
    # Common mappings based on view type
    if 'AlarmEvent' in view_external_id:
        # Map for AlarmEvent view
        # Required from CogniteActivity: name, startTime
        properties['name'] = data.get('name') or data.get('message') or data.get('description', 'Alarm Event')
        properties['description'] = data.get('description') or data.get('message', '')
        
        # startTime (inherited from CogniteSchedulable)
        start_time = data.get('startTime') or data.get('start_time') or data.get('timestamp')
        if start_time:
            properties['startTime'] = normalize_timestamp(start_time)
        
        # Custom AlarmEvent properties
        if 'eventType' in data or 'event_type' in data or 'log_type' in data:
            event_type = data.get('eventType') or data.get('event_type') or data.get('log_type')
            # Map ALARM_START/ALARM_END to ACTIVATED/CLEARED
            if event_type == 'ALARM_START':
                event_type = 'ACTIVATED'
            elif event_type == 'ALARM_END':
                event_type = 'CLEARED'
            properties['eventType'] = event_type
        
        if 'valueSnapshot' in data or 'value_snapshot' in data:
            properties['valueSnapshot'] = str(data.get('valueSnapshot') or data.get('value_snapshot'))
        elif 'valueAtTrigger' in data or 'value_at_trigger' in data:
            # Also populate valueSnapshot from valueAtTrigger for compatibility
            val = data.get('valueAtTrigger') or data.get('value_at_trigger')
            if val is not None:
                properties['valueSnapshot'] = str(val)
                properties['valueAtTrigger'] = str(val)
        
        if 'triggerEntity' in data or 'trigger_entity' in data:
            properties['triggerEntity'] = data.get('triggerEntity') or data.get('trigger_entity')
        
        # definition relationship
        definition = data.get('definition') or data.get('alarm_definition_id')
        if definition:
            if isinstance(definition, str):
                properties['definition'] = {'space': instance_space, 'externalId': definition}
            elif isinstance(definition, dict):
                properties['definition'] = definition
        
        # Source system (CogniteSourceable)
        source = data.get('source')
        if source:
            if isinstance(source, str):
                properties['source'] = {'space': instance_space, 'externalId': source}
            elif isinstance(source, dict):
                properties['source'] = source
        
    elif 'AlarmFrame' in view_external_id:
        # Map for AlarmFrame view
        # CogniteDescribable: name, description
        properties['name'] = data.get('name') or f"Alarm Frame {data.get('external_id', '')}"
        properties['description'] = data.get('description', '')
        
        # AlarmFrame specific properties
        start_time = data.get('startTime') or data.get('start_time')
        if start_time:
            properties['startTime'] = normalize_timestamp(start_time)
        
        end_time = data.get('endTime') or data.get('end_time')
        if end_time:
            properties['endTime'] = normalize_timestamp(end_time)
        
        duration = data.get('durationSeconds') or data.get('duration_seconds')
        if duration is not None:
            properties['durationSeconds'] = float(duration)
        
        trigger_value = data.get('triggerValue') or data.get('trigger_value')
        if trigger_value is not None:
            properties['triggerValue'] = str(trigger_value)
        
        # definition relationship
        definition = data.get('definition') or data.get('alarm_definition_id')
        if definition:
            if isinstance(definition, str):
                properties['definition'] = {'space': instance_space, 'externalId': definition}
            elif isinstance(definition, dict):
                properties['definition'] = definition
        
        # assets relationship (list)
        assets = data.get('assets', [])
        if assets:
            asset_refs = []
            for asset in assets:
                if isinstance(asset, str):
                    asset_refs.append({'space': instance_space, 'externalId': asset})
                elif isinstance(asset, dict):
                    asset_refs.append(asset)
            if asset_refs:
                properties['assets'] = asset_refs
        
        # Source system (CogniteSourceable)
        source = data.get('source')
        if source:
            if isinstance(source, str):
                properties['source'] = {'space': instance_space, 'externalId': source}
            elif isinstance(source, dict):
                properties['source'] = source
    
    else:
        # Generic fallback - pass through common properties
        for key, value in data.items():
            if key in ('external_id', 'externalId', 'type'):
                continue  # Skip metadata fields
            
            # Handle timestamp fields
            if 'time' in key.lower() or 'timestamp' in key.lower():
                normalized = normalize_timestamp(value)
                if normalized:
                    properties[key] = normalized
                continue
            
            # Handle relationship fields (dict with externalId)
            if isinstance(value, dict) and 'externalId' in value:
                if 'space' not in value:
                    value['space'] = instance_space
                properties[key] = value
                continue
            
            # Pass through other values
            if value is not None:
                properties[key] = value
    
    return properties


def parse(payload: bytes, topic: str, client: Any = None, subscription_topic: str = None) -> Generator[Tuple[str, int, Union[int, float, str]], None, None]:
    """
    Parse MQTT payload and write to CDF Data Model based on topic routing configuration.
    
    This is a flexible handler that routes messages to different views based on the topic.
    """
    if not client:
        logger.error("CDF Client not provided to datamodel handler")
        return

    try:
        # Find matching configuration for this topic
        view_config = find_matching_config(topic)
        
        if not view_config:
            logger.debug(f"No data_model_writes config found for topic: {topic}")
            return
        
        logger.debug(f"Found config for topic {topic}: view={view_config.get('view_external_id')}")
        
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
            logger.debug(f"Parsed JSON from {topic}: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON for topic %s: %s", topic, e)
            return

        if not isinstance(data, dict):
            logger.debug("Payload is not a JSON object for topic %s, skipping", topic)
            return

        # Get configuration values
        instance_space = view_config.get('instance_space')
        view_external_id = view_config.get('view_external_id')
        data_model_space = view_config.get('data_model_space', 'sp_enterprise_schema_space')
        data_model_version = view_config.get('data_model_version', 'v1')

        if not instance_space:
            logger.error(f"No instance_space configured for topic {topic}")
            return

        if not view_external_id:
            logger.error(f"No view_external_id configured for topic {topic}")
            return

        # Get or generate external ID for the node
        external_id = data.get('external_id') or data.get('externalId')
        if not external_id:
            # Generate from topic and timestamp
            start_time_ms = timestamp_to_ms(data.get('startTime') or data.get('start_time') or data.get('timestamp'))
            safe_topic = topic.replace('/', '_')
            external_id = f"{safe_topic}_{start_time_ms}"
            logger.debug(f"Generated external_id: {external_id}")

        # Import required CDF data classes
        from cognite.client.data_classes.data_modeling import NodeApply, ViewId, NodeOrEdgeData

        view_id = ViewId(
            space=data_model_space,
            external_id=view_external_id,
            version=data_model_version
        )

        # Build properties based on the view type
        properties = build_node_properties(data, view_config)

        logger.info(f"Writing to {view_external_id}: {external_id}")
        logger.debug(f"Properties: {json.dumps(properties, indent=2, default=str)}")

        # Create the node
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
            logger.info(f"Successfully wrote {view_external_id} node: {external_id}")
            
            # Update last successful write time
            global _last_successful_write
            _last_successful_write = time.time()
            
            # After successful write, retry any failed writes (connectivity restored)
            _retry_failed_writes(client)
        except Exception as e:
            logger.error(f"Failed to write to CDF data model: {e}")
            logger.debug(f"Failed node: space={instance_space}, external_id={external_id}")
            logger.debug(f"Failed properties: {json.dumps(properties, indent=2, default=str)}")
            logger.debug("Full traceback:", exc_info=True)
            
            # Queue for retry
            _queue_failed_write(topic, payload, view_config)

    except Exception as e:
        logger.exception("Unexpected error in datamodel handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)


def _queue_failed_write(topic: str, payload: bytes, view_config: Dict):
    """
    Queue a failed write for retry later.
    
    Args:
        topic: MQTT topic
        payload: Raw message payload bytes
        view_config: View configuration dictionary
    """
    global _failed_writes_queue, _max_failed_queue_size
    
    # Check queue size limit
    if len(_failed_writes_queue) >= _max_failed_queue_size:
        logger.error(f"Failed writes queue full ({_max_failed_queue_size}), dropping oldest message")
        _failed_writes_queue.popleft()
    
    _failed_writes_queue.append((
        time.time(),
        topic,
        payload,
        view_config
    ))
    logger.warning(f"Queued message for retry after CDF write failure (queue size: {len(_failed_writes_queue)})")
    
    # Cleanup expired messages periodically
    if len(_failed_writes_queue) % 100 == 0:
        _cleanup_failed_writes()


def _cleanup_failed_writes():
    """Remove expired messages from failed writes queue."""
    global _failed_writes_queue, _failed_write_timeout
    
    if not _failed_writes_queue:
        return
    
    current_time = time.time()
    initial_size = len(_failed_writes_queue)
    
    # Remove expired messages from the front
    while _failed_writes_queue:
        timestamp, _, _, _ = _failed_writes_queue[0]
        if current_time - timestamp > _failed_write_timeout:
            _failed_writes_queue.popleft()
        else:
            break
    
    removed = initial_size - len(_failed_writes_queue)
    if removed > 0:
        logger.warning(f"Removed {removed} expired failed write(s) from queue")


def _retry_failed_writes(client: Any):
    """
    Retry writing messages that failed due to connectivity issues.
    Called after successful writes to detect when connectivity is restored.
    
    Args:
        client: CogniteClient instance
    """
    global _failed_writes_queue, _last_successful_write
    
    if not _failed_writes_queue:
        return
    
    retried_count = 0
    current_time = time.time()
    
    # Try to retry failed writes
    while _failed_writes_queue:
        timestamp, topic, payload_bytes, view_config = _failed_writes_queue[0]
        
        # Skip expired messages
        if current_time - timestamp > _failed_write_timeout:
            _failed_writes_queue.popleft()
            logger.warning(f"Removed expired failed write (age: {current_time - timestamp:.0f}s)")
            continue
        
        # Try to write by calling parse again
        try:
            # Re-parse and write
            list(parse(payload_bytes, topic, client))
            _failed_writes_queue.popleft()
            retried_count += 1
        except Exception as e:
            # Still failing, stop retrying (will retry again after next successful write)
            logger.debug(f"Retry still failing: {e}")
            break
    
    if retried_count > 0:
        logger.info(f"Retried {retried_count} failed write(s) after connectivity restored")


def retry_failed_writes_periodic(client: Any):
    """
    Periodically retry failed writes (called from main loop).
    This handles the case where connectivity is restored but no new messages arrive.
    
    Args:
        client: CogniteClient instance
    """
    global _failed_writes_queue, _last_successful_write
    
    if not _failed_writes_queue:
        return
    
    current_time = time.time()
    
    # Check if we've had a successful write recently (within last 5 minutes)
    # If so, connectivity is likely restored, try retrying
    if current_time - _last_successful_write < 300:
        _retry_failed_writes(client)
    else:
        # No successful writes recently, but try once anyway to test connectivity
        # This is called periodically from main loop, so limit retries
        if len(_failed_writes_queue) > 0:
            # Try just one message to test connectivity
            _retry_failed_writes(client)






