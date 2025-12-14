"""
Beach zone data access functions.
Handles zone CRUD operations.
"""

from database import get_db


def get_all_zones(active_only: bool = True) -> list:
    """
    Get all beach zones.

    Args:
        active_only: If True, only return active zones

    Returns:
        List of zone dicts ordered by display_order
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT z.*,
               (SELECT COUNT(*) FROM beach_furniture WHERE zone_id = z.id) as furniture_count,
               (SELECT COUNT(*) FROM beach_zones WHERE parent_zone_id = z.id) as child_count
        FROM beach_zones z
    '''

    if active_only:
        query += ' WHERE z.active = 1'

    query += ' ORDER BY z.display_order, z.name'

    cursor.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_zone_by_id(zone_id: int) -> dict:
    """
    Get zone by ID.

    Args:
        zone_id: Zone ID

    Returns:
        Zone dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM beach_zones WHERE id = ?', (zone_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_zone(name: str, description: str = None, parent_zone_id: int = None, color: str = '#F5E6D3') -> int:
    """
    Create new beach zone.

    Args:
        name: Zone name
        description: Zone description
        parent_zone_id: Parent zone ID (for hierarchical zones)
        color: Zone color for map display

    Returns:
        New zone ID
    """
    db = get_db()
    cursor = db.cursor()

    # Get next display order
    cursor.execute('SELECT COALESCE(MAX(display_order), 0) + 1 FROM beach_zones')
    display_order = cursor.fetchone()[0]

    cursor.execute('''
        INSERT INTO beach_zones (name, description, parent_zone_id, color, display_order)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, description, parent_zone_id, color, display_order))

    db.commit()
    return cursor.lastrowid


def update_zone(zone_id: int, **kwargs) -> bool:
    """
    Update zone fields.

    Args:
        zone_id: Zone ID to update
        **kwargs: Fields to update (name, description, color, display_order, active)

    Returns:
        True if updated successfully
    """
    db = get_db()

    allowed_fields = ['name', 'description', 'color', 'display_order', 'active', 'parent_zone_id']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(zone_id)
    query = f'UPDATE beach_zones SET {", ".join(updates)} WHERE id = ?'

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_zone(zone_id: int) -> bool:
    """
    Delete zone permanently.
    Only allowed if zone has no furniture (active or inactive).

    Args:
        zone_id: Zone ID to delete

    Returns:
        True if deleted successfully

    Raises:
        ValueError if zone has any furniture
    """
    db = get_db()
    cursor = db.cursor()

    # Check for any furniture (active or inactive)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_furniture
        WHERE zone_id = ?
    ''', (zone_id,))

    if cursor.fetchone()['count'] > 0:
        raise ValueError('No se puede eliminar zona con mobiliario asignado')

    # Check for child zones
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_zones
        WHERE parent_zone_id = ?
    ''', (zone_id,))

    if cursor.fetchone()['count'] > 0:
        raise ValueError('No se puede eliminar zona con subzonas')

    # Hard delete
    cursor.execute('DELETE FROM beach_zones WHERE id = ?', (zone_id,))

    db.commit()
    return cursor.rowcount > 0
