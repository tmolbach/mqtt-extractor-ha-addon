"""
Generic handler for writing MQTT payloads to CDF Records.

This handler automatically transforms MQTT JSON payloads for CDF Records:
- Regular attributes pass through directly
- Attributes ending in 'ExternalId' are converted to node references
- Arrays of ExternalIds become arrays of node references
"""

import json
import logging
from typing import Any

from cognite.client import CogniteClient

logger = logging.getLogger(__name__)


def transform_payload(payload: dict, instance_space: str) -> dict:
    """
    Transform MQTT payload to CDF Records properties.
    
    - Regular attributes pass through as-is
    - Attributes ending in 'ExternalId' are converted to direct relations:
      - Single value: {"space": instance_space, "externalId": value}
      - Array value: [{"space": instance_space, "externalId": v} for v in value]
    
    Args:
        payload: Raw MQTT JSON payload
        instance_space: CDF space for node references
        
    Returns:
        Transformed properties dict ready for CDF Records
    """
    properties = {}
    
    for key, value in payload.items():
        if key.endswith('ExternalId'):
            # Strip 'ExternalId' suffix to get target attribute name
            target_attr = key[:-len('ExternalId')]
            
            if value is None:
                # Skip null references
                continue
                
            if isinstance(value, list):
                # Array of references - filter out None/empty values
                refs = [
                    {'space': instance_space, 'externalId': ext_id}
                    for ext_id in value
                    if ext_id
                ]
                if refs:
                    properties[target_attr] = refs
            else:
                # Single reference
                if value:  # Only add if not empty
                    properties[target_attr] = {
                        'space': instance_space,
                        'externalId': str(value)
                    }
        else:
            # Pass through as-is (preserve original value including None)
            properties[key] = value
    
    return properties


