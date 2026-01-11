"""
Beach furniture data access functions.
Handles furniture CRUD operations and furniture type management.
"""

import json
from database import get_db
from datetime import datetime


def get_all_furniture(zone_id: int = None, active_only: bool = True,
                      for_date: str = None) -> list:
    """
    Get all beach furniture.

    Args:
        zone_id: Filter by zone ID (optional)
        active_only: If True, only return active furniture
        for_date: Date string YYYY-MM-DD for filtering temporary furniture (optional)
                  If provided, temporary furniture is only included if for_date
                  falls within temp_start_date and temp_end_date

    Returns:
        List of furniture dicts with zone information
    """
    with get_db() as conn:
        cursor = conn.cursor()

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

        # Filter temporary furniture by date range
        if for_date:
            query += '''
                AND (
                    f.is_temporary = 0
                    OR (f.is_temporary = 1
                        AND DATE(f.temp_start_date) <= DATE(?)
                        AND DATE(f.temp_end_date) >= DATE(?))
                )
            '''
            params.append(for_date)
            params.append(for_date)

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
    with get_db() as conn:
        cursor = conn.cursor()
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
    with get_db() as conn:
        cursor = conn.cursor()
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
                  features can be a list of codes, JSON string, or comma-separated string

    Returns:
        New furniture ID
    """
    with get_db() as conn:
        cursor = conn.cursor()

        rotation = kwargs.get('rotation', 0)
        width = kwargs.get('width', 60)
        height = kwargs.get('height', 40)
        features_input = kwargs.get('features', '')
        is_temporary = kwargs.get('is_temporary', 0)
        valid_date = kwargs.get('valid_date', None)
        fill_color = kwargs.get('fill_color', None)

        # Convert features to JSON string for legacy column
        features_json = _normalize_features_to_json(features_input)

        cursor.execute('''
            INSERT INTO beach_furniture
            (number, zone_id, furniture_type, capacity, position_x, position_y,
             rotation, width, height, features, is_temporary, valid_date, fill_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (number, zone_id, furniture_type, capacity, position_x, position_y,
              rotation, width, height, features_json, is_temporary, valid_date, fill_color))

        furniture_id = cursor.lastrowid
        conn.commit()

        # Sync to junction table
        _sync_features_to_junction_table(furniture_id, features_input)

        return furniture_id


def update_furniture(furniture_id: int, **kwargs) -> bool:
    """
    Update furniture fields.

    Args:
        furniture_id: Furniture ID to update
        **kwargs: Fields to update (features can be list, JSON, or comma-separated)

    Returns:
        True if updated successfully
    """
    features_input = kwargs.pop('features', None)

    with get_db() as conn:
        allowed_fields = ['number', 'zone_id', 'capacity', 'position_x', 'position_y',
                          'rotation', 'width', 'height', 'active', 'fill_color']
        updates = []
        values = []

        for field in allowed_fields:
            if field in kwargs:
                updates.append(f'{field} = ?')
                values.append(kwargs[field])

        # Handle features separately - normalize and add to update
        if features_input is not None:
            features_json = _normalize_features_to_json(features_input)
            updates.append('features = ?')
            values.append(features_json)

        if not updates:
            # Even if no DB fields to update, sync features if provided
            if features_input is not None:
                _sync_features_to_junction_table(furniture_id, features_input)
                return True
            return False

        values.append(furniture_id)
        query = f'UPDATE beach_furniture SET {", ".join(updates)} WHERE id = ?'

        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        # Sync features to junction table
        if features_input is not None:
            _sync_features_to_junction_table(furniture_id, features_input)

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
    with get_db() as conn:
        cursor = conn.cursor()

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

        conn.commit()
        return cursor.rowcount > 0


def get_temporary_furniture(date: str) -> list:
    """
    Get temporary furniture valid for a specific date.

    Args:
        date: Date string (YYYY-MM-DD)

    Returns:
        List of temporary furniture dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
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
    with get_db() as conn:
        cursor = conn.cursor()

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


# =============================================================================
# AUTO-POSITIONING FUNCTIONS (Phase 7: Interactive Map)
# =============================================================================

import math


