import inspect
import importlib
import io
import logging
import os
import re
import signal
import sys
import time
import warnings
from dataclasses import dataclass, field
from threading import Event
from typing import List

# Suppress the FeaturePreviewWarning from Cognite SDK
warnings.filterwarnings("ignore", message=".*Extractor Extension Model.*")

from cognite.client import CogniteClient
from cognite.client.data_classes import ExtractionPipelineRun, TimeSeries
from cognite.client.data_classes.data_modeling import NodeApply, ViewId, NodeOrEdgeData, NodeId
from cognite.extractorutils.configtools import (
    BaseConfig,
    load_yaml,
)
from cognite.extractorutils.uploader import TimeSeriesUploadQueue
from dotenv import load_dotenv
from paho.mqtt.client import Client as MqttClient

from . import metrics

logger = logging.getLogger(__name__)


@dataclass
class MqttConfig:
    hostname: str
    port: int
    username: str = None
    password: str = None
    client_id: str = "mqtt-extractor"
    clean_session: bool = False

@dataclass
class Handler:
    module: str = "mqtt_extractor.cdf"
    function: str = "parse"
    package: str = None

    def handler(self):
        module = importlib.import_module(self.module, self.package)
        return getattr(module, self.function)


@dataclass
class Subscription:
    topic: str
    handler: Handler = field(default_factory=Handler)
    qos: int = 0

@dataclass
class TargetConfig:
    instance_space: str = None
    data_model_space: str = "sp_enterprise_schema_space"
    data_model_version: str = "v1"
    timeseries_view_external_id: str = "haTimeSeries"
    source_system_space: str = "cdf_cdm"
    source_system_version: str = "v1"

@dataclass
class WorkflowConfig:
    external_id: str = None
    version: str = None
    trigger_interval: int = 300  # Minimum time between triggers (default 5 minutes)
    debounce_window: int = 5  # Wait N seconds after last message before triggering (default 5 seconds)

@dataclass
class AlarmEventConfig:
    instance_space: str = None
    data_model_space: str = "sp_enterprise_schema_space"
    data_model_version: str = "v1"
    view_external_id: str = "haAlarmEvent"
    source_system: str = "MQTT"

@dataclass
class DataModelWriteConfig:
    """Configuration for flexible topic-to-view mapping."""
    topic: str  # MQTT topic pattern (exact or wildcard)
    view_external_id: str  # Target view external ID (e.g., "haAlarmEvent", "haAlarmFrame")
    instance_space: str  # CDF instance space for nodes
    data_model_space: str = "sp_enterprise_schema_space"
    data_model_version: str = "v1"

@dataclass
class Config(BaseConfig):
    mqtt: MqttConfig
    subscriptions: List[Subscription]
    upload_interval: int = 1
    create_missing: bool = True  # create_missing_timeseries in config
    status_pipeline: str = None
    status_interval: int = 60
    target: TargetConfig = None
    workflow: WorkflowConfig = None
    alarm_events: AlarmEventConfig = None
    data_model_writes: List[DataModelWriteConfig] = None  # Flexible topic-to-view mapping
    max_datapoints: int = None  # Stop after this many datapoints (for testing)
    external_id_prefix: str = "mqtt:"  # Prefix on external ID used when creating CDF resources


def config_logging(config_file):
    from yaml import safe_load

    logger_format = "%(asctime)s.%(msecs)03d %(levelname)-8s %(name)-22s %(message)s"
    logging.basicConfig(format=logger_format, datefmt="%Y-%m-%d %H:%M:%S")
    if config_file:
        with open(config_file) as f:
            logging.config.dictConfig(safe_load(f))


_handlers = {}

# Global config for alarm event handler
alarm_event_config = {
    'enabled': False,
    'instance_space': None,
    'data_model_space': 'sp_enterprise_schema_space',
    'data_model_version': 'v1',
    'view_external_id': 'haAlarmEvent',
    'source_system': 'MQTT',
}


