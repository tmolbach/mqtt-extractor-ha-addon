"""
Generic handler for writing MQTT payloads to CDF data model views.

This handler automatically transforms MQTT JSON payloads for CDF:
- Regular attributes pass through directly
- Attributes ending in 'ExternalId' are converted to node references
- Arrays of ExternalIds become arrays of node references
"""

import json
import logging
from typing import Any

from cognite.client import CogniteClient
from cognite.client.data_classes.data_modeling import NodeApply, NodeId, ViewId

logger = logging.getLogger(__name__)


def transform_payload(payload: dict, instance_space: str) -> dict:
    """
    Transform MQTT payload to CDF data model properties.
    
    - Regular attributes pass through as-is
    - Attributes ending in 'ExternalId' are converted to direct relations:
      - Single value: {"space": instance_space, "externalId": value}
      - Array value: [{"space": instance_space, "externalId": v} for v in value]
    
    Args:
        payload: Raw MQTT JSON payload
        instance_space: CDF space for node references
        
    Returns:
        Transformed properties dict ready for CDF
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


def write_to_cdf(
    client: CogniteClient,
    payload: dict,
    view_external_id: str,
    instance_space: str,
    data_model_space: str,
    data_model_version: str
) -> bool:
    """
    Write a transformed MQTT payload to a CDF data model view.
    
    Args:
        client: CogniteClient instance
        payload: Raw MQTT JSON payload
        view_external_id: Target view external ID (e.g., 'haAlarmEvent')
        instance_space: CDF space for storing the node instance
        data_model_space: CDF space where the data model/view is defined
        data_model_version: Version of the data model view
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get external_id from payload (required field)
        external_id = payload.get('external_id')
        if not external_id:
            logger.error("Missing 'external_id' in payload")
            return False
        
        # Transform payload to CDF properties
        properties = transform_payload(payload, instance_space)
        
        # Remove external_id from properties (it's used as the node ID, not a property)
        properties.pop('external_id', None)
        
        logger.debug(f"Writing to {view_external_id}: {external_id}")
        logger.debug(f"Properties: {json.dumps(properties, indent=2, default=str)}")
        
        # Create node
        view_id = ViewId(
            space=data_model_space,
            external_id=view_external_id,
            version=data_model_version
        )
        
        node = NodeApply(
            space=instance_space,
            external_id=external_id,
            sources=[{
                'source': view_id,
                'properties': properties
            }]
        )
        
        # Write to CDF
        result = client.data_modeling.instances.apply(nodes=[node])
        logger.info(f"Wrote {view_external_id} node: {external_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write to CDF: {e}")
        logger.debug("Full traceback:", exc_info=True)
        return False


class AlarmHandler:
    """
    Handler for processing alarm messages from MQTT and writing to CDF.
    """
    
    def __init__(
        self,
        client: CogniteClient,
        instance_space: str,
        data_model_space: str,
        data_model_version: str
    ):
        """
        Initialize the alarm handler.
        
        Args:
            client: CogniteClient instance
            instance_space: CDF space for storing node instances
            data_model_space: CDF space where data model views are defined
            data_model_version: Version of the data model views
        """
        self.client = client
        self.instance_space = instance_space
        self.data_model_space = data_model_space
        self.data_model_version = data_model_version
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_written': 0,
            'frames_received': 0,
            'frames_written': 0,
            'errors': 0
        }
    
    def process_message(self, topic: str, payload_bytes: bytes, view_external_id: str) -> bool:
        """
        Process an MQTT message and write to the appropriate CDF view.
        
        Args:
            topic: MQTT topic the message was received on
            payload_bytes: Raw message payload bytes
            view_external_id: Target CDF view external ID
            
        Returns:
            True if successful, False otherwise
        """
        # Track statistics
        if 'Event' in view_external_id:
            self.stats['events_received'] += 1
        elif 'Frame' in view_external_id:
            self.stats['frames_received'] += 1
        
        try:
            # Parse JSON payload
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            logger.debug(f"Processing message from {topic} -> {view_external_id}")
            
            # Write to CDF
            success = write_to_cdf(
                client=self.client,
                payload=payload,
                view_external_id=view_external_id,
                instance_space=self.instance_space,
                data_model_space=self.data_model_space,
                data_model_version=self.data_model_version
            )
            
            if success:
                if 'Event' in view_external_id:
                    self.stats['events_written'] += 1
                elif 'Frame' in view_external_id:
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

