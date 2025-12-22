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


def create_zone(
    name: str,
    description: str = None,
    parent_zone_id: int = None,
    color: str = '#F5E6D3',
    canvas_width: float = 2000,
    canvas_height: float = 1000,
    background_color: str = '#FAFAFA'
) -> int:
    """
    Create new beach zone.

    Args:
        name: Zone name
        description: Zone description
        parent_zone_id: Parent zone ID (for hierarchical zones)
        color: Zone color for map display
        canvas_width: Canvas width in pixels for map editor
        canvas_height: Canvas height in pixels for map editor
        background_color: Canvas background color

    Returns:
        New zone ID
    """
    db = get_db()
    cursor = db.cursor()

    # Get next display order
    cursor.execute('SELECT COALESCE(MAX(display_order), 0) + 1 FROM beach_zones')
    display_order = cursor.fetchone()[0]

    cursor.execute('''
        INSERT INTO beach_zones (name, description, parent_zone_id, color, display_order,
                                 canvas_width, canvas_height, background_color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, parent_zone_id, color, display_order,
          canvas_width, canvas_height, background_color))

    db.commit()
    return cursor.lastrowid


def update_zone(zone_id: int, **kwargs) -> bool:
    """
    Update zone fields.

    Args:
        zone_id: Zone ID to update
        **kwargs: Fields to update (name, description, color, display_order, active,
                  canvas_width, canvas_height, background_color)

    Returns:
        True if updated successfully
    """
    db = get_db()

    allowed_fields = ['name', 'description', 'color', 'display_order', 'active', 'parent_zone_id',
                      'canvas_width', 'canvas_height', 'background_color']
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


def get_zone_with_furniture(zone_id: int) -> dict:
    """
    Get zone with all its furniture for map editor.

    Args:
        zone_id: Zone ID

    Returns:
        Dict with zone data and furniture list, or None if not found
    """
    db = get_db()
    cursor = db.cursor()

    # Get zone
    cursor.execute('SELECT * FROM beach_zones WHERE id = ?', (zone_id,))
    zone_row = cursor.fetchone()
    if not zone_row:
        return None

    zone = dict(zone_row)

    # Get furniture with type info
    cursor.execute('''
        SELECT f.*,
               ft.display_name as furniture_type_name,
               ft.icon as furniture_type_icon,
               ft.map_shape,
               ft.fill_color as type_fill_color,
               ft.stroke_color as type_stroke_color,
               ft.stroke_width as type_stroke_width,
               ft.border_radius as type_border_radius,
               ft.is_decorative
        FROM beach_furniture f
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        WHERE f.zone_id = ? AND f.active = 1
        ORDER BY f.number
    ''', (zone_id,))

    zone['furniture'] = [dict(row) for row in cursor.fetchall()]
    return zone