def write_record_to_cdf(
    client: CogniteClient,
    payload: dict,
    container_external_id: str,
    records_space: str,
    stream_external_id: str,
    instance_space: str
) -> bool:
    """
    Write a transformed MQTT payload to a CDF Record.
    
    Args:
        client: CogniteClient instance
        payload: Raw MQTT JSON payload
        container_external_id: Target container external ID (e.g., 'AlarmEventRecord')
        records_space: CDF space where the Records containers are defined
        stream_external_id: Stream external ID for writing records
        instance_space: CDF space for node references
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get external_id from payload (support both camelCase and snake_case)
        external_id = payload.get('externalId') or payload.get('external_id')
        if not external_id:
            logger.error("Missing 'externalId' or 'external_id' in payload")
            return False
        
        # Transform payload to CDF properties
        properties = transform_payload(payload, instance_space)
        
        # Remove external_id from properties (it's used as the record ID, not a property)
        properties.pop('external_id', None)
        properties.pop('externalId', None)
        
        # Get name for logging
        name = properties.get('name', 'N/A')
        
        # Single polished log line per alarm event/frame
        msg_type = "AlarmEvent" if "Event" in container_external_id else "AlarmFrame"
        logger.info(f"{msg_type}: {name}")
        
        logger.debug(f"Processing {container_external_id}: {external_id}")
        logger.debug(f"Properties: {json.dumps(properties, default=str)}")
        
        # Create record structure
        record = {
            "space": records_space,
            "externalId": external_id,
            "sources": [{
                "source": {
                    "type": "container",
                    "space": records_space,
                    "externalId": container_external_id
                },
                "properties": properties
            }]
        }
        
        # Log the full record structure before sending
        try:
            logger.debug(f"  Full record payload: {json.dumps(record, indent=2, default=str)}")
        except Exception as log_err:
            logger.debug(f"  Could not serialize record for logging: {log_err}")
        
        # Write to CDF Records API
        logger.debug(f"Writing record to stream: {stream_external_id}")
        response = client.post(
            url=f"/api/v1/projects/{client.config.project}/streams/{stream_external_id}/records",
            json={"items": [record]}
        )
        
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers) if hasattr(response, 'headers') else 'N/A'}")
        
        # Check response status - 200 (OK), 201 (Created), and 202 (Accepted) are all success codes
        if response.status_code in [200, 201, 202]:
            logger.debug(f"Written to CDF Records successfully: {external_id} (HTTP {response.status_code})")
            # Log response body if available for debugging
            try:
                if hasattr(response, 'json'):
                    response_body = response.json()
                    logger.debug(f"Response body: {response_body}")
                elif hasattr(response, 'text') and response.text:
                    logger.debug(f"Response text: {response.text}")
            except Exception as e:
                logger.debug(f"Could not parse response body: {e}")
            return True
        else:
            logger.error(f"Failed to write record to CDF: HTTP {response.status_code}")
            try:
                if hasattr(response, 'json'):
                    error_body = response.json()
                    logger.error(f"  Error response: {error_body}")
                elif hasattr(response, 'text'):
                    logger.error(f"  Error response text: {response.text}")
                else:
                    logger.error(f"  Error response: {response}")
            except Exception as e:
                logger.error(f"  Could not parse error response: {e}")
                logger.error(f"  Raw response: {response}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to write {container_external_id} to CDF Records: {e}")
        # Log the full record structure on error
        try:
            record_dict = {
                'space': records_space,
                'externalId': external_id,
                'sources': [{
                    'source': {
                        'type': 'container',
                        'space': records_space,
                        'externalId': container_external_id
                    },
                    'properties': properties
                }]
            }
            logger.error(f"  Full record payload that failed: {json.dumps(record_dict, indent=2, default=str)}")
        except Exception as log_err:
            logger.error(f"  Could not serialize failed record for logging: {log_err}")
        logger.debug("Full traceback:", exc_info=True)
        return False


class AlarmRecordsHandler:
    """
    Handler for processing alarm messages from MQTT and writing to CDF Records.
    """
    
    def __init__(
        self,
        client: CogniteClient,
        instance_space: str,
        records_space: str,
        stream_external_id: str
    ):
        """
        Initialize the alarm records handler.
        
        Args:
            client: CogniteClient instance
            instance_space: CDF space for node references
            records_space: CDF space where Records containers are defined
            stream_external_id: Stream external ID for writing records
        """
        self.client = client
        self.instance_space = instance_space
        self.records_space = records_space
        self.stream_external_id = stream_external_id
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_written': 0,
            'frames_received': 0,
            'frames_written': 0,
            'errors': 0
        }
    
    def process_message(self, topic: str, payload_bytes: bytes, container_external_id: str) -> bool:
        """
        Process an MQTT message and write to the appropriate CDF Record container.
        
        Args:
            topic: MQTT topic the message was received on
            payload_bytes: Raw message payload bytes
            container_external_id: Target CDF container external ID
            
        Returns:
            True if successful, False otherwise
        """
        # Track statistics
        is_event = 'Event' in container_external_id
        is_frame = 'Frame' in container_external_id
        
        if is_event:
            self.stats['events_received'] += 1
        elif is_frame:
            self.stats['frames_received'] += 1
        
        try:
            # Parse JSON payload
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            logger.debug(f"Incoming message from {topic} -> {container_external_id}")
            
            # Write to CDF Records
            success = write_record_to_cdf(
                client=self.client,
                payload=payload,
                container_external_id=container_external_id,
                records_space=self.records_space,
                stream_external_id=self.stream_external_id,
                instance_space=self.instance_space
            )
            
            if success:
                if 'Event' in container_external_id:
                    self.stats['events_written'] += 1
                elif 'Frame' in container_external_id:
                    self.stats['frames_written'] += 1
                return True
            else:
                self.stats['errors'] += 1
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload from {topic}: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error processing message from {topic}: {e}")
            logger.debug("Full traceback:", exc_info=True)
            self.stats['errors'] += 1
            return False
    
    def get_stats_summary(self) -> str:
        """Get a summary of processing statistics."""
        return (
            f"Events: {self.stats['events_written']}/{self.stats['events_received']} | "
            f"Frames: {self.stats['frames_written']}/{self.stats['frames_received']} | "
            f"Errors: {self.stats['errors']}"
        )

