"""
Beach furniture data access functions.
Handles furniture CRUD operations and furniture type management.
"""

from database import get_db
from datetime import datetime


def get_all_furniture(zone_id: int = None, active_only: bool = True) -> list:
    """
    Get all beach furniture.

    Args:
        zone_id: Filter by zone ID (optional)
        active_only: If True, only return active furniture

    Returns:
        List of furniture dicts with zone information
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT f.*, z.name as zone_name, z.color as zone_color,
               ft.display_name as furniture_type_name, ft.icon as furniture_type_icon,
               ft.fill_color as furniture_type_fill_color,
               ft.stroke_color as furniture_type_stroke_color,
               ft.is_decorative as furniture_type_is_decorative
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        WHERE 1=1
    '''

    params = []

    if zone_id:
        query += ' AND f.zone_id = ?'
        params.append(zone_id)

    if active_only:
        query += ' AND f.active = 1'

    query += ' ORDER BY z.display_order, f.number'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_furniture_by_id(furniture_id: int) -> dict:
    """
    Get furniture by ID.

    Args:
        furniture_id: Furniture ID

    Returns:
        Furniture dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT f.*, z.name as zone_name, z.color as zone_color,
               ft.display_name as furniture_type_name
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        WHERE f.id = ?
    ''', (furniture_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_furniture_types() -> list:
    """
    Get all furniture types.

    Returns:
        List of furniture type dicts
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM beach_furniture_types
        WHERE active = 1
        ORDER BY display_name
    ''')
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def create_furniture(number: str, zone_id: int, furniture_type: str, capacity: int,
                      position_x: float = 0, position_y: float = 0, **kwargs) -> int:
    """
    Create new furniture item.

    Args:
        number: Display number/identifier
        zone_id: Zone ID
        furniture_type: Furniture type code
        capacity: Maximum capacity
        position_x: X coordinate for map
        position_y: Y coordinate for map
        **kwargs: Optional fields (rotation, width, height, features, is_temporary, valid_date)

    Returns:
        New furniture ID
    """
    db = get_db()
    cursor = db.cursor()

    rotation = kwargs.get('rotation', 0)
    width = kwargs.get('width', 60)
    height = kwargs.get('height', 40)
    features = kwargs.get('features', '')
    is_temporary = kwargs.get('is_temporary', 0)
    valid_date = kwargs.get('valid_date', None)

    cursor.execute('''
        INSERT INTO beach_furniture
        (number, zone_id, furniture_type, capacity, position_x, position_y,
         rotation, width, height, features, is_temporary, valid_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (number, zone_id, furniture_type, capacity, position_x, position_y,
          rotation, width, height, features, is_temporary, valid_date))

    db.commit()
    return cursor.lastrowid


def update_furniture(furniture_id: int, **kwargs) -> bool:
    """
    Update furniture fields.

    Args:
        furniture_id: Furniture ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    db = get_db()

    allowed_fields = ['number', 'zone_id', 'capacity', 'position_x', 'position_y',
                      'rotation', 'width', 'height', 'features', 'active']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(furniture_id)
    query = f'UPDATE beach_furniture SET {", ".join(updates)} WHERE id = ?'

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_furniture(furniture_id: int) -> bool:
    """
    Soft delete furniture (set active = 0).
    Only allowed if no active reservations.

    Args:
        furniture_id: Furniture ID to delete

    Returns:
        True if deleted successfully

    Raises:
        ValueError if furniture has active reservations
    """
    db = get_db()
    cursor = db.cursor()

    # Check for active reservations
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE rf.furniture_id = ?
          AND rf.assignment_date >= date('now')
    ''', (furniture_id,))

    if cursor.fetchone()['count'] > 0:
        raise ValueError('No se puede eliminar mobiliario con reservas activas')

    cursor.execute('''
        UPDATE beach_furniture SET active = 0
        WHERE id = ?
    ''', (furniture_id,))

    db.commit()
    return cursor.rowcount > 0


def get_temporary_furniture(date: str) -> list:
    """
    Get temporary furniture valid for a specific date.

    Args:
        date: Date string (YYYY-MM-DD)

    Returns:
        List of temporary furniture dicts
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT f.*, z.name as zone_name
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        WHERE f.is_temporary = 1
          AND f.valid_date = ?
          AND f.active = 1
    ''', (date,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_next_number_by_prefix(prefix: str) -> str:
    """
    Get the next available number for a given prefix.

    Searches all furniture numbers with the given prefix and returns
    the next sequential number.

    Args:
        prefix: The prefix to search for (e.g., "H", "B", "S")

    Returns:
        Next available number string (e.g., "H5", "B10")
    """
    db = get_db()
    cursor = db.cursor()

    if prefix:
        # Find all numbers with this prefix
        cursor.execute('''
            SELECT number FROM beach_furniture
            WHERE number LIKE ? || '%'
        ''', (prefix,))
    else:
        # Find all numeric-only numbers
        cursor.execute('''
            SELECT number FROM beach_furniture
            WHERE number GLOB '[0-9]*'
        ''')

    rows = cursor.fetchall()

    max_num = 0
    for row in rows:
        try:
            # Extract number part after prefix
            num_str = row['number'][len(prefix):] if prefix else row['number']
            num = int(num_str)
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue

    next_num = max_num + 1
    return f"{prefix}{next_num}"
