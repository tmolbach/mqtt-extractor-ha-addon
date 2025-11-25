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
            logger.debug("Parsed as numeric: topic=%s, raw_payload='%s', parsed_value=%s (type=%s)", 
                        topic, payload_str, value, type(value).__name__)
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
                    # Check if this is a structured CDF datapoint with value, timestamp, external_id
                    if 'value' in data and 'timestamp' in data:
                        # Structured datapoint format
                        raw_value = data['value']
                        
                        # Convert value using existing logic
                        converted_value = None
                        if isinstance(raw_value, (int, float)):
                            converted_value = raw_value
                        elif isinstance(raw_value, bool):
                            converted_value = 1 if raw_value else 0
                        elif isinstance(raw_value, str):
                            # Try numeric conversion
                            try:
                                converted_value = float(raw_value)
                            except ValueError:
                                # Try boolean conversion
                                value_lower = raw_value.lower()
                                true_values = {'on', 'yes', 'true', '1', 'active', 'enabled', 'open', 'high', 'online', 'arm', 'armed'}
                                false_values = {'off', 'no', 'false', '0', 'inactive', 'disabled', 'closed', 'low', 'offline', 'disarm', 'disarmed'}
                                
                                if value_lower in true_values:
                                    converted_value = 1
                                elif value_lower in false_values:
                                    converted_value = 0
                        
                        if converted_value is not None:
                            # Use provided timestamp (convert to int milliseconds if needed)
                            ts = int(data['timestamp']) if isinstance(data['timestamp'], float) else data['timestamp']
                            
                            # Use provided external_id if available, otherwise derive from topic
                            if 'external_id' in data:
                                ext_id = main.clean_topic_for_external_id(data['external_id'])
                            else:
                                ext_id = external_id
                            
                            logger.debug("Parsed structured JSON: topic=%s, external_id=%s, value=%s->%s (type=%s), timestamp=%d", 
                                       topic, ext_id, raw_value, converted_value, type(converted_value).__name__, ts)
                            yield ext_id, ts, converted_value
                            return
                        else:
                            logger.debug("Skipped (structured JSON with unconvertible value): %s = %s", topic, payload_str[:80])
                            return
                    
                    # Not structured format, try extracting numeric values from the JSON object
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
                        logger.debug("Parsed from JSON: topic=%s, raw_payload='%s', json_key='%s', parsed_value=%s (type=%s)", 
                                   topic, payload_str[:80], key, value, type(value).__name__)
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
            logger.debug("Parsed as boolean: topic=%s, raw_payload='%s', parsed_value=1 (true)", topic, payload_str)
            yield external_id, timestamp, 1
            return
        elif payload_lower in false_values:
            logger.debug("Parsed as boolean: topic=%s, raw_payload='%s', parsed_value=0 (false)", topic, payload_str)
            yield external_id, timestamp, 0
            return
        
        # It's a string value we can't convert
        logger.debug("Skipped (unconvertible string): %s = '%s'", topic, payload_str[:50])
        
    except UnicodeDecodeError as e:
        logger.warning("Failed to decode payload from topic %s: %s", topic, e)
    except Exception as e:
        logger.warning("Unexpected error parsing payload from topic %s: %s", topic, e)


