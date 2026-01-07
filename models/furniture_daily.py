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
    start_date: str,
    end_date: str = None,
    **kwargs
) -> int:
    """
    Create temporary furniture for a date range.

    Args:
        zone_id: Zone to add furniture to
        furniture_type: Type code
        number: Furniture number/identifier
        capacity: Capacity
        position_x: X position
        position_y: Y position
        start_date: Start date for validity (YYYY-MM-DD)
        end_date: End date for validity (YYYY-MM-DD), defaults to start_date
        **kwargs: Additional fields (width, height, rotation, etc.)

    Returns:
        int: Furniture ID
    """
    # Default end_date to start_date if not provided (single day)
    if end_date is None:
        end_date = start_date

    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO beach_furniture
            (zone_id, furniture_type, number, capacity, position_x, position_y,
             width, height, rotation, active, is_temporary,
             temp_start_date, temp_end_date, valid_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
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
            start_date,
            end_date,
            start_date  # Keep valid_date for backward compatibility
        ))
        conn.commit()
        return cursor.lastrowid


def get_temporary_furniture_for_date(target_date: str, zone_id: int = None) -> list:
    """
    Get temporary furniture active on a specific date (within date range).

    Args:
        target_date: Date to check (YYYY-MM-DD)
        zone_id: Optional zone filter

    Returns:
        list: Temporary furniture items active on that date
    """
    with get_db() as conn:
        # Query by date range (temp_start_date <= date AND temp_end_date >= date)
        # Falls back to valid_date for backward compatibility
        query = '''
            SELECT f.*, z.name as zone_name,
                   ft.display_name as furniture_type_name
            FROM beach_furniture f
            JOIN beach_zones z ON f.zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
            WHERE f.is_temporary = 1
            AND f.active = 1
            AND (
                (f.temp_start_date IS NOT NULL AND f.temp_start_date <= ? AND f.temp_end_date >= ?)
                OR (f.temp_start_date IS NULL AND f.valid_date = ?)
            )
        '''
        params = [target_date, target_date, target_date]

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


def get_next_temp_furniture_number(furniture_type: str, zone_id: int = None) -> str:
    """
    Get the next available number for temporary furniture.

    Uses "T" prefix followed by incremental number (T1, T2, etc.)
    Finds gaps in the sequence to reuse deleted numbers.

    Args:
        furniture_type: Type code (not currently used, reserved for future)
        zone_id: Zone ID (not currently used, reserved for future)

    Returns:
        str: Next available number (e.g., "T1", "T2")
    """
    with get_db() as conn:
        # Get all existing temp furniture numbers starting with "T"
        cursor = conn.execute('''
            SELECT number FROM beach_furniture
            WHERE is_temporary = 1
            AND number LIKE 'T%'
            ORDER BY CAST(SUBSTR(number, 2) AS INTEGER)
        ''')
        existing = [row['number'] for row in cursor.fetchall()]

        # Find the first available number
        for i in range(1, 1000):
            candidate = f"T{i}"
            if candidate not in existing:
                return candidate

        # Fallback (shouldn't happen)
        return f"T{len(existing) + 1}"


def cleanup_expired_temporary_furniture(before_date: str) -> int:
    """
    Remove temporary furniture that has expired (without reservations).

    Args:
        before_date: Remove temporary furniture ending before this date

    Returns:
        int: Number of items removed
    """
    with get_db() as conn:
        # Use temp_end_date for expiry, fallback to valid_date
        cursor = conn.execute('''
            DELETE FROM beach_furniture
            WHERE is_temporary = 1
            AND (
                (temp_end_date IS NOT NULL AND temp_end_date < ?)
                OR (temp_end_date IS NULL AND valid_date < ?)
            )
            AND id NOT IN (
                SELECT DISTINCT furniture_id FROM beach_reservation_furniture
            )
        ''', (before_date, before_date))
        conn.commit()
        return cursor.rowcount


