"""
Furniture Daily Position model.
CRUD operations for temporary furniture repositioning per day.
"""

from database import get_db
from typing import Optional


# =============================================================================
# DAILY POSITION CRUD
# =============================================================================

def set_daily_position(
    furniture_id: int,
    target_date: str,
    position_x: float,
    position_y: float,
    created_by: str = None
) -> int:
    """
    Set a daily position override for furniture.

    Args:
        furniture_id: Furniture ID
        target_date: Date for the position (YYYY-MM-DD)
        position_x: X coordinate
        position_y: Y coordinate
        created_by: Username setting the position

    Returns:
        int: Daily position record ID
    """
    with get_db() as conn:
        # Use INSERT OR REPLACE for upsert behavior
        cursor = conn.execute('''
            INSERT INTO beach_furniture_daily_positions
            (furniture_id, date, position_x, position_y, created_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(furniture_id, date) DO UPDATE SET
                position_x = excluded.position_x,
                position_y = excluded.position_y,
                created_by = excluded.created_by,
                created_at = CURRENT_TIMESTAMP
        ''', (furniture_id, target_date, position_x, position_y, created_by))

        conn.commit()
        return cursor.lastrowid


def get_daily_position(furniture_id: int, target_date: str) -> Optional[dict]:
    """
    Get daily position override for furniture.

    Args:
        furniture_id: Furniture ID
        target_date: Date to check

    Returns:
        dict or None: Position data if override exists
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT * FROM beach_furniture_daily_positions
            WHERE furniture_id = ? AND date = ?
        ''', (furniture_id, target_date))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_daily_positions_for_date(target_date: str) -> list:
    """
    Get all daily position overrides for a date.

    Args:
        target_date: Date to check

    Returns:
        list: List of position overrides
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT dp.*, f.number as furniture_number, f.zone_id
            FROM beach_furniture_daily_positions dp
            JOIN beach_furniture f ON dp.furniture_id = f.id
            WHERE dp.date = ?
            ORDER BY f.zone_id, f.number
        ''', (target_date,))

        return [dict(row) for row in cursor.fetchall()]


def clear_daily_position(furniture_id: int, target_date: str) -> bool:
    """
    Clear daily position override (revert to default).

    Args:
        furniture_id: Furniture ID
        target_date: Date to clear

    Returns:
        bool: True if deleted
    """
    with get_db() as conn:
        cursor = conn.execute('''
            DELETE FROM beach_furniture_daily_positions
            WHERE furniture_id = ? AND date = ?
        ''', (furniture_id, target_date))
        conn.commit()
        return cursor.rowcount > 0


def clear_daily_positions_for_date(target_date: str) -> int:
    """
    Clear all daily position overrides for a date.

    Args:
        target_date: Date to clear

    Returns:
        int: Number of positions cleared
    """
    with get_db() as conn:
        cursor = conn.execute('''
            DELETE FROM beach_furniture_daily_positions
            WHERE date = ?
        ''', (target_date,))
        conn.commit()
        return cursor.rowcount


def get_furniture_with_daily_positions(target_date: str, zone_id: int = None) -> list:
    """
    Get all furniture with daily positions applied for a date.

    Returns furniture with position_x/position_y reflecting daily overrides
    when they exist.

    Args:
        target_date: Date to get positions for
        zone_id: Optional zone filter

    Returns:
        list: Furniture with effective positions
    """
    with get_db() as conn:
        query = '''
            SELECT
                f.*,
                z.name as zone_name,
                COALESCE(dp.position_x, f.position_x) as effective_x,
                COALESCE(dp.position_y, f.position_y) as effective_y,
                CASE WHEN dp.id IS NOT NULL THEN 1 ELSE 0 END as has_daily_position
            FROM beach_furniture f
            JOIN beach_zones z ON f.zone_id = z.id
            LEFT JOIN beach_furniture_daily_positions dp
                ON dp.furniture_id = f.id AND dp.date = ?
            WHERE f.active = 1
        '''
        params = [target_date]

        if zone_id:
            query += ' AND f.zone_id = ?'
            params.append(zone_id)

        query += ' ORDER BY f.zone_id, f.number'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# TEMPORARY FURNITURE
# =============================================================================

def create_temporary_furniture(
    zone_id: int,
    furniture_type: str,
    number: str,
    capacity: int,
    position_x: float,
    position_y: float,
    target_date: str,
    **kwargs
) -> int:
    """
    Create temporary furniture for a specific date/event.

    Args:
        zone_id: Zone to add furniture to
        furniture_type: Type code
        number: Furniture number/identifier
        capacity: Capacity
        position_x: X position
        position_y: Y position
        target_date: Date this furniture is active for
        **kwargs: Additional fields (width, height, rotation, etc.)

    Returns:
        int: Furniture ID
    """
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO beach_furniture
            (zone_id, furniture_type, number, capacity, position_x, position_y,
             width, height, rotation, active, is_temporary, valid_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
        ''', (
            zone_id,
            furniture_type,
            number,
            capacity,
            position_x,
            position_y,
            kwargs.get('width', 60),
            kwargs.get('height', 40),
            kwargs.get('rotation', 0),
            target_date
        ))
        conn.commit()
        return cursor.lastrowid


def get_temporary_furniture_for_date(target_date: str, zone_id: int = None) -> list:
    """
    Get temporary furniture active on a specific date.

    Args:
        target_date: Date to check
        zone_id: Optional zone filter

    Returns:
        list: Temporary furniture items
    """
    with get_db() as conn:
        query = '''
            SELECT f.*, z.name as zone_name
            FROM beach_furniture f
            JOIN beach_zones z ON f.zone_id = z.id
            WHERE f.is_temporary = 1 AND f.valid_date = ?
        '''
        params = [target_date]

        if zone_id:
            query += ' AND f.zone_id = ?'
            params.append(zone_id)

        query += ' ORDER BY f.zone_id, f.number'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def delete_temporary_furniture(furniture_id: int) -> bool:
    """
    Delete temporary furniture.

    Args:
        furniture_id: Furniture ID

    Returns:
        bool: True if deleted

    Raises:
        ValueError: If furniture is not temporary or has reservations
    """
    with get_db() as conn:
        # Check if temporary
        cursor = conn.execute('''
            SELECT is_temporary FROM beach_furniture WHERE id = ?
        ''', (furniture_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Mobiliario no encontrado")

        if not row['is_temporary']:
            raise ValueError("Solo se puede eliminar mobiliario temporal")

        # Check for reservations
        cursor = conn.execute('''
            SELECT COUNT(*) as count FROM beach_reservation_furniture
            WHERE furniture_id = ?
        ''', (furniture_id,))
        if cursor.fetchone()['count'] > 0:
            raise ValueError("No se puede eliminar mobiliario con reservas")

        # Delete
        cursor = conn.execute('''
            DELETE FROM beach_furniture WHERE id = ? AND is_temporary = 1
        ''', (furniture_id,))
        conn.commit()
        return cursor.rowcount > 0


def cleanup_expired_temporary_furniture(before_date: str) -> int:
    """
    Remove temporary furniture from past dates (without reservations).

    Args:
        before_date: Remove temporary furniture before this date

    Returns:
        int: Number of items removed
    """
    with get_db() as conn:
        cursor = conn.execute('''
            DELETE FROM beach_furniture
            WHERE is_temporary = 1
            AND valid_date < ?
            AND id NOT IN (
                SELECT DISTINCT furniture_id FROM beach_reservation_furniture
            )
        ''', (before_date,))
        conn.commit()
        return cursor.rowcount