def auto_position_furniture_in_zone(zone_id: int, zone_bounds: dict) -> int:
    """
    Auto-arrange furniture in a grid layout within a zone.

    Args:
        zone_id: Zone ID to position furniture in
        zone_bounds: Dict with x, y, width, height for zone area

    Returns:
        Number of furniture items positioned
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get furniture in this zone
        cursor.execute('''
            SELECT f.id, f.width, f.height
            FROM beach_furniture f
            WHERE f.zone_id = ? AND f.active = 1
            ORDER BY f.number
        ''', (zone_id,))
        furniture_items = cursor.fetchall()

        if not furniture_items:
            return 0

        count = len(furniture_items)
        zone_x = zone_bounds['x']
        zone_y = zone_bounds['y']
        zone_width = zone_bounds['width']

        # Calculate grid layout
        padding = 20  # Space between items
        avg_width = 70  # Average furniture width for column calculation

        # Calculate columns that fit in zone width
        cols = max(1, int((zone_width - padding) / (avg_width + padding)))
        rows = math.ceil(count / cols)

        # Position each item
        positioned = 0
        for idx, item in enumerate(furniture_items):
            col = idx % cols
            row = idx // cols

            item_width = item['width'] or 60
            item_height = item['height'] or 40

            # Calculate position with padding
            pos_x = zone_x + padding + col * (avg_width + padding) + (avg_width - item_width) / 2
            pos_y = zone_y + padding + row * (item_height + padding)

            cursor.execute('''
                UPDATE beach_furniture
                SET position_x = ?, position_y = ?
                WHERE id = ?
            ''', (pos_x, pos_y, item['id']))
            positioned += 1

        conn.commit()
        return positioned


def setup_initial_furniture_positions(map_width: int = 1200, zone_height: int = 200,
                                       zone_padding: int = 20) -> dict:
    """
    Generate initial positions for all furniture items.
    Uses vertical zone stacking with grid layout within each zone.

    Args:
        map_width: Total map width in pixels
        zone_height: Height per zone in pixels
        zone_padding: Padding between zones

    Returns:
        Dict with zone counts and total positioned
    """
    from models.zone import get_all_zones

    zones = get_all_zones(active_only=True)
    results = {'zones': {}, 'total': 0}

    for idx, zone in enumerate(zones):
        # Calculate zone bounds (vertical stacking)
        zone_bounds = {
            'x': zone_padding,
            'y': zone_padding + idx * (zone_height + zone_padding),
            'width': map_width - 2 * zone_padding,
            'height': zone_height
        }

        count = auto_position_furniture_in_zone(zone['id'], zone_bounds)
        results['zones'][zone['name']] = count
        results['total'] += count

    return results


def get_furniture_needing_position() -> list:
    """
    Get furniture items with position at origin (0, 0).

    Returns:
        List of furniture IDs needing positioning
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, number, zone_id
            FROM beach_furniture
            WHERE position_x = 0 AND position_y = 0 AND active = 1
        ''')
        return [dict(row) for row in cursor.fetchall()]


def update_furniture_position(furniture_id: int, x: float, y: float,
                               rotation: int = None) -> bool:
    """
    Update furniture position (used by drag-and-drop).

    Args:
        furniture_id: Furniture ID
        x: New X position
        y: New Y position
        rotation: New rotation (optional)

    Returns:
        True if updated successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if rotation is not None:
            cursor.execute('''
                UPDATE beach_furniture
                SET position_x = ?, position_y = ?, rotation = ?
                WHERE id = ?
            ''', (x, y, rotation, furniture_id))
        else:
            cursor.execute('''
                UPDATE beach_furniture
                SET position_x = ?, position_y = ?
                WHERE id = ?
            ''', (x, y, furniture_id))

        conn.commit()
        return cursor.rowcount > 0


def batch_update_furniture_positions(updates: list) -> int:
    """
    Batch update multiple furniture positions.

    Args:
        updates: List of dicts with id, x, y, rotation (optional)

    Returns:
        Number of items updated
    """
    with get_db() as conn:
        cursor = conn.cursor()

        updated = 0
        for item in updates:
            if 'rotation' in item:
                cursor.execute('''
                    UPDATE beach_furniture
                    SET position_x = ?, position_y = ?, rotation = ?
                    WHERE id = ?
                ''', (item['x'], item['y'], item['rotation'], item['id']))
            else:
                cursor.execute('''
                    UPDATE beach_furniture
                    SET position_x = ?, position_y = ?
                    WHERE id = ?
                ''', (item['x'], item['y'], item['id']))
            updated += cursor.rowcount

        conn.commit()
        return updated


# =============================================================================
# HELPER FUNCTIONS FOR CHARACTERISTICS SYNC
# =============================================================================

def _normalize_features_to_json(features_input) -> str:
    """
    Normalize features input to JSON string for legacy column.

    Args:
        features_input: Can be list, JSON string, or comma-separated string

    Returns:
        JSON string (e.g., '["primera_linea", "sombra"]')
    """
    if not features_input:
        return '[]'

    # Already a list
    if isinstance(features_input, list):
        return json.dumps(features_input)

    # Try to parse as JSON
    if isinstance(features_input, str):
        try:
            parsed = json.loads(features_input)
            if isinstance(parsed, list):
                return features_input  # Already valid JSON
        except json.JSONDecodeError:
            pass

        # Comma-separated string
        codes = [c.strip() for c in features_input.split(',') if c.strip()]
        return json.dumps(codes)

    return '[]'


def _parse_features_to_codes(features_input) -> list:
    """
    Parse features input to list of codes.

    Args:
        features_input: Can be list, JSON string, or comma-separated string

    Returns:
        List of feature codes
    """
    if not features_input:
        return []

    # Already a list
    if isinstance(features_input, list):
        return features_input

    # Try to parse as JSON
    if isinstance(features_input, str):
        try:
            parsed = json.loads(features_input)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Comma-separated string
        return [c.strip() for c in features_input.split(',') if c.strip()]

    return []


def _sync_features_to_junction_table(furniture_id: int, features_input) -> None:
    """
    Sync features to beach_furniture_characteristics junction table.

    Args:
        furniture_id: Furniture ID
        features_input: Features in any format (list, JSON, comma-separated)
    """
    from models.characteristic import get_characteristic_by_code
    from models.characteristic_assignments import set_furniture_characteristics

    codes = _parse_features_to_codes(features_input)

    if not codes:
        # Clear all characteristics
        set_furniture_characteristics(furniture_id, [])
        return

    # Convert codes to IDs
    char_ids = []
    for code in codes:
        char = get_characteristic_by_code(code)
        if char:
            char_ids.append(char['id'])

    set_furniture_characteristics(furniture_id, char_ids)
