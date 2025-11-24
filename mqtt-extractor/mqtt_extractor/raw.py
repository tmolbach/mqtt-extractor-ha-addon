import json
import logging
from typing import Generator, Tuple, Union, Any

logger = logging.getLogger(__name__)

# Cache for existing databases and tables to avoid repeated API calls
# Structure: {db_name: {table_name: True}}
_existing_resources = {}

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

def parse(payload: bytes, topic: str, client: Any = None) -> Generator[Tuple[str, int, Union[int, float, str]], None, None]:
    """
    Parse payload and write to Cognite Data Fusion Raw.
    Topic structure expected: db_name/table_name/...
    Payload expected: JSON object
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

        # Parse Topic for DB, Table, and Key
        # Example: registry/areas/living_room -> db=registry, table=areas, key=living_room
        parts = topic.split('/')
        
        # We need at least db/table
        if len(parts) < 2:
            logger.warning("Topic %s too short to derive DB and Table names (needs db/table)", topic)
            return
        
        db_name = parts[0]
        table_name = parts[1]
        
        # Key generation strategy:
        # 1. Use the last part of the topic if parts > 2
        # 2. Or check for an 'id' or 'key' field in the payload
        # 3. Fallback to a UUID or timestamp
        
        row_key = None
        if len(parts) > 2:
            row_key = parts[-1]
        elif 'key' in data:
            row_key = str(data['key'])
        elif 'id' in data:
            row_key = str(data['id'])
        else:
            # No key found in topic or payload
            # For raw rows, we need a key. 
            # If the user intends to just dump data, maybe we use a timestamp or uuid
            import uuid
            row_key = str(uuid.uuid4())
            
        # Ensure safe names for CDF Raw (alphanumeric, underscore, dash)
        # CDF Raw constraints: 
        # db/table: ^[a-zA-Z0-9_][a-zA-Z0-9_-]{0,254}$
        # key: up to 1024 chars
        
        # Simple sanitization for db/table if needed, but assuming topic is relatively safe
        # or user configured valid topics. 
        
        if ensure_db_table(client, db_name, table_name):
            try:
                # Insert row
                # client.raw.rows.insert expects a list of rows (Row object or dict)
                # If dict, it should be mapped to key/columns
                # The SDK method signature: insert(db_name, table_name, row_list)
                # row_list can be {"key": "k", "columns": {...}} objects
                
                from cognite.client.data_classes import Row
                
                row = Row(key=row_key, columns=data)
                client.raw.rows.insert(db_name, table_name, [row])
                logger.debug(f"Inserted row into Raw {db_name}.{table_name} with key {row_key}")
                
            except Exception as e:
                logger.error(f"Failed to insert row into {db_name}.{table_name}: {e}")
                
    except Exception as e:
        logger.exception("Unexpected error in raw handler for topic %s", topic)

    # Yield nothing as we handle storage internally
    if False:
        yield ("", 0, 0)
