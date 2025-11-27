import json
import logging
import time
import threading
from typing import Generator, Tuple, Union, Any

logger = logging.getLogger(__name__)

# Cache for existing databases and tables to avoid repeated API calls
# Structure: {db_name: {table_name: True}}
_existing_resources = {}

# Track databases that have been updated for workflow triggering
# Structure: {db_name: {'last_update': timestamp, 'timer': Timer, 'pending': bool}}
_workflow_pending = {}
_workflow_lock = threading.Lock()

# Workflow configuration - will be set by main.py
workflow_config = {
    'enabled': False,
    'external_id': None,
    'version': None,
    'trigger_interval': 300,  # Minimum time between triggers (default 5 minutes)
    'debounce_window': 5,  # Wait N seconds after last message before triggering (default 5 seconds)
    'client': None,  # CDF client reference
}

def ensure_db_table(client, db_name: str, table_name: str) -> bool:
    """
    Ensure that the database and table exist in CDF Raw.
    Uses caching to minimize API calls.
    """
    if db_name in _existing_resources and table_name in _existing_resources[db_name]:
        return True

    try:
        # Check/Create Database
        if db_name not in _existing_resources:
            try:
                client.raw.databases.create(db_name)
                logger.info(f"Created Raw database: {db_name}")
            except Exception as e:
                # If it fails, check if it exists (Cognite API often throws 400 or 409 if exists)
                # We can also list databases, but create is idempotent-ish usually or we catch error
                # The SDK might raise an error if it exists.
                # Let's verify existence if create failed
                dbs = client.raw.databases.list(limit=None)
                if not any(db.name == db_name for db in dbs):
                    logger.error(f"Failed to create database {db_name}: {e}")
                    return False
            _existing_resources[db_name] = {}

        # Check/Create Table
        if table_name not in _existing_resources[db_name]:
            try:
                client.raw.tables.create(db_name, table_name)
                logger.info(f"Created Raw table: {db_name}.{table_name}")
            except Exception as e:
                # Similar check for table
                tables = client.raw.tables.list(db_name, limit=None)
                if not any(t.name == table_name for t in tables):
                    logger.error(f"Failed to create table {db_name}.{table_name}: {e}")
                    return False
            _existing_resources[db_name][table_name] = True
            
        return True
    except Exception as e:
        logger.error(f"Error ensuring Raw resources {db_name}.{table_name}: {e}")
        return False


def trigger_workflow_if_needed(client, db_name: str):
    """
    Schedule a workflow trigger after a debounce window.
    This ensures we wait for a burst of messages to complete before triggering.
    Throttles workflow triggers per database to avoid excessive executions.
    """
    if not workflow_config.get('enabled'):
        return
    
    if not workflow_config.get('external_id'):
        return
    
    with _workflow_lock:
        current_time = time.time()
        
        # Check if there's already a pending trigger for this database
        if db_name in _workflow_pending:
            pending_info = _workflow_pending[db_name]
            
            # Cancel the existing timer
            if pending_info.get('timer'):
                pending_info['timer'].cancel()
            
            # Update last update time
            pending_info['last_update'] = current_time
            
            logger.debug(f"Workflow trigger for {db_name} rescheduled (burst continuing)")
        else:
            # First message for this database in this burst
            _workflow_pending[db_name] = {
                'last_update': current_time,
                'last_trigger': _workflow_pending.get(db_name, {}).get('last_trigger', 0) if db_name in _workflow_pending else 0,
                'timer': None,
                'pending': True
            }
            logger.debug(f"Workflow trigger for {db_name} scheduled (burst started)")
        
        # Schedule a new timer for the debounce window
        debounce_window = workflow_config.get('debounce_window', 5)
        timer = threading.Timer(debounce_window, _execute_workflow_trigger, args=(client, db_name))
        timer.daemon = True
        _workflow_pending[db_name]['timer'] = timer
        timer.start()


def _execute_workflow_trigger(client, db_name: str):
    """
    Execute the actual workflow trigger after the debounce window.
    Called by the Timer thread.
    """
    with _workflow_lock:
        if db_name not in _workflow_pending or not _workflow_pending[db_name].get('pending'):
            return
        
        pending_info = _workflow_pending[db_name]
        current_time = time.time()
        last_trigger = pending_info.get('last_trigger', 0)
        trigger_interval = workflow_config.get('trigger_interval', 300)
        
        # Check if enough time has elapsed since last actual trigger
        if current_time - last_trigger < trigger_interval:
            logger.info(f"Skipping workflow trigger for {db_name} (last triggered {current_time - last_trigger:.1f}s ago, interval={trigger_interval}s)")
            pending_info['pending'] = False
            return
        
        # Mark as no longer pending before we trigger (in case trigger takes time)
        pending_info['pending'] = False
        pending_info['last_trigger'] = current_time
    
    # Trigger outside the lock to avoid blocking
    try:
        external_id = workflow_config['external_id']
        version = workflow_config.get('version')
        
        # Prepare input data for the workflow
        input_data = {
            'database': db_name,
            'triggered_by': 'mqtt-extractor-raw',
            'timestamp': int(current_time * 1000)
        }
        
        logger.info(f"Triggering workflow: {external_id} (version={version}) for database: {db_name}")
        
        if version:
            execution = client.workflows.executions.run(
                workflow_external_id=external_id,
                version=version,
                input=input_data
            )
        else:
            execution = client.workflows.executions.run(
                workflow_external_id=external_id,
                input=input_data
            )
        
        logger.info(f"Workflow triggered successfully: execution_id={execution.id}")
        
    except Exception as e:
        logger.error(f"Failed to trigger workflow for database {db_name}: {e}")
        logger.debug("Full traceback:", exc_info=True)

