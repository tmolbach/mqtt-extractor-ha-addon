import logging
import time

logger = logging.getLogger(__name__)


def parse(payload: bytes, topic: str):
    """
    Parse MQTT payloads - handles numeric, string, and JSON values.
    
    - Numeric values (e.g., "20.66", "44.21") -> float/int
    - Boolean strings (e.g., "ON", "OFF", "true", "false") -> 1/0
    - JSON objects with single numeric value -> extracts that value
    - Other strings and multi-value JSON -> skipped
    """
    try:
        # Decode bytes to string
        payload_str = payload.decode('utf-8').strip()
        
        if not payload_str:
            logger.debug("Skipping empty payload from topic %s", topic)
            return
        
        # Clean the topic for use as external ID (remove 'states/' prefix, etc.)
        # Note: We return the cleaned ID, and main.py will add the prefix
        from . import main
        external_id = main.clean_topic_for_external_id(topic)
        
        # Use current timestamp in milliseconds
        timestamp = int(time.time() * 1000)
        
        # Try to parse as numeric first
        try:
            value = float(payload_str)
            logger.debug("Parsed numeric value - Topic: %s, Value: %s, Timestamp: %d", topic, value, timestamp)
            yield external_id, timestamp, value
            return
        except ValueError:
            # Not numeric - continue to check other formats
            pass
        
        # Check if it's JSON (starts with { or [)
        if payload_str.startswith('{'):
            try:
                import json
                data = json.loads(payload_str)
                
                if isinstance(data, dict):
                    # Extract numeric values from the JSON object
                    numeric_values = {}
                    for key, val in data.items():
                        if isinstance(val, (int, float)):
                            numeric_values[key] = val
                        # Also check for boolean values in JSON
                        elif isinstance(val, bool):
                            numeric_values[key] = 1 if val else 0
                    
                    # If there's exactly one numeric value, use it
                    if len(numeric_values) == 1:
                        key, value = next(iter(numeric_values.items()))
                        logger.debug("Extracted single value from JSON - Topic: %s, Key: %s, Value: %s", 
                                   topic, key, value)
                        yield external_id, timestamp, value
                        return
                    elif len(numeric_values) > 1:
                        # Multiple numeric values - skip for now
                        logger.debug("Skipped (multi-value JSON): %s = %s", topic, payload_str[:80])
                        return
                    else:
                        # No numeric values in JSON
                        logger.debug("Skipped (non-numeric JSON): %s = %s", topic, payload_str[:80])
                        return
                else:
                    # JSON but not a dict (e.g., array)
                    logger.debug("Skipped (JSON array): %s = %s", topic, payload_str[:80])
                    return
                    
            except json.JSONDecodeError:
                # Looks like JSON but isn't valid - treat as string below
                pass
        
        # Check if it's a boolean-like string
        payload_lower = payload_str.lower()
        
        # Define boolean mappings (case-insensitive)
        true_values = {'on', 'yes', 'true', '1', 'active', 'enabled', 'open', 'high', 'online', 'arm', 'armed'}
        false_values = {'off', 'no', 'false', '0', 'inactive', 'disabled', 'closed', 'low', 'offline', 'disarm', 'disarmed'}
        
        if payload_lower in true_values:
            logger.debug("Boolean string '%s' -> 1 (topic: %s)", payload_str, topic)
            yield external_id, timestamp, 1
            return
        elif payload_lower in false_values:
            logger.debug("Boolean string '%s' -> 0 (topic: %s)", payload_str, topic)
            yield external_id, timestamp, 0
            return
        
        # It's a string value we can't convert
        logger.debug("Skipped (unconvertible string): %s = '%s'", topic, payload_str[:50])
        
    except UnicodeDecodeError as e:
        logger.warning("Failed to decode payload from topic %s: %s", topic, e)
    except Exception as e:
        logger.warning("Unexpected error parsing payload from topic %s: %s", topic, e)