def mqtt_topic_matches(topic: str, pattern: str) -> bool:
    """
    Check if an MQTT topic matches a subscription pattern.
    Supports MQTT wildcards:
    - '#' matches multiple levels (must be last character)
    - '+' matches a single level
    """
    if topic == pattern:
        return True
    
    # Handle multi-level wildcard '#'
    if pattern.endswith('/#'):
        prefix = pattern[:-2]  # Remove '/#'
        return topic.startswith(prefix + '/') or topic == prefix
    
    if pattern == '#':
        return True
    
    # Handle single-level wildcard '+'
    if '+' in pattern:
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(pattern_parts) != len(topic_parts):
            return False
        
        for p_part, t_part in zip(pattern_parts, topic_parts):
            if p_part != '+' and p_part != t_part:
                return False
        
        return True
    
    return False


def on_connect(client, userdata, flags, rc):
    if flags.get("session present") != 1:
        # Should have session state for QoS=1
        logger.debug("MQTT connection without session state")
    
    for subscription in config.subscriptions:
        handler = subscription.handler.handler()
        
        # Support wildcard topics: "*" maps to "#" (all topics), "+" for single level
        mqtt_topic = subscription.topic
        if mqtt_topic == "*":
            mqtt_topic = "#"  # MQTT multi-level wildcard
        
        _handlers[mqtt_topic] = handler
        client.subscribe(mqtt_topic, qos=subscription.qos)
        logger.debug("Subscribed to MQTT topic: %s (qos=%d)", mqtt_topic, subscription.qos)
    
    logger.info("Connected to %s:%d (%d subscriptions)", 
               config.mqtt.hostname, config.mqtt.port, len(config.subscriptions))


def on_disconnect(client, userdata, flags):
    # Only log as warning if it's an unexpected disconnect (rc != 0)
    # Expected disconnects (session restoration) are logged at debug
    rc = flags.get('rc', 0) if isinstance(flags, dict) else 0
    if rc == 0:
        logger.debug("Disconnected from %s:%d (reconnecting...)", 
                    config.mqtt.hostname, config.mqtt.port)
    else:
        logger.warning("Disconnected from %s:%d, reconnecting... (rc=%d)", 
                      config.mqtt.hostname, config.mqtt.port, rc)


def mqtt_client(config: MqttConfig):
    logger.debug("Initializing MQTT client (id=%s, clean_session=%s)", 
                config.client_id, config.clean_session)
    client = MqttClient(client_id=config.client_id, clean_session=config.clean_session)
    client.username_pw_set(
        username=config.username,
        password=config.password,
    )
    client.enable_logger()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect_async(config.hostname, config.port)
    client.loop_start()
    return client


def now() -> int:
    return int(1000 * time.time())


def clean_topic_for_external_id(topic: str) -> str:
    """
    Clean up topic for use in external ID.
    Removes 'states/' prefix if present and replaces / with _
    """
    # Remove 'states/' prefix if present
    if topic.startswith('states/'):
        topic = topic[7:]  # len('states/') = 7
    
    # Replace / with _ for external ID
    return topic.replace('/', '_')


def check_timeseries_in_data_model(cdf_client: CogniteClient, config: Config, external_id: str) -> bool:
    """Check if a CogniteTimeSeries instance exists in the data model."""
    if not config.target or not config.target.instance_space:
        return False
    
    try:
        view_id = ViewId(
            space=config.target.data_model_space,
            external_id=config.target.timeseries_view_external_id,
            version=config.target.data_model_version
        )
        
        instances = cdf_client.data_modeling.instances.retrieve(
            nodes=(config.target.instance_space, external_id),
            sources=[view_id]
        )
        
        if len(instances.nodes) > 0:
            logger.debug("Time series exists in data model: %s", external_id)
            return True
        return False
    except Exception as e:
        logger.debug("Error checking data model for %s: %s", external_id, e)
        return False


