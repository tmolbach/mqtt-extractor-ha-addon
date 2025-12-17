"""
Generic Data Model Writer Handler

Flexible handler that maps MQTT topics to CDF Data Model views based on configuration.
Supports writing to any view by routing messages based on topic patterns.

Example configuration in extractor.yaml:
  data_model_writes:
    - topic: "sensors/temperature"
      view_external_id: "haSensor"
      instance_space: "sp_instance"
      data_model_space: "sp_enterprise_schema_space"
      data_model_version: "v1"
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Generator, Tuple, Union, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration for data model writes - will be set by main.py
# Structure: { "topic_pattern": { "view_external_id": ..., "instance_space": ..., ... } }
data_model_writes_config: Dict[str, Dict] = {}


def sanitize_external_id(ext_id: str, prefix: str = "hal_") -> str:
    """
    Ensure external ID meets CDF naming requirements.
    Must start with a letter, contain only letters/numbers/underscores, and end with letter/number.
    Pattern: ^[a-zA-Z]([a-zA-Z0-9_]{0,253}[a-zA-Z0-9])?$
    
    Args:
        ext_id: The external ID to sanitize
        prefix: Prefix to use if needed (default: "ha_")
                - "haa_" for assets/properties (Home Assistant Asset)
                - "has_" for source systems (Home Assistant Source)
    """
    if not ext_id:
        return ext_id
    
    # Convert to string if not already
    ext_id = str(ext_id)
    
    # Check if it already has the correct prefix
    already_has_correct_prefix = ext_id.startswith(prefix)
    
    # Strip any existing Home Assistant prefix (including the correct one)
    # We'll re-add the correct prefix later if needed
    ha_prefixes = ['haa_', 'has_', 'ha_']
    original_had_prefix = False
    for ha_prefix in ha_prefixes:
        if ext_id.startswith(ha_prefix):
            ext_id = ext_id[len(ha_prefix):]
            original_had_prefix = True
            break
    
    # CDF allows: letters, numbers, underscores, dots, hyphens
    # Only replace truly invalid characters (spaces, special chars)
    sanitized = ''
    for char in ext_id:
        if char.isalnum() or char in ('_', '.', '-'):
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
    
    # Generic fallback - pass through common properties
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
        
        view_external_id = view_config.get('view_external_id')
        logger.debug(f"Found config for topic {topic}: view={view_external_id}")
        
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
        
        # Sanitize external_id to meet CDF naming requirements
        original_ext_id = external_id
        external_id = sanitize_external_id(external_id, prefix="ha_")
        if external_id != original_ext_id:
            logger.debug(f"Sanitized external_id: {original_ext_id} -> {external_id}")

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
            logger.debug(f"Wrote {view_external_id}: {external_id}")
        except Exception as e:
            logger.error(f"Failed to write {view_external_id} to CDF: {e}")
            logger.error(f"Failed external_id: {external_id}")
            logger.error(f"Failed properties: {json.dumps(properties, indent=2, default=str)}")
            logger.debug("Full traceback:", exc_info=True)

    except Exception as e:
        logger.exception("Unexpected error in datamodel handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)

