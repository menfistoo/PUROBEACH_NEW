"""
Audit Log model and data access functions.
Handles audit log creation, retrieval, filtering, and retention cleanup.
"""

import json
from datetime import timedelta
from database import get_db
from utils.datetime_helpers import get_now


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_audit_log_by_id(audit_log_id: int) -> dict:
    """
    Get audit log entry by ID.

    Args:
        audit_log_id: Audit log ID

    Returns:
        Audit log dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.*, u.username, u.full_name as user_full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.id = ?
        ''', (audit_log_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_audit_logs(
    user_id: int = None,
    action: str = None,
    entity_type: str = None,
    entity_id: int = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Get audit logs with optional filtering.

    Args:
        user_id: Filter by user ID
        action: Filter by action type (CREATE, UPDATE, DELETE, etc.)
        entity_type: Filter by entity type (reservation, customer, etc.)
        entity_id: Filter by specific entity ID
        start_date: Filter logs from this date (ISO format YYYY-MM-DD)
        end_date: Filter logs until this date (ISO format YYYY-MM-DD)
        limit: Maximum number of records to return (default 100)
        offset: Number of records to skip for pagination

    Returns:
        List of audit log dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT al.*, u.username, u.full_name as user_full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        '''

        params = []

        if user_id is not None:
            query += ' AND al.user_id = ?'
            params.append(user_id)

        if action:
            query += ' AND al.action = ?'
            params.append(action)

        if entity_type:
            query += ' AND al.entity_type = ?'
            params.append(entity_type)

        if entity_id is not None:
            query += ' AND al.entity_id = ?'
            params.append(entity_id)

        if start_date:
            query += ' AND date(al.created_at) >= date(?)'
            params.append(start_date)

        if end_date:
            query += ' AND date(al.created_at) <= date(?)'
            params.append(end_date)

        query += ' ORDER BY al.created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def count_audit_logs(
    user_id: int = None,
    action: str = None,
    entity_type: str = None,
    entity_id: int = None,
    start_date: str = None,
    end_date: str = None
) -> int:
    """
    Count audit logs with optional filtering (for pagination).

    Args:
        user_id: Filter by user ID
        action: Filter by action type
        entity_type: Filter by entity type
        entity_id: Filter by specific entity ID
        start_date: Filter logs from this date
        end_date: Filter logs until this date

    Returns:
        Total count of matching audit logs
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT COUNT(*) as count
            FROM audit_log al
            WHERE 1=1
        '''

        params = []

        if user_id is not None:
            query += ' AND al.user_id = ?'
            params.append(user_id)

        if action:
            query += ' AND al.action = ?'
            params.append(action)

        if entity_type:
            query += ' AND al.entity_type = ?'
            params.append(entity_type)

        if entity_id is not None:
            query += ' AND al.entity_id = ?'
            params.append(entity_id)

        if start_date:
            query += ' AND date(al.created_at) >= date(?)'
            params.append(start_date)

        if end_date:
            query += ' AND date(al.created_at) <= date(?)'
            params.append(end_date)

        cursor.execute(query, params)
        row = cursor.fetchone()
        return row['count'] if row else 0


def get_audit_logs_for_entity(entity_type: str, entity_id: int, limit: int = 50) -> list:
    """
    Get audit history for a specific entity.

    Args:
        entity_type: Entity type (reservation, customer, etc.)
        entity_id: Entity ID
        limit: Maximum number of records to return

    Returns:
        List of audit log dicts ordered by most recent first
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.*, u.username, u.full_name as user_full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.entity_type = ? AND al.entity_id = ?
            ORDER BY al.created_at DESC
            LIMIT ?
        ''', (entity_type, entity_id, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_distinct_actions() -> list:
    """
    Get list of distinct action types in audit logs.

    Returns:
        List of distinct action strings
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT action FROM audit_log ORDER BY action')
        rows = cursor.fetchall()
        return [row['action'] for row in rows]


def get_distinct_entity_types() -> list:
    """
    Get list of distinct entity types in audit logs.

    Returns:
        List of distinct entity type strings
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT entity_type FROM audit_log ORDER BY entity_type')
        rows = cursor.fetchall()
        return [row['entity_type'] for row in rows]


# =============================================================================
# CREATE OPERATIONS
# =============================================================================

def create_audit_log(
    action: str,
    entity_type: str,
    entity_id: int = None,
    user_id: int = None,
    changes: dict = None,
    old_value: str = None,
    new_value: str = None,
    ip_address: str = None,
    user_agent: str = None
) -> int:
    """
    Create a new audit log entry.

    Args:
        action: Action type (CREATE, UPDATE, DELETE, VIEW, etc.)
        entity_type: Entity type (reservation, customer, pricing, etc.)
        entity_id: ID of the affected entity
        user_id: ID of the user who performed the action (None for system actions)
        changes: Dictionary with before/after state for tracking changes
        old_value: Legacy field for backward compatibility
        new_value: Legacy field for backward compatibility
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        New audit log ID

    Example:
        # Log a reservation update with before/after state
        create_audit_log(
            action='UPDATE',
            entity_type='reservation',
            entity_id=123,
            user_id=1,
            changes={
                'before': {'start_date': '2024-01-01', 'num_people': 2},
                'after': {'start_date': '2024-01-05', 'num_people': 4}
            },
            ip_address='192.168.1.1'
        )
    """
    # Serialize changes dict to JSON string
    changes_json = None
    if changes is not None:
        changes_json = json.dumps(changes, default=str, ensure_ascii=False)

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO audit_log
            (user_id, action, entity_type, entity_id, changes, old_value, new_value, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, action, entity_type, entity_id, changes_json, old_value, new_value, ip_address, user_agent))

        conn.commit()
        return cursor.lastrowid


# =============================================================================
# CLEANUP OPERATIONS
# =============================================================================

def cleanup_old_logs(days: int = 90) -> int:
    """
    Delete audit logs older than specified number of days.
    Implements retention policy to keep database size manageable.

    Args:
        days: Number of days to retain logs (default 90)

    Returns:
        Number of deleted records
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Calculate cutoff date
        cutoff_date = get_now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')

        # Delete old logs
        cursor.execute('''
            DELETE FROM audit_log
            WHERE created_at < ?
        ''', (cutoff_str,))

        deleted_count = cursor.rowcount
        conn.commit()

        return deleted_count


def get_retention_stats() -> dict:
    """
    Get statistics about audit log retention.

    Returns:
        Dict with oldest_log, newest_log, total_count, and logs_older_than_90_days
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) as count FROM audit_log')
        total_count = cursor.fetchone()['count']

        # Get oldest and newest log dates
        cursor.execute('''
            SELECT
                MIN(created_at) as oldest_log,
                MAX(created_at) as newest_log
            FROM audit_log
        ''')
        row = cursor.fetchone()

        # Count logs older than 90 days
        cutoff_date = get_now() - timedelta(days=90)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            SELECT COUNT(*) as count FROM audit_log
            WHERE created_at < ?
        ''', (cutoff_str,))
        old_count = cursor.fetchone()['count']

        return {
            'oldest_log': row['oldest_log'],
            'newest_log': row['newest_log'],
            'total_count': total_count,
            'logs_older_than_90_days': old_count
        }