def ensure_source_system(cdf_client: CogniteClient, config: Config) -> bool:
    """Ensure CogniteSourceSystem 'MQTT' exists in the instance space."""
    if not config.target or not config.target.instance_space:
        return False
    
    source_external_id = "MQTT"
    
    try:
        # Check if source system already exists
        view_id = ViewId(
            space=config.target.source_system_space,
            external_id="CogniteSourceSystem",
            version=config.target.source_system_version
        )
        
        instances = cdf_client.data_modeling.instances.retrieve(
            nodes=(config.target.instance_space, source_external_id),
            sources=[view_id]
        )
        
        if len(instances.nodes) > 0:
            logger.debug("CogniteSourceSystem 'MQTT' already exists in instance space '%s'", config.target.instance_space)
            return True
        
        # Create source system if it doesn't exist
        logger.info("Creating CogniteSourceSystem 'MQTT' in instance space '%s'", config.target.instance_space)
        
        node = NodeApply(
            space=config.target.instance_space,
            external_id=source_external_id,
            sources=[
                NodeOrEdgeData(
                    source=view_id,
                    properties={
                        "name": "MQTT",
                        "description": "MQTT message broker source system"
                    }
                )
            ]
        )
        
        result = cdf_client.data_modeling.instances.apply(nodes=[node])
        logger.info("Created CogniteSourceSystem 'MQTT' successfully")
        return True
        
    except Exception as e:
        logger.warning("Failed to ensure CogniteSourceSystem 'MQTT': %s", e)
        return False


def detect_data_type(value) -> str:
    """Detect the data type of a value and return the appropriate CogniteTimeSeries type."""
    if value is None:
        return "numeric"  # Default to numeric if unknown
    
    # Check if it's a numeric type
    if isinstance(value, (int, float)):
        return "numeric"
    
    # Check if it's a string
    if isinstance(value, str):
        # Try to parse as number - if the MQTT payload is numeric string
        try:
            float(value)
            return "numeric"
        except (ValueError, TypeError):
            # It's a non-numeric string
            return "string"
    
    # Check if it's a dict, list, or other JSON-serializable type
    if isinstance(value, (dict, list)):
        return "json"
    
    # Default to string for other types
    return "string"


def create_timeseries_in_data_model(cdf_client: CogniteClient, config: Config, external_id: str, topic: str, data_type: str = "numeric") -> bool:
    """Create a CogniteTimeSeries instance in the data model."""
    if not config.target or not config.target.instance_space:
        logger.warning("Cannot create time series in data model: target.instance_space not configured")
        return False
    
    try:
        # First, ensure the underlying TimeSeries exists in the classic API
        # Check if it exists, if not create it
        try:
            ts = cdf_client.time_series.retrieve(external_id=external_id)
            if not ts:
                # Create the underlying time series
                # Remove 'states/' prefix from topic for cleaner names
                clean_topic = topic[7:] if topic.startswith('states/') else topic
                name = clean_topic  # Use cleaned topic as name (with slashes)
                description = f"Time series from MQTT topic: {clean_topic}"
                ts = TimeSeries(
                    external_id=external_id,
                    name=name,
                    description=description,
                    metadata={"sourceContext": "MQTT", "topic": topic}
                )
                cdf_client.time_series.create(ts)
                logger.debug("Created underlying TimeSeries: %s", external_id)
        except Exception as e:
            logger.debug("Error checking/creating underlying TimeSeries for %s: %s", external_id, e)
            # Continue anyway - it might be created by the upload queue
        
        # Now create the data model instance
        view_id = ViewId(
            space=config.target.data_model_space,
            external_id=config.target.timeseries_view_external_id,
            version=config.target.data_model_version
        )
        
        # Remove 'states/' prefix from topic for cleaner names
        clean_topic = topic[7:] if topic.startswith('states/') else topic
        name = clean_topic
        description = f"Time series from MQTT topic: {clean_topic}"
        
        # Create the node with properties
        # The CogniteTimeSeries view requires a reference to the actual time series
        # Note: externalId is a reserved property and set at the node level, not in properties
        properties = {
            "name": name,
            "description": description,
            "type": data_type,  # Detected data type: numeric, string, or json
            "source": {
                "space": config.target.instance_space,
                "externalId": "MQTT"
            }
        }
        
        logger.info("Creating TS: %s (type=%s)", topic, data_type)
        
        node = NodeApply(
            space=config.target.instance_space,
            external_id=external_id,
            sources=[
                NodeOrEdgeData(
                    source=view_id,
                    properties=properties
                )
            ]
        )
        
        result = cdf_client.data_modeling.instances.apply(nodes=[node])
        logger.debug("Created time series: %s (topic=%s, type=%s)", external_id, topic, data_type)
        return True
    except Exception as e:
        logger.error("Failed to create time series for topic %s: %s", topic, e)
        return False


