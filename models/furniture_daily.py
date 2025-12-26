"""
Furniture daily positions and temporary furniture models.
Handles daily position overrides and temporary furniture.
"""

from database.connection import get_db
from typing import Optional, List, Dict, Any


# =============================================================================
# DAILY POSITION OVERRIDES
# =============================================================================

def set_daily_position(furniture_id: int, date: str, position_x: float, position_y: float, created_by: str = None) -> bool:
    """
    Set or update daily position override for furniture.

    Args:
        furniture_id: ID of the furniture
        date: Date in YYYY-MM-DD format
        position_x: X coordinate
        position_y: Y coordinate
        created_by: Username who created the override

    Returns:
        bool: True if successful
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        INSERT INTO beach_furniture_daily_positions (furniture_id, date, position_x, position_y, created_by)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(furniture_id, date)
        DO UPDATE SET
            position_x = excluded.position_x,
            position_y = excluded.position_y,
            created_by = excluded.created_by,
            created_at = CURRENT_TIMESTAMP
    ''', (furniture_id, date, position_x, position_y, created_by))

    db.commit()
    return True


def get_daily_position(furniture_id: int, date: str) -> Optional[Dict[str, Any]]:
    """
    Get daily position override for furniture on specific date.

    Args:
        furniture_id: ID of the furniture
        date: Date in YYYY-MM-DD format

    Returns:
        dict with position data or None if no override exists
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT id, furniture_id, date, position_x, position_y, created_by, created_at
        FROM beach_furniture_daily_positions
        WHERE furniture_id = ? AND date = ?
    ''', (furniture_id, date))

    row = cursor.fetchone()
    if not row:
        return None

    return {
        'id': row[0],
        'furniture_id': row[1],
        'date': row[2],
        'position_x': row[3],
        'position_y': row[4],
        'created_by': row[5],
        'created_at': row[6]
    }


def clear_daily_position(furniture_id: int, date: str) -> bool:
    """
    Clear daily position override for furniture.

    Args:
        furniture_id: ID of the furniture
        date: Date in YYYY-MM-DD format

    Returns:
        bool: True if successful
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        DELETE FROM beach_furniture_daily_positions
        WHERE furniture_id = ? AND date = ?
    ''', (furniture_id, date))

    db.commit()
    return True


def get_daily_positions_for_date(date: str) -> List[Dict[str, Any]]:
    """
    Get all daily position overrides for a specific date.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        list of position override dicts
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT dp.id, dp.furniture_id, dp.date, dp.position_x, dp.position_y,
               dp.created_by, dp.created_at,
               f.code as furniture_code, f.name as furniture_name
        FROM beach_furniture_daily_positions dp
        JOIN beach_furniture f ON dp.furniture_id = f.id
        WHERE dp.date = ?
        ORDER BY f.code
    ''', (date,))

    positions = []
    for row in cursor.fetchall():
        positions.append({
            'id': row[0],
            'furniture_id': row[1],
            'date': row[2],
            'position_x': row[3],
            'position_y': row[4],
            'created_by': row[5],
            'created_at': row[6],
            'furniture_code': row[7],
            'furniture_name': row[8]
        })

    return positions


# =============================================================================
# TEMPORARY FURNITURE
# =============================================================================

def create_temporary_furniture(
    furniture_type_id: int,
    zone_id: int,
    code: str,
    name: str,
    position_x: float,
    position_y: float,
    valid_from: str,
    valid_to: str,
    created_by: str = None
) -> Optional[int]:
    """
    Create temporary furniture valid for specific date range.

    Args:
        furniture_type_id: Type of furniture
        zone_id: Zone where furniture is located
        code: Furniture code
        name: Furniture name
        position_x: X coordinate
        position_y: Y coordinate
        valid_from: Start date (YYYY-MM-DD)
        valid_to: End date (YYYY-MM-DD)
        created_by: Username who created it

    Returns:
        int: ID of created furniture or None on error
    """
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            INSERT INTO beach_furniture (
                furniture_type_id, zone_id, code, name,
                position_x, position_y, capacity, active,
                is_temporary, temporary_valid_from, temporary_valid_to
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1, ?, ?)
        ''', (furniture_type_id, zone_id, code, name, position_x, position_y, valid_from, valid_to))

        db.commit()
        return cursor.lastrowid
    except Exception as e:
        db.rollback()
        print(f"Error creating temporary furniture: {e}")
        return None


def get_temporary_furniture_for_date(date: str) -> List[Dict[str, Any]]:
    """
    Get all temporary furniture valid for a specific date.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        list of furniture dicts
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT f.id, f.code, f.name, f.furniture_type_id, f.zone_id,
               f.position_x, f.position_y, f.capacity,
               f.temporary_valid_from, f.temporary_valid_to,
               ft.name as type_name, z.name as zone_name
        FROM beach_furniture f
        JOIN beach_furniture_types ft ON f.furniture_type_id = ft.id
        JOIN beach_zones z ON f.zone_id = z.id
        WHERE f.is_temporary = 1
          AND f.active = 1
          AND DATE(?) BETWEEN DATE(f.temporary_valid_from) AND DATE(f.temporary_valid_to)
        ORDER BY f.code
    ''', (date,))

    furniture_list = []
    for row in cursor.fetchall():
        furniture_list.append({
            'id': row[0],
            'code': row[1],
            'name': row[2],
            'furniture_type_id': row[3],
            'zone_id': row[4],
            'position_x': row[5],
            'position_y': row[6],
            'capacity': row[7],
            'valid_from': row[8],
            'valid_to': row[9],
            'type_name': row[10],
            'zone_name': row[11]
        })

    return furniture_list


def delete_temporary_furniture(furniture_id: int) -> bool:
    """
    Delete temporary furniture.

    Args:
        furniture_id: ID of the furniture

    Returns:
        bool: True if successful
    """
    db = get_db()
    cursor = db.cursor()

    # Verify it's temporary furniture
    cursor.execute('''
        SELECT is_temporary FROM beach_furniture WHERE id = ?
    ''', (furniture_id,))

    row = cursor.fetchone()
    if not row or not row[0]:
        return False

    cursor.execute('DELETE FROM beach_furniture WHERE id = ?', (furniture_id,))
    db.commit()
    return True
