"""
HA MQTT Alarm Records Extractor for Cognite Data Fusion

Main entry point that:
- Loads configuration from config.yaml
- Connects to MQTT broker
- Subscribes to alarm event and frame topics
- Routes messages to the handler for CDF Records writes
"""

import logging
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
import yaml
from cognite.client import CogniteClient, ClientConfig
from cognite.client.credentials import OAuthClientCredentials

from .handler import AlarmRecordsHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-5s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration loaded from config.yaml."""
    # Cognite settings
    cognite_project: str
    cognite_cluster: str
    cognite_client_id: str
    cognite_client_secret: str
    cognite_token_url: str
    cognite_scopes: str
    
    # MQTT settings
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_qos: int
    
    # Records settings
    instance_space: str
    records_space: str
    stream_external_id: str
    
    # Subscriptions (topic -> container mapping)
    subscriptions: list
    
    # Logging
    log_level: str = "INFO"


def load_config(config_path: str = "/app/config.yaml") -> Config:
    """Load configuration from YAML file."""
    logger.debug(f"Loading configuration from {config_path}")
    
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return Config(
        cognite_project=data['cognite']['project'],
        cognite_cluster=data['cognite']['cluster'],
        cognite_client_id=data['cognite']['client_id'],
        cognite_client_secret=data['cognite']['client_secret'],
        cognite_token_url=data['cognite']['token_url'],
        cognite_scopes=data['cognite']['scopes'],
        mqtt_host=data['mqtt']['host'],
        mqtt_port=data['mqtt']['port'],
        mqtt_username=data['mqtt'].get('username', ''),
        mqtt_password=data['mqtt'].get('password', ''),
        mqtt_qos=data['mqtt'].get('qos', 1),
        instance_space=data.get('instance_space', 'ha_instances'),
        records_space=data.get('records_space', 'ha_records'),
        stream_external_id=data.get('stream_external_id', 'ha_alarm_stream'),
        subscriptions=data.get('subscriptions', []),
        log_level=data.get('log_level', 'INFO')
    )


def create_cognite_client(config: Config) -> CogniteClient:
    """Create and return a CogniteClient instance."""
    logger.debug(f"Connecting to Cognite: {config.cognite_cluster}/{config.cognite_project}")
    
    credentials = OAuthClientCredentials(
        token_url=config.cognite_token_url,
        client_id=config.cognite_client_id,
        client_secret=config.cognite_client_secret,
        scopes=config.cognite_scopes.split(',')
    )
    
    client_config = ClientConfig(
        client_name="mqtt-alarm-records-extractor",
        project=config.cognite_project,
        base_url=f"https://{config.cognite_cluster}.cognitedata.com",
        credentials=credentials
    )
    
    client = CogniteClient(client_config)
    
    # Verify connection
    try:
        status = client.iam.token.inspect()
        logger.debug(f"Connected to CDF as: {status.subject}")
    except Exception as e:
        logger.error(f"Failed to connect to CDF: {e}")
        raise
    
    return client


class MQTTAlarmRecordsExtractor:
    """Main extractor class that connects MQTT to CDF Records."""
    
    def __init__(self, config: Config, cdf_client: CogniteClient):
        self.config = config
        self.cdf_client = cdf_client
        
        # Build topic -> container mapping
        self.topic_container_map = {}
        for sub in config.subscriptions:
            topic = sub['topic']
            container = sub['container']
            self.topic_container_map[topic] = container
            logger.debug(f"Subscription: {topic} -> {container}")
        
        # Create handler
        self.handler = AlarmRecordsHandler(
            client=cdf_client,
            instance_space=config.instance_space,
            records_space=config.records_space,
            stream_external_id=config.stream_external_id
        )
        
        # MQTT client
        self.mqtt_client: Optional[mqtt.Client] = None
        
        # Stop signal
        self.stop_event = threading.Event()
        
        # Statistics tracking
        self.last_stats_time = time.time()
        self.stats_interval = 60  # Log stats every 60 seconds
    
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Callback when MQTT client connects."""
        if reason_code == 0:
            logger.info(f"Connected to MQTT broker: {self.config.mqtt_host}:{self.config.mqtt_port}")
            
            # Subscribe to all configured topics
            for topic in self.topic_container_map.keys():
                client.subscribe(topic + "/#", qos=self.config.mqtt_qos)
                logger.debug(f"Subscribed to: {topic}/#")
            
            logger.info("Ready for alarm events and frames")
        else:
            logger.error(f"Failed to connect to MQTT broker: {reason_code}")
    
    def _on_disconnect(self, client, userdata, reason_code, *args, **kwargs):
        """Callback when MQTT client disconnects."""
        if reason_code != 0:
            logger.warning(f"Disconnected from MQTT broker: {reason_code}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when MQTT message is received."""
        topic = msg.topic
        
        # Find matching subscription (topic prefix match)
        container = None
        for sub_topic, sub_container in self.topic_container_map.items():
            if topic.startswith(sub_topic):
                container = sub_container
                break
        
        if container is None:
            logger.debug(f"No matching container for topic: {topic}")
            return
        
        logger.debug(f"Received message on {topic}")
        
        # Process the message
        self.handler.process_message(topic, msg.payload, container)
        
        # Periodic stats logging
        now = time.time()
        if now - self.last_stats_time >= self.stats_interval:
            logger.debug(f"Stats: {self.handler.get_stats_summary()}")
            self.last_stats_time = now
    
    def start(self):
        """Start the extractor."""
        logger.debug("Starting MQTT Alarm Records Extractor...")
        
        # Create MQTT client
        self.mqtt_client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="mqtt-alarm-records-extractor",
            protocol=mqtt.MQTTv5
        )
        
        # Set callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message
        
        # Set credentials if provided
        if self.config.mqtt_username:
            self.mqtt_client.username_pw_set(
                self.config.mqtt_username,
                self.config.mqtt_password
            )
        
        # Connect to MQTT broker
        logger.debug(f"Connecting to MQTT: {self.config.mqtt_host}:{self.config.mqtt_port}")
        self.mqtt_client.connect(
            self.config.mqtt_host,
            self.config.mqtt_port,
            keepalive=60
        )
        
        # Start MQTT loop in background
        self.mqtt_client.loop_start()
        
        # Wait for stop signal
        try:
            while not self.stop_event.is_set():
                self.stop_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        self.stop()
    
    def stop(self):
        """Stop the extractor."""
        logger.info("Stopping MQTT Alarm Records Extractor...")
        
        self.stop_event.set()
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            try:
                self.mqtt_client.disconnect()
            except Exception as e:
                logger.debug(f"Error during disconnect: {e}")
        
        # Final summary
        stats = self.handler.stats
        logger.info("")
        logger.info("MQTT Alarm Records Extractor - Stopped")
        logger.info("Final Statistics:")
        logger.info("  Alarm Events: %d/%d written/received", stats['events_written'], stats['events_received'])
        logger.info("  Alarm Frames: %d/%d written/received", stats['frames_written'], stats['frames_received'])
        if stats['errors'] > 0:
            logger.info("  Errors: %d", stats['errors'])


def main():
    """Main entry point."""
    # Load configuration
    config_path = "/app/config.yaml"
    if not Path(config_path).exists():
        # For local testing
        config_path = "config.yaml"
    
    config = load_config(config_path)
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    
    # Create CDF client
    cdf_client = create_cognite_client(config)
    
    # Create and start extractor
    extractor = MQTTAlarmRecordsExtractor(config, cdf_client)
    
    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.debug(f"Received signal {signum}")
        extractor.stop_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start extractor
    extractor.start()


if __name__ == "__main__":
    main()