def parse(payload: bytes, topic: str, client: Any = None, subscription_topic: str = None) -> Generator[Tuple[str, int, Union[int, float, str]], None, None]:
    """
    Parse payload and write to Cognite Data Fusion Raw.
    Topic structure expected is relative to the subscription_topic (filter).
    
    If subscription_topic is "eastham/75_nsunkenmeadow/registry/#"
    And topic is "eastham/75_nsunkenmeadow/registry/sites/site1"
    
    Database = registry (last part of base)
    Table = sites (first part of suffix)
    Row Key = site1 (rest of suffix or from payload)
    """
    if not client:
        logger.error("CDF Client not provided to raw handler")
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
        except json.JSONDecodeError:
            # Not JSON, ignore for raw handler
            return

        if not isinstance(data, dict):
            logger.debug("Payload is not a JSON object for topic %s, skipping", topic)
            return

        # Derive DB and Table names from topic and subscription_topic
        db_name = None
        table_name = None
        row_key = None
        
        # Strip wildcard from subscription topic to get the "base" path
        # e.g. "eastham/75_nsunkenmeadow/registry/#" -> "eastham/75_nsunkenmeadow/registry"
        base_path = ""
        if subscription_topic:
            if subscription_topic == "#" or subscription_topic == "*":
                base_path = ""
            elif subscription_topic.endswith("/#"):
                base_path = subscription_topic[:-2]
            elif subscription_topic.endswith("/+"):
                 base_path = subscription_topic[:-2]
            elif subscription_topic.endswith("+"):
                 # Single + wildcard, strip it
                 base_path = subscription_topic[:-1] if subscription_topic[-1:] == "+" else subscription_topic
            else:
                base_path = subscription_topic
        
        logger.debug(f"Raw handler - subscription: {subscription_topic}, base: {base_path}, topic: {topic}")
        
        # If we have a base path and the topic starts with it
        if base_path and topic.startswith(base_path):
             # DB is the last part of the base path
             parts_base = base_path.split('/')
             db_name = parts_base[-1] if parts_base else None
             
             # Remainder of the topic determines table and key
             # topic: base/table/key...
             # remainder: /table/key... or table/key...
             remainder = topic[len(base_path):]
             if remainder.startswith('/'):
                 remainder = remainder[1:]
             
             parts_suffix = remainder.split('/') if remainder else []
             
             if len(parts_suffix) >= 1 and parts_suffix[0]:
                 table_name = parts_suffix[0]
                 
                 if len(parts_suffix) > 1:
                     # Use remaining parts as row key
                     row_key = "/".join(parts_suffix[1:])
             
             logger.debug(f"Parsed from subscription: db={db_name}, table={table_name}, key={row_key}")
        
        # Fallback to old logic if pattern didn't match expectation or was just wildcard
        if not db_name or not table_name:
            parts = topic.split('/')
            if len(parts) >= 2:
                db_name = parts[0]
                table_name = parts[1]
                if len(parts) > 2:
                    row_key = "/".join(parts[2:])
                logger.debug(f"Parsed from topic fallback: db={db_name}, table={table_name}, key={row_key}")
            else:
                logger.warning("Topic %s too short to derive DB and Table names", topic)
                return

        # Sanitize DB and Table names (allow alphanumeric, underscore, dash)
        # CDF Raw naming constraints are relatively strict
        def sanitize(name):
             return "".join(c for c in name if c.isalnum() or c in ('_', '-'))
        
        safe_db_name = sanitize(db_name)
        safe_table_name = sanitize(table_name)
        
        if not safe_db_name or not safe_table_name:
             logger.warning(f"Invalid characters in DB ({db_name}) or Table ({table_name}) derived from topic {topic}")
             return

        # Key generation fallback
        if not row_key:
            if 'key' in data:
                row_key = str(data['key'])
            elif 'id' in data:
                row_key = str(data['id'])
            else:
                import uuid
                row_key = str(uuid.uuid4())
            
        if ensure_db_table(client, safe_db_name, safe_table_name):
            try:
                from cognite.client.data_classes import Row
                
                row = Row(key=row_key, columns=data)
                client.raw.rows.insert(safe_db_name, safe_table_name, [row])
                logger.debug(f"Inserted row into Raw {safe_db_name}.{safe_table_name} with key {row_key}")
                
                # Trigger workflow if configured (throttled per database)
                trigger_workflow_if_needed(client, safe_db_name)
                
            except Exception as e:
                logger.error(f"Failed to insert row into {safe_db_name}.{safe_table_name}: {e}")
                
    except Exception as e:
        logger.exception("Unexpected error in raw handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)
