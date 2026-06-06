"""
Import log model.
Tracks hotel guest import history, results, and errors.
"""

import json
from typing import Dict, Any, Optional
from database.connection import get_db


def save_import_log(
    import_type: str,
    source_file: str,
    total_records: int,
    created_count: int,
    updated_count: int,
    errors: list,
    room_changes: list,
    imported_by: Optional[int] = None
) -> int:
    """
    Save an import result to the log.

    Args:
        import_type: Type of import (e.g., 'hotel_guests')
        source_file: Original filename
        total_records: Total rows processed
        created_count: New records created
        updated_count: Existing records updated
        errors: List of error strings
        room_changes: List of room change dicts
        imported_by: User ID who triggered the import

    Returns:
        int: ID of the created log entry
    """
    db = get_db()
    cursor = db.execute('''
        INSERT INTO beach_import_log
        (import_type, source_file, total_records, created_count,
         updated_count, error_count, errors_json, room_changes_json, imported_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        import_type,
        source_file,
        total_records,
        created_count,
        updated_count,
        len(errors),
        json.dumps(errors, ensure_ascii=False) if errors else None,
        json.dumps(room_changes, ensure_ascii=False) if room_changes else None,
        imported_by
    ))
    db.commit()
    return cursor.lastrowid


def get_last_import(import_type: str = 'hotel_guests') -> Optional[Dict[str, Any]]:
    """
    Get the most recent import log entry.

    Args:
        import_type: Type of import to query

    Returns:
        Dict with import info or None if no imports found
    """
    db = get_db()
    row = db.execute('''
        SELECT il.*, u.username as imported_by_name
        FROM beach_import_log il
        LEFT JOIN users u ON il.imported_by = u.id
        WHERE il.import_type = ?
        ORDER BY il.imported_at DESC
        LIMIT 1
    ''', (import_type,)).fetchone()

    if not row:
        return None

    result = dict(row)
    # Parse JSON fields
    if result.get('errors_json'):
        result['errors'] = json.loads(result['errors_json'])
    else:
        result['errors'] = []

    if result.get('room_changes_json'):
        result['room_changes'] = json.loads(result['room_changes_json'])
    else:
        result['room_changes'] = []

    return result


def get_import_log_list(
    import_type: str = 'hotel_guests',
    limit: int = 20
) -> list:
    """
    Get recent import log entries.

    Args:
        import_type: Type of import to query
        limit: Max entries to return

    Returns:
        List of import log dicts
    """
    db = get_db()
    rows = db.execute('''
        SELECT il.*, u.username as imported_by_name
        FROM beach_import_log il
        LEFT JOIN users u ON il.imported_by = u.id
        WHERE il.import_type = ?
        ORDER BY il.imported_at DESC
        LIMIT ?
    ''', (import_type, limit)).fetchall()

    results = []
    for row in rows:
        entry = dict(row)
        entry['errors'] = json.loads(entry['errors_json']) if entry.get('errors_json') else []
        entry['room_changes'] = json.loads(entry['room_changes_json']) if entry.get('room_changes_json') else []
        results.append(entry)

    return results