def ensure_timeseries_in_data_model(cdf_client: CogniteClient, config: Config, external_id: str, topic: str, value=None):
    """Ensure a CogniteTimeSeries instance exists in the data model, create if missing."""
    if not config.target or not config.target.instance_space:
        return
    
    if not check_timeseries_in_data_model(cdf_client, config, external_id):
        logger.debug("Time series not found in data model, creating: %s", external_id)
        # Detect the data type from the value
        data_type = detect_data_type(value)
        if create_timeseries_in_data_model(cdf_client, config, external_id, topic, data_type):
            # Track statistics
            # Access the stats dict from the calling scope via nonlocal in the future
            pass


def substitute_env_vars(text: str) -> str:
    """Substitute environment variables in the format ${VAR_NAME} in a string."""
    def replace_var(match):
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))  # Return original if not found
    
    return re.sub(r'\$\{([^}]+)\}', replace_var, text)


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Read config file and substitute environment variables
    with open(sys.argv[1]) as config_file:
        config_content = config_file.read()
    
    # Substitute environment variables in config content
    config_content = substitute_env_vars(config_content)
    
    # Load YAML from the processed content
    global config
    config = load_yaml(io.StringIO(config_content), Config)

    config.logger.setup_logging()
    
    # Customize logging format for cleaner output
    # Remove thread names and shorten timestamp for INFO level
    for handler in logging.root.handlers:
        if handler.level <= logging.INFO:
            formatter = logging.Formatter(
                fmt='%(asctime)s [%(levelname)-8s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)

    logger.info("=" * 80)
    logger.info("MQTT to CDF Extractor - Starting")
    logger.info("=" * 80)
    logger.info("Configuration:")
    logger.info("  MQTT Broker: %s:%d", config.mqtt.hostname, config.mqtt.port)
    logger.info("  Subscriptions: %d topics", len(config.subscriptions))
    for subscription in config.subscriptions:
        mqtt_topic = subscription.topic
        if mqtt_topic == "*":
            mqtt_topic = "#"  # MQTT multi-level wildcard
        logger.info("    - %s (QoS=%d)", mqtt_topic, subscription.qos)
    logger.info("  External ID Prefix: %s", config.external_id_prefix)
    if config.target and config.target.instance_space:
        logger.info("  Data Model: ENABLED")
        logger.info("    - Instance Space: %s", config.target.instance_space)
        logger.info("    - View: %s/%s (%s)", config.target.data_model_space, 
                   config.target.timeseries_view_external_id, config.target.data_model_version)
    else:
        logger.info("  Data Model: DISABLED (using classic time series)")
    logger.info("=" * 80)

    # Create Cognite client using config (which may have environment variables substituted)
    cdf_client = config.cognite.get_cognite_client("mqtt-extractor")
    
    # Configure workflow triggering for raw handler if enabled
    if config.workflow and config.workflow.external_id:
        from . import raw
        raw.workflow_config['enabled'] = True
        raw.workflow_config['external_id'] = config.workflow.external_id
        raw.workflow_config['version'] = config.workflow.version
        raw.workflow_config['trigger_interval'] = config.workflow.trigger_interval
        raw.workflow_config['debounce_window'] = config.workflow.debounce_window
        raw.workflow_config['client'] = cdf_client
        logger.info("Workflow triggering enabled: %s (version=%s, interval=%ds, debounce=%ds)", 
                   config.workflow.external_id, config.workflow.version or "latest", 
                   config.workflow.trigger_interval, config.workflow.debounce_window)
    
    # Configure alarm event handler if enabled
    if config.alarm_events and config.alarm_events.instance_space:
        global alarm_event_config
        alarm_event_config['enabled'] = True
        alarm_event_config['instance_space'] = config.alarm_events.instance_space
        alarm_event_config['data_model_space'] = config.alarm_events.data_model_space
        alarm_event_config['data_model_version'] = config.alarm_events.data_model_version
        alarm_event_config['view_external_id'] = config.alarm_events.view_external_id
        alarm_event_config['source_system'] = config.alarm_events.source_system
        logger.info("Alarm event handler enabled: view=%s/%s (space=%s)", 
                   config.alarm_events.data_model_space, config.alarm_events.view_external_id,
                   config.alarm_events.instance_space)
    
    # Configure flexible data model writes (topic-to-view mapping)
    if config.data_model_writes:
        from . import datamodel
        for write_config in config.data_model_writes:
            topic_pattern = write_config.topic
            datamodel.data_model_writes_config[topic_pattern] = {
                'topic': topic_pattern,
                'view_external_id': write_config.view_external_id,
                'instance_space': write_config.instance_space,
                'data_model_space': write_config.data_model_space,
                'data_model_version': write_config.data_model_version,
            }
            logger.info("Data model write configured: %s -> %s/%s (space=%s)",
                       topic_pattern, write_config.data_model_space, 
                       write_config.view_external_id, write_config.instance_space)
    
    # Ensure CogniteSourceSystem 'MQTT' exists in the instance space
    if config.target and config.target.instance_space:
        ensure_source_system(cdf_client, config)

    client = mqtt_client(config.mqtt)

    message_time_stamp = 0
    cdf_time_stamp = 0
    status_time_stamp = 0
    
    # Statistics tracking
    stats = {
        "messages_received": 0,
        "datapoints_uploaded": 0,
        "timeseries_discovered": 0,
        "timeseries_created": 0,
        "messages_skipped": 0,
        "last_status_time": now(),
        "period_datapoints": 0,
        "period_messages": 0,
        "by_topic": {},  # Track statistics per topic
        "start_time": now(),  # Track when extractor started
    }
    
    def log_statistics():
        """Log periodic statistics summary with adaptive intervals"""
        elapsed = (now() - stats["last_status_time"]) / 1000.0  # seconds
        if elapsed > 0:
            msg_rate = stats["period_messages"] / elapsed
            dp_rate = stats["period_datapoints"] / elapsed
            logger.info("Status: %.2f msg/s, %.2f dp/s | Total: %d topics, %d messages, %d datapoints",
                       msg_rate, dp_rate, stats["timeseries_discovered"], 
                       stats["messages_received"], stats["datapoints_uploaded"])
            
            # Log per-topic statistics only for DEBUG level
            if len(stats["by_topic"]) > 1 and logger.isEnabledFor(logging.DEBUG):
                logger.debug("Per-topic breakdown:")
                for topic, topic_stats in sorted(stats["by_topic"].items()):
                    logger.debug("  %s: %d messages, %d datapoints", 
                               topic, topic_stats["messages"], topic_stats["datapoints"])
        
        stats["last_status_time"] = now()
        stats["period_messages"] = 0
        stats["period_datapoints"] = 0
    
    def get_next_status_interval():
        """Calculate next status log interval based on runtime (adaptive logging)"""
        runtime_minutes = (now() - stats["start_time"]) / 60000.0  # minutes
        
        if runtime_minutes < 10:
            return 60000  # 1 minute for first 10 minutes
        elif runtime_minutes < 60:
            return 600000  # 10 minutes for first hour
        else:
            return 3600000  # 1 hour after that

    def post_upload_handler(ts_dps):
        dps = sum(len(ts["datapoints"]) for ts in ts_dps)
        metrics.cdf_data_points.inc(dps)
        logger.debug("Uploaded %d data points", dps)
        logger.debug("Uploaded %r", ts_dps)
        if not ts_dps:
            # calls the handler with empty ts_dps when API call fails.
            # max([]) fails below but could use default=... argument.
            metrics.cdf_requests_failed.inc()
            return
        try:
            if 0:
                time_stamp = max(max(ts["datapoints"]["timestamp"]) for ts in ts_dps)
                nonlocal cdf_time_stamp
                if time_stamp > cdf_time_stamp:
                    cdf_time_stamp = time_stamp
                    metrics.cdf_time_stamp.set(cdf_time_stamp)

            if config.status_pipeline:
                # "success" (should be "seen") heart beat after uploading data points to CDF
                nonlocal status_time_stamp
                t = now()
                if t >= status_time_stamp:
                    cdf_client.extraction_pipeline_runs.create(
                        ExtractionPipelineRun(status="success", external_id=config.status_pipeline)
                    )
                    status_time_stamp = t + 1000 * config.status_interval
        except Exception:
            # Risk of too many stack traces?
            logger.exception("post upload handler")

    stop = Event()
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received, stopping extractor...")
        stop.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Track external IDs we've seen during this session
    seen_external_ids = set()
    datapoint_count = 0
    
    # For data model integration, we need to batch data points by external_id
    # since the upload queue doesn't support instance_id yet
    data_model_buffer = {}  # external_id -> [(timestamp, value), ...]

    with TimeSeriesUploadQueue(
        cdf_client,
        post_upload_function=post_upload_handler,
        max_upload_interval=config.upload_interval,
        trigger_log_level="DEBUG",  # Changed from INFO to reduce verbosity
        thread_name="CDF-Uploader",
        create_missing=config.create_missing,
    ) as upload_queue:
 
        def on_message(client, userdata, message):
            try:
                nonlocal message_time_stamp, datapoint_count
                
                # Ignore messages if we're stopping
                if stop.is_set():
                    return
                
                topic = message.topic
                payload_preview = message.payload[:200] if len(message.payload) <= 200 else message.payload[:200] + b"..."
                logger.debug(
                    "MQTT RX: topic=%s, payload=%s (%d bytes)",
                    topic,
                    payload_preview,
                    len(message.payload),
                )

                # Only track statistics for topics that match subscription filters
                stats["messages_received"] += 1
                stats["period_messages"] += 1

                handle = _handlers.get(message.topic)
                matched_pattern = message.topic
                if not handle:
                    # For wildcard subscriptions, try to find a matching handler
                    for pattern, handler in _handlers.items():
                        if mqtt_topic_matches(message.topic, pattern):
                            handle = handler
                            matched_pattern = pattern
                            logger.info("Matched: %s -> %s", message.topic, pattern)
                            break
                    
                    if not handle:
                        logger.debug("No handler for topic: %s", message.topic)
                        return
                
                # Track per-topic statistics
                if topic not in stats["by_topic"]:
                    stats["by_topic"][topic] = {"messages": 0, "datapoints": 0}
                stats["by_topic"][topic]["messages"] += 1
                
                # Track if we got any datapoints from the handler
                datapoints_from_message = 0
                    
                # Prepare arguments for the handler
                handler_args = [message.payload, message.topic]
                handler_kwargs = {}
                
                # Check if handler accepts client argument
                sig = inspect.signature(handle)
                if 'client' in sig.parameters:
                    handler_kwargs['client'] = cdf_client
                
                # Check if handler accepts subscription_topic argument
                if 'subscription_topic' in sig.parameters:
                    handler_kwargs['subscription_topic'] = matched_pattern
                
                for ts_id, time_stamp, value in handle(*handler_args, **handler_kwargs):
                    datapoints_from_message += 1

                    logger.debug("Handler output: ts_id=%s, value=%r (type=%s), timestamp=%d", 
                                ts_id, value, type(value).__name__, time_stamp)
                    external_id = config.external_id_prefix + ts_id
                    logger.debug("External ID after prefix: %s", external_id)

                    # Check if this is a new external ID we haven't seen yet
                    if external_id not in seen_external_ids:
                        seen_external_ids.add(external_id)
                        stats["timeseries_discovered"] += 1
                        
                        # Ensure CogniteTimeSeries exists in data model
                        # Pass the value so we can detect its data type
                        if not check_timeseries_in_data_model(cdf_client, config, external_id):
                            data_type = detect_data_type(value)
                            if create_timeseries_in_data_model(cdf_client, config, external_id, message.topic, data_type):
                                logger.info("New topic: %s", message.topic)
                                stats["timeseries_created"] += 1

                    # Add to TS upload queue
                    if time_stamp is not None and value is not None:
                        # When using data models, we need to use instance_id with NodeId
                        if config.target and config.target.instance_space:
                            # Buffer data points for data model time series
                            # We'll insert them using the SDK directly
                            logger.debug("Buffering for data model: %s = %r @ %d", external_id, value, time_stamp)
                            if external_id not in data_model_buffer:
                                data_model_buffer[external_id] = []
                            data_model_buffer[external_id].append((time_stamp, value))
                        else:
                            # Use external_id for classic time series via upload queue
                            logger.debug("Queueing for classic TS: %s = %r @ %d", external_id, value, time_stamp)
                            upload_queue.add_to_upload_queue(
                                external_id=external_id, datapoints=[(time_stamp, value)]
                            )
                        datapoint_count += 1
                        stats["datapoints_uploaded"] += 1
                        stats["period_datapoints"] += 1
                        stats["by_topic"][topic]["datapoints"] += 1
                        
                        # Check if we've reached the max datapoints limit
                        if config.max_datapoints and datapoint_count >= config.max_datapoints:
                            logger.info("")
                            logger.info("Reached limit (%d datapoints), stopping", config.max_datapoints)
                            stop.set()

                    if time_stamp > message_time_stamp:
                        message_time_stamp = time_stamp
                
                # Track if message was skipped (no datapoints extracted)
                if datapoints_from_message == 0:
                    stats["messages_skipped"] += 1
                
                # Upload any remaining TS in queue
                upload_queue.upload()
                
                # For data model time series, insert data points using SDK directly
                if config.target and config.target.instance_space and data_model_buffer and not stop.is_set():
                    try:
                        to_insert = []
                        for ext_id, datapoints in data_model_buffer.items():
                            instance_id = NodeId(space=config.target.instance_space, external_id=ext_id)
                            to_insert.append({
                                "instance_id": instance_id,
                                "datapoints": datapoints
                            })
                            logger.debug("Prepared for CDF upload: %s (%d datapoints)", ext_id, len(datapoints))
                            for ts, val in datapoints:
                                logger.debug("  -> ts=%d, value=%r (type=%s)", ts, val, type(val).__name__)
                        
                        if to_insert:
                            logger.debug("Uploading %d time series to CDF data model", len(to_insert))
                            cdf_client.time_series.data.insert_multiple(to_insert)
                            total_dps = sum(len(item["datapoints"]) for item in to_insert)
                            logger.debug("CDF upload complete: %d datapoints across %d time series", total_dps, len(to_insert))
                            data_model_buffer.clear()
                    except Exception as e:
                        logger.error("Failed to upload datapoints to data model: %s", e)
                        logger.debug("Full traceback:", exc_info=True)
                        data_model_buffer.clear()

                # Periodic status logging with adaptive intervals
                current_interval = get_next_status_interval()
                if now() - stats["last_status_time"] >= current_interval:
                    log_statistics()
                
                metrics.messages.inc()
                metrics.message_time_stamp.set(message_time_stamp)
            except Exception as e:
                stats["messages_skipped"] += 1
                logger.error("Error processing MQTT message from %s: %s", message.topic, e)
                logger.debug("Full traceback:", exc_info=True)

        client.on_message = on_message
        
        # Wait for stop signal
        try:
            while not stop.is_set():
                stop.wait(timeout=1.0)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            stop.set()

    if hasattr(config, 'metrics') and config.metrics:
        config.metrics.stop_pushers()

    # Final statistics
    logger.info("")
    logger.info("=" * 80)
    logger.info("MQTT to CDF Extractor - Stopped")
    logger.info("Final Statistics:")
    logger.info("  Topics Discovered: %d", stats["timeseries_discovered"])
    logger.info("  Time Series Created in CDF: %d", stats["timeseries_created"])
    logger.info("  Messages Received: %d", stats["messages_received"])
    logger.info("  Messages Skipped: %d", stats["messages_skipped"])
    logger.info("  Datapoints Uploaded: %d", stats["datapoints_uploaded"])
    
    if stats["by_topic"]:
        logger.info("Per-Topic Breakdown:")
        for topic, topic_stats in sorted(stats["by_topic"].items()):
            logger.info("  %s: %d messages, %d datapoints", 
                       topic, topic_stats["messages"], topic_stats["datapoints"])
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