def partial_delete_temp_furniture(furniture_id: int, delete_date: str) -> dict:
    """
    Partially delete temporary furniture for a specific date.

    This may delete, shrink, or split the date range depending on the delete date:
    - If furniture is single day or delete covers entire range: delete entirely
    - If delete is at start: shrink (move start_date forward)
    - If delete is at end: shrink (move end_date back)
    - If delete is in middle: split into two furniture items

    Args:
        furniture_id: Furniture ID to partially delete
        delete_date: Date to remove from the range (YYYY-MM-DD)

    Returns:
        dict: Result with action taken and any new furniture IDs

    Raises:
        ValueError: If validation fails
    """
    from datetime import datetime, timedelta

    with get_db() as conn:
        # Get current furniture
        cursor = conn.execute('''
            SELECT * FROM beach_furniture WHERE id = ? AND is_temporary = 1
        ''', (furniture_id,))
        furniture = cursor.fetchone()

        if not furniture:
            raise ValueError("Mobiliario temporal no encontrado")

        furniture = dict(furniture)
        start_date = str(furniture['temp_start_date'])
        end_date = str(furniture['temp_end_date'])

        # Validate delete_date is within range
        if delete_date < start_date or delete_date > end_date:
            raise ValueError("La fecha debe estar dentro del rango del mobiliario")

        # Check for reservations on that date
        cursor = conn.execute('''
            SELECT COUNT(*) as count FROM beach_reservation_furniture
            WHERE furniture_id = ? AND assignment_date = ?
        ''', (furniture_id, delete_date))
        if cursor.fetchone()['count'] > 0:
            raise ValueError("No se puede eliminar: hay reservas en esta fecha")

        # Calculate adjacent dates
        def add_days(date_str: str, days: int) -> str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return (dt + timedelta(days=days)).strftime('%Y-%m-%d')

        result = {'action': None, 'furniture_ids': []}

        # Case 1: Single day or delete covers entire range - delete entirely
        if start_date == end_date or (delete_date == start_date and delete_date == end_date):
            conn.execute('DELETE FROM beach_furniture WHERE id = ?', (furniture_id,))
            result['action'] = 'deleted'

        # Case 2: Delete at start - shrink forward
        elif delete_date == start_date:
            new_start = add_days(delete_date, 1)
            conn.execute('''
                UPDATE beach_furniture
                SET temp_start_date = ?, valid_date = ?
                WHERE id = ?
            ''', (new_start, new_start, furniture_id))
            result['action'] = 'shrunk_start'
            result['furniture_ids'] = [furniture_id]

        # Case 3: Delete at end - shrink backward
        elif delete_date == end_date:
            new_end = add_days(delete_date, -1)
            conn.execute('''
                UPDATE beach_furniture
                SET temp_end_date = ?
                WHERE id = ?
            ''', (new_end, furniture_id))
            result['action'] = 'shrunk_end'
            result['furniture_ids'] = [furniture_id]

        # Case 4: Delete in middle - split into two
        else:
            # Update original to end before delete_date
            new_end_first = add_days(delete_date, -1)
            conn.execute('''
                UPDATE beach_furniture
                SET temp_end_date = ?
                WHERE id = ?
            ''', (new_end_first, furniture_id))

            # Create new furniture starting after delete_date
            new_start_second = add_days(delete_date, 1)
            cursor = conn.execute('''
                INSERT INTO beach_furniture
                (zone_id, furniture_type, number, capacity, position_x, position_y,
                 width, height, rotation, active, is_temporary,
                 temp_start_date, temp_end_date, valid_date, fill_color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
            ''', (
                furniture['zone_id'],
                furniture['furniture_type'],
                furniture['number'],  # Same number for continuity
                furniture['capacity'],
                furniture['position_x'],
                furniture['position_y'],
                furniture['width'],
                furniture['height'],
                furniture['rotation'],
                new_start_second,
                end_date,
                new_start_second,
                furniture.get('fill_color')
            ))
            new_id = cursor.lastrowid
            result['action'] = 'split'
            result['furniture_ids'] = [furniture_id, new_id]

        conn.commit()
        return result


def get_temp_furniture_date_info(furniture_id: int) -> dict:
    """
    Get date range info for temporary furniture.

    Args:
        furniture_id: Furniture ID

    Returns:
        dict: Date info including is_multi_day flag
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT id, number, temp_start_date, temp_end_date, is_temporary
            FROM beach_furniture WHERE id = ?
        ''', (furniture_id,))
        row = cursor.fetchone()

        if not row:
            return None

        row = dict(row)
        start = str(row['temp_start_date']) if row['temp_start_date'] else None
        end = str(row['temp_end_date']) if row['temp_end_date'] else None

        return {
            'id': row['id'],
            'number': row['number'],
            'start_date': start,
            'end_date': end,
            'is_temporary': row['is_temporary'],
            'is_multi_day': start != end if (start and end) else False
        }
