"""
Beach config data access functions.
Handles reading and writing beach_config key-value pairs.
"""

from typing import Optional, Dict, Any
from database import get_db


def get_config(key: str, default: str = None) -> Optional[str]:
    """
    Get a single config value by key.

    Args:
        key: Config key name
        default: Default value if key not found

    Returns:
        Config value string or default
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT value FROM beach_config WHERE key = ?', (key,))
    row = cursor.fetchone()
    return row['value'] if row else default


def get_config_int(key: str, default: int = 0) -> int:
    """
    Get a config value as integer.

    Args:
        key: Config key name
        default: Default value if key not found or invalid

    Returns:
        Config value as integer
    """
    value = get_config(key)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_config_float(key: str, default: float = 0.0) -> float:
    """
    Get a config value as float.

    Args:
        key: Config key name
        default: Default value if key not found or invalid

    Returns:
        Config value as float
    """
    value = get_config(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_config_bool(key: str, default: bool = False) -> bool:
    """
    Get a config value as boolean.

    Args:
        key: Config key name
        default: Default value if key not found

    Returns:
        Config value as boolean
    """
    value = get_config(key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def get_all_config() -> Dict[str, str]:
    """
    Get all config key-value pairs.

    Returns:
        Dict of all config values
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT key, value FROM beach_config')
    return {row['key']: row['value'] for row in cursor.fetchall()}


def get_map_config() -> Dict[str, Any]:
    """
    Get all map-related configuration values.

    Returns:
        Dict with map configuration (typed values)
    """
    return {
        'default_width': get_config_int('map_default_width', 1200),
        'min_height': get_config_int('map_min_height', 800),
        'zone_padding': get_config_int('map_zone_padding', 20),
        'zone_height': get_config_int('map_zone_height', 200),
        'auto_refresh_ms': get_config_int('map_auto_refresh_ms', 30000),
        'min_zoom': get_config_float('map_min_zoom', 0.1),
        'max_zoom': get_config_float('map_max_zoom', 3.0),
        'snap_grid': get_config_int('map_snap_grid', 10),
    }


def set_config(key: str, value: str, description: str = None) -> bool:
    """
    Set a config value (insert or update).

    Args:
        key: Config key name
        value: Config value
        description: Optional description (only used on insert)

    Returns:
        True if successful
    """
    db = get_db()
    cursor = db.cursor()

    # Check if exists
    existing = get_config(key)

    if existing is not None:
        cursor.execute('''
            UPDATE beach_config
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE key = ?
        ''', (value, key))
    else:
        cursor.execute('''
            INSERT INTO beach_config (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, description))

    db.commit()
    return cursor.rowcount > 0


def delete_config(key: str) -> bool:
    """
    Delete a config key.

    Args:
        key: Config key name

    Returns:
        True if deleted
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM beach_config WHERE key = ?', (key,))
    db.commit()
    return cursor.rowcount > 0
