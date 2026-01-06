"""
Generic handler for writing MQTT payloads to CDF data model views.

This handler automatically transforms MQTT JSON payloads for CDF:
- Regular attributes pass through directly
- Attributes ending in 'ExternalId' are converted to node references
- Arrays of ExternalIds become arrays of node references
"""

import json
import logging
import time
from collections import deque
from typing import Any, Dict, Optional, Tuple

from cognite.client import CogniteClient
from cognite.client.data_classes.data_modeling import NodeApply, NodeId, ViewId, NodeOrEdgeData

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
        # Get external_id from payload (support both camelCase and snake_case)
        external_id = payload.get('externalId') or payload.get('external_id')
        if not external_id:
            logger.error("Missing 'externalId' or 'external_id' in payload")
            return False
        
        # Transform payload to CDF properties
        properties = transform_payload(payload, instance_space)
        
        # Remove external_id from properties (it's used as the node ID, not a property)
        properties.pop('external_id', None)
        properties.pop('externalId', None)
        
        # Get name for logging
        name = properties.get('name', 'N/A')
        
        # Single polished log line per alarm event/frame
        msg_type = "AlarmEvent" if "Event" in view_external_id else "AlarmFrame"
        logger.info(f"{msg_type}: {name}")
        
        logger.debug(f"Processing {view_external_id}: {external_id}")
        logger.debug(f"Properties: {json.dumps(properties, default=str)}")
        
        # Create node
        view_id = ViewId(
            space=data_model_space,
            external_id=view_external_id,
            version=data_model_version
        )
        
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
        
        # Log the full node structure before sending
        try:
            node_dict = {
                'space': instance_space,
                'external_id': external_id,
                'sources': [{
                    'source': {
                        'space': data_model_space,
                        'external_id': view_external_id,
                        'version': data_model_version
                    },
                    'properties': properties
                }]
            }
            logger.debug(f"  Full node payload: {json.dumps(node_dict, indent=2, default=str)}")
        except Exception as log_err:
            logger.debug(f"  Could not serialize node for logging: {log_err}")
        
        # Write to CDF
        result = client.data_modeling.instances.apply(nodes=[node])
        logger.debug(f"Written to CDF successfully: {external_id}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        # Check if this is the "Cannot auto-create a direct relation target" error
        if "Cannot auto-create a direct relation target" in error_msg or "container constraint" in error_msg:
            # Re-raise this specific error so caller can handle buffering
            raise RuntimeError(f"Frame dependency error: {error_msg}") from e
        logger.error(f"Failed to write {view_external_id} to CDF: {e}")
        # Log the full node structure on error
        try:
            node_dict = {
                'space': instance_space,
                'external_id': external_id,
                'sources': [{
                    'source': {
                        'space': data_model_space,
                        'external_id': view_external_id,
                        'version': data_model_version
                    },
                    'properties': properties
                }]
            }
            logger.error(f"  Full node payload that failed: {json.dumps(node_dict, indent=2, default=str)}")
        except Exception as log_err:
            logger.error(f"  Could not serialize failed node for logging: {log_err}")
        logger.debug("Full traceback:", exc_info=True)
        return False


class AlarmHandler:
    """
    Handler for processing alarm messages from MQTT and writing to CDF.
    
    Handles ordering dependencies: AlarmEvents that reference AlarmFrames are buffered
    until their referenced frames exist in CDF.
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
        
        # Buffer for events waiting for frames to exist
        # Key: frame_external_id, Value: deque of (timestamp, topic, payload_bytes, view_external_id)
        self.pending_events: Dict[str, deque] = {}
        
        # Maximum time to buffer an event (seconds) - default 5 minutes
        self.buffer_timeout = 300
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_written': 0,
            'frames_received': 0,
            'frames_written': 0,
            'errors': 0,
            'events_buffered': 0,
            'events_retried': 0
        }
    
    def _node_exists(self, external_id: str) -> bool:
        """
        Check if a node exists in CDF.
        
        Args:
            external_id: Node external ID to check
            
        Returns:
            True if node exists, False otherwise
        """
        try:
            node_id = NodeId(space=self.instance_space, external_id=external_id)
            result = self.client.data_modeling.instances.retrieve(nodes=[node_id])
            return len(result) > 0
        except Exception as e:
            logger.debug(f"Error checking if node exists {external_id}: {e}")
            return False
    
    def _get_frame_external_id(self, properties: dict) -> Optional[str]:
        """
        Extract frame external ID from properties if present.
        
        Args:
            properties: Transformed properties dict
            
        Returns:
            Frame external ID if present, None otherwise
        """
        frame_ref = properties.get('frame')
        if isinstance(frame_ref, dict):
            return frame_ref.get('externalId')
        return None
    
    def _cleanup_old_buffered_events(self):
        """Remove events from buffer that have exceeded timeout."""
        current_time = time.time()
        frames_to_remove = []
        
        for frame_external_id, event_queue in self.pending_events.items():
            # Remove expired events from the front of the queue
            while event_queue:
                timestamp, _, _, _ = event_queue[0]
                if current_time - timestamp > self.buffer_timeout:
                    event_queue.popleft()
                    logger.warning(f"Removed expired buffered event for frame: {frame_external_id}")
                else:
                    break
            
            # Remove empty queues
            if not event_queue:
                frames_to_remove.append(frame_external_id)
        
        for frame_external_id in frames_to_remove:
            del self.pending_events[frame_external_id]
    
    def _retry_pending_events_for_frame(self, frame_external_id: str):
        """
        Retry writing events that were buffered waiting for this frame.
        
        Args:
            frame_external_id: External ID of the frame that was just written
        """
        if frame_external_id not in self.pending_events:
            return
        
        event_queue = self.pending_events[frame_external_id]
        retried_count = 0
        
        while event_queue:
            timestamp, topic, payload_bytes, view_external_id = event_queue.popleft()
            
            logger.debug(f"Retrying buffered event for frame: {frame_external_id}")
            
            # Try to write the event again
            success = self._write_event_directly(topic, payload_bytes, view_external_id)
            
            if success:
                retried_count += 1
                self.stats['events_retried'] += 1
                self.stats['events_written'] += 1
            else:
                # If it still fails, put it back at the end (might be a different issue)
                logger.warning(f"Retry failed for event referencing frame {frame_external_id}, will retry later")
                event_queue.append((timestamp, topic, payload_bytes, view_external_id))
                break
        
        # Remove the queue if empty
        if not event_queue:
            del self.pending_events[frame_external_id]
        
        if retried_count > 0:
            logger.info(f"Retried {retried_count} buffered event(s) after frame {frame_external_id} was written")
    
    def _write_event_directly(self, topic: str, payload_bytes: bytes, view_external_id: str) -> bool:
        """
        Write an event directly to CDF without buffering checks.
        
        Args:
            topic: MQTT topic
            payload_bytes: Raw message payload bytes
            view_external_id: Target CDF view external ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
            return write_to_cdf(
                client=self.client,
                payload=payload,
                view_external_id=view_external_id,
                instance_space=self.instance_space,
                data_model_space=self.data_model_space,
                data_model_version=self.data_model_version
            )
        except Exception as e:
            logger.error(f"Error writing event directly: {e}")
            return False
    
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
        is_event = 'Event' in view_external_id
        is_frame = 'Frame' in view_external_id
        
        if is_event:
            self.stats['events_received'] += 1
        elif is_frame:
            self.stats['frames_received'] += 1
        
        try:
            # Parse JSON payload
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            logger.debug(f"Incoming message from {topic} -> {view_external_id}")
            
            is_event = 'Event' in view_external_id
            is_frame = 'Frame' in view_external_id
            
            # For AlarmEvents, check if they reference a frame that doesn't exist yet
            if is_event:
                # Transform to check for frame reference
                properties = transform_payload(payload, self.instance_space)
                frame_external_id = self._get_frame_external_id(properties)
                
                if frame_external_id:
                    # Check if the frame exists
                    if not self._node_exists(frame_external_id):
                        # Frame doesn't exist yet, buffer this event
                        logger.debug(f"Buffering event - frame {frame_external_id} does not exist yet")
                        
                        if frame_external_id not in self.pending_events:
                            self.pending_events[frame_external_id] = deque()
                        
                        self.pending_events[frame_external_id].append((
                            time.time(),
                            topic,
                            payload_bytes,
                            view_external_id
                        ))
                        self.stats['events_buffered'] += 1
                        
                        # Cleanup old buffered events periodically
                        self._cleanup_old_buffered_events()
                        
                        return True  # Consider buffered as "handled" for now
            
            # Write to CDF (either frame, or event without frame dependency, or frame exists)
            try:
                success = write_to_cdf(
                    client=self.client,
                    payload=payload,
                    view_external_id=view_external_id,
                    instance_space=self.instance_space,
                    data_model_space=self.data_model_space,
                    data_model_version=self.data_model_version
                )
                
                if success:
                    if is_event:
                        self.stats['events_written'] += 1
                    elif is_frame:
                        self.stats['frames_written'] += 1
                        
                        # After successfully writing a frame, retry any buffered events waiting for it
                        frame_external_id = payload.get('externalId') or payload.get('external_id')
                        if frame_external_id:
                            self._retry_pending_events_for_frame(frame_external_id)
                    
                    return True
                else:
                    self.stats['errors'] += 1
                    return False
            except RuntimeError as write_error:
                error_msg = str(write_error)
                # Check if this is the "Cannot auto-create a direct relation target" error
                if is_event and ("Frame dependency error" in error_msg or "Cannot auto-create a direct relation target" in error_msg or "container constraint" in error_msg):
                    # This means the frame doesn't exist - buffer the event
                    properties = transform_payload(payload, self.instance_space)
                    frame_external_id = self._get_frame_external_id(properties)
                    
                    if frame_external_id:
                        logger.debug(f"Buffering event after write failure - frame {frame_external_id} does not exist")
                        
                        if frame_external_id not in self.pending_events:
                            self.pending_events[frame_external_id] = deque()
                        
                        self.pending_events[frame_external_id].append((
                            time.time(),
                            topic,
                            payload_bytes,
                            view_external_id
                        ))
                        self.stats['events_buffered'] += 1
                        
                        # Cleanup old buffered events periodically
                        self._cleanup_old_buffered_events()
                        
                        return True  # Consider buffered as "handled"
                
                # Other errors - log and count as error
                logger.error(f"Failed to write {view_external_id} to CDF: {write_error}")
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
        buffered_count = sum(len(queue) for queue in self.pending_events.values())
        return (
            f"Events: {self.stats['events_written']}/{self.stats['events_received']} | "
            f"Frames: {self.stats['frames_written']}/{self.stats['frames_received']} | "
            f"Errors: {self.stats['errors']} | "
            f"Buffered: {buffered_count} | "
            f"Retried: {self.stats['events_retried']}"
        )

