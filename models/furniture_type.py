"""
Beach furniture type data access functions.
Handles furniture type CRUD operations with enhanced SVG rendering,
auto-numbering, and advanced configuration support.
"""

import json
from typing import Tuple, Optional
from database import get_db


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_all_furniture_types(active_only: bool = True) -> list:
    """
    Get all furniture types.

    Args:
        active_only: If True, only return active types

    Returns:
        List of furniture type dicts sorted by display_order
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT ft.*,
                   (SELECT COUNT(*) FROM beach_furniture
                    WHERE furniture_type = ft.type_code AND active = 1) as furniture_count
            FROM beach_furniture_types ft
        '''

        if active_only:
            query += ' WHERE ft.active = 1'

        query += ' ORDER BY ft.display_order, ft.display_name'

        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_furniture_type_by_id(type_id: int) -> Optional[dict]:
    """
    Get furniture type by ID.

    Args:
        type_id: Furniture type ID

    Returns:
        Furniture type dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_furniture_types WHERE id = ?', (type_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_furniture_type_by_code(type_code: str) -> Optional[dict]:
    """
    Get furniture type by code.

    Args:
        type_code: Furniture type code

    Returns:
        Furniture type dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_furniture_types WHERE type_code = ?', (type_code,))
        row = cursor.fetchone()
        return dict(row) if row else None


# =============================================================================
# CREATE OPERATIONS
# =============================================================================

def create_furniture_type(type_code: str, display_name: str, **kwargs) -> int:
    """
    Create new furniture type with enhanced fields.

    Args:
        type_code: Unique type code
        display_name: Display name
        **kwargs: Optional fields:
            - icon: FontAwesome icon class
            - default_color: Default color for map display
            - min_capacity, max_capacity, default_capacity: Capacity settings
            - is_suite_only: If 1, only for suite guests
            - notes: Additional notes
            - map_shape: SVG shape type (rounded_rect, circle, ellipse, custom)
            - custom_svg: Custom SVG code
            - default_width, default_height: Dimensions
            - border_radius: Border radius for rectangles
            - fill_color, stroke_color, stroke_width: SVG styling
            - status_colors: JSON with colors per state
            - default_rotation: Default rotation (0 or 1)
            - is_decorative: If 1, not reservable
            - number_prefix: Prefix for auto-numbering
            - number_start: Starting number
            - default_features: CSV of default features
            - allowed_zones: CSV of allowed zone IDs
            - display_order: Display order in lists

    Returns:
        New furniture type ID

    Raises:
        ValueError if type_code already exists or validation fails
    """
    # Validate
    data = {'type_code': type_code, 'display_name': display_name, **kwargs}
    is_valid, errors = validate_furniture_type_data(data, is_update=False)
    if not is_valid:
        raise ValueError('; '.join(errors.values()))

    with get_db() as conn:
        cursor = conn.cursor()

        # Build dynamic insert
        fields = ['type_code', 'display_name']
        values = [type_code, display_name]

        optional_fields = [
            'icon', 'default_color', 'min_capacity', 'max_capacity', 'is_suite_only', 'notes',
            'map_shape', 'custom_svg', 'default_width', 'default_height',
            'border_radius', 'fill_color', 'stroke_color', 'stroke_width', 'status_colors',
            'default_capacity', 'default_rotation', 'is_decorative',
            'number_prefix', 'number_start', 'default_features', 'allowed_zones', 'display_order'
        ]

        for field in optional_fields:
            if field in kwargs and kwargs[field] is not None:
                fields.append(field)
                values.append(kwargs[field])

        placeholders = ', '.join(['?' for _ in fields])
        query = f'INSERT INTO beach_furniture_types ({", ".join(fields)}) VALUES ({placeholders})'

        cursor.execute(query, values)
        conn.commit()
        return cursor.lastrowid


# =============================================================================
# UPDATE OPERATIONS
# =============================================================================

def update_furniture_type(type_id: int, **kwargs) -> bool:
    """
    Update furniture type fields.

    Args:
        type_id: Furniture type ID to update
        **kwargs: Fields to update (see create_furniture_type for list)

    Returns:
        True if updated successfully

    Raises:
        ValueError if validation fails
    """
    # Validate
    is_valid, errors = validate_furniture_type_data(kwargs, is_update=True)
    if not is_valid:
        raise ValueError('; '.join(errors.values()))

    # Extended allowed fields
    allowed_fields = [
        'display_name', 'icon', 'default_color', 'min_capacity', 'max_capacity',
        'is_suite_only', 'notes', 'active',
        'map_shape', 'custom_svg', 'default_width', 'default_height',
        'border_radius', 'fill_color', 'stroke_color', 'stroke_width', 'status_colors',
        'default_capacity', 'default_rotation', 'is_decorative',
        'number_prefix', 'number_start', 'default_features', 'allowed_zones', 'display_order'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(type_id)
    query = f'UPDATE beach_furniture_types SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        return cursor.rowcount > 0


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

def delete_furniture_type(type_id: int) -> bool:
    """
    Soft delete furniture type (set active = 0).
    Only allowed if no active furniture uses this type.

    Args:
        type_id: Furniture type ID to delete

    Returns:
        True if deleted successfully

    Raises:
        ValueError if type has active furniture
    """
    # Get type code
    ftype = get_furniture_type_by_id(type_id)
    if not ftype:
        return False

    with get_db() as conn:
        cursor = conn.cursor()

        # Check for active furniture using this type
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM beach_furniture
            WHERE furniture_type = ? AND active = 1
        ''', (ftype['type_code'],))

        if cursor.fetchone()['count'] > 0:
            raise ValueError('No se puede eliminar tipo con mobiliario activo')

        cursor.execute('''
            UPDATE beach_furniture_types SET active = 0
            WHERE id = ?
        ''', (type_id,))

        conn.commit()
        return cursor.rowcount > 0


# =============================================================================
# AUTO-NUMBERING
# =============================================================================

def get_next_number_for_type(type_id: int, zone_id: int = None) -> str:
    """
    Get the next available number for a furniture type.

    Finds the first available gap in the sequence, reusing numbers
    from deleted furniture.

    Follows pattern: {prefix}{number} where number starts at number_start
    and fills gaps before incrementing past existing numbers.

    Args:
        type_id: Furniture type ID
        zone_id: Optional zone filter for zone-specific numbering

    Returns:
        Next available number string (e.g., "H15", "B3")
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get type config
        cursor.execute('''
            SELECT type_code, number_prefix, number_start
            FROM beach_furniture_types WHERE id = ?
        ''', (type_id,))
        ftype = cursor.fetchone()

        if not ftype:
            return "1"

        prefix = ftype['number_prefix'] or ''
        start = ftype['number_start'] or 1
        type_code = ftype['type_code']

        # Get all existing numbers for this type
        query = '''
            SELECT number FROM beach_furniture
            WHERE furniture_type = ? AND active = 1
        '''
        params = [type_code]

        if prefix:
            query += ' AND number LIKE ? || \'%\''
            params.append(prefix)

        if zone_id:
            query += ' AND zone_id = ?'
            params.append(zone_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Extract numeric parts and build a set of used numbers
        used_numbers = set()
        for row in rows:
            try:
                if prefix:
                    num_str = row['number'][len(prefix):]
                else:
                    num_str = row['number']
                num = int(num_str)
                used_numbers.add(num)
            except (ValueError, IndexError):
                continue

        # Find first available number starting from 'start'
        next_num = start
        while next_num in used_numbers:
            next_num += 1

        return f"{prefix}{next_num}"


# =============================================================================
# SVG RENDERING
# =============================================================================

def get_furniture_type_svg(type_config: dict, state: str = None,
                           width: float = None, height: float = None,
                           state_colors: dict = None) -> str:
    """
    Generate SVG representation for a furniture type.

    Args:
        type_config: Furniture type configuration dict
        state: Current state for color lookup (None = use fill_color)
        width: Override width (uses default if None)
        height: Override height (uses default if None)
        state_colors: Optional dict of state->color mappings from reservation states config

    Returns:
        SVG string for the furniture shape

    Note:
        Status colors are NOT stored per furniture type. They come from the global
        reservation states configuration (beach_reservation_states table).
        When rendering on the map, pass state_colors from get_all_reservation_states().
    """
    shape_type = type_config.get('map_shape', 'rounded_rect')
    w = width or type_config.get('default_width', 60)
    h = height or type_config.get('default_height', 40)
    border_radius = type_config.get('border_radius', 5)
    stroke_width = type_config.get('stroke_width', 2)
    stroke_color = type_config.get('stroke_color', '#654321')

    # Determine fill color:
    # 1. If state and state_colors provided, use state color
    # 2. Otherwise use fill_color from type config
    if state and state_colors and state in state_colors:
        fill_color = state_colors[state]
    else:
        fill_color = type_config.get('fill_color', type_config.get('default_color', '#D2B48C'))

    if shape_type in ('rounded_rect', 'rectangle'):
        return f'''<rect x="{stroke_width}" y="{stroke_width}"
                        width="{w - 2*stroke_width}" height="{h - 2*stroke_width}"
                        rx="{border_radius}" ry="{border_radius}"
                        fill="{fill_color}"
                        stroke="{stroke_color}"
                        stroke-width="{stroke_width}"/>'''

    elif shape_type == 'circle':
        radius = min(w, h) / 2 - stroke_width
        cx = w / 2
        cy = h / 2
        return f'''<circle cx="{cx}" cy="{cy}" r="{radius}"
                          fill="{fill_color}"
                          stroke="{stroke_color}"
                          stroke-width="{stroke_width}"/>'''

    elif shape_type == 'ellipse':
        rx = w / 2 - stroke_width
        ry = h / 2 - stroke_width
        cx = w / 2
        cy = h / 2
        return f'''<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"
                           fill="{fill_color}"
                           stroke="{stroke_color}"
                           stroke-width="{stroke_width}"/>'''

    elif shape_type == 'custom':
        custom_code = type_config.get('custom_svg', '')
        # Replace color placeholders if present
        custom_code = custom_code.replace('{{fill}}', fill_color)
        custom_code = custom_code.replace('{{stroke}}', stroke_color)
        custom_code = custom_code.replace('{fill}', fill_color)
        custom_code = custom_code.replace('{stroke}', stroke_color)
        return custom_code

    # Default fallback
    return f'<rect width="{w}" height="{h}" fill="{fill_color}"/>'


# =============================================================================
# VALIDATION
# =============================================================================

def validate_furniture_type_data(data: dict, is_update: bool = False) -> Tuple[bool, dict]:
    """
    Validate furniture type form data.

    Args:
        data: Form data dict
        is_update: True if updating existing record

    Returns:
        Tuple of (is_valid, errors_dict)
    """
    errors = {}

    # Required fields (only for create)
    if not is_update:
        type_code = data.get('type_code', '').strip().lower() if data.get('type_code') else ''
        if not type_code:
            errors['type_code'] = 'El código es obligatorio'
        elif not type_code.replace('_', '').isalnum():
            errors['type_code'] = 'Solo letras, números y guiones bajos'
        elif len(type_code) > 50:
            errors['type_code'] = 'Máximo 50 caracteres'
        else:
            # Check uniqueness
            existing = get_furniture_type_by_code(type_code)
            if existing:
                errors['type_code'] = f'Ya existe un tipo con código "{type_code}"'

    # Display name validation
    if 'display_name' in data:
        display_name = data.get('display_name', '').strip() if data.get('display_name') else ''
        if not is_update and not display_name:
            errors['display_name'] = 'El nombre es obligatorio'
        elif display_name and len(display_name) > 100:
            errors['display_name'] = 'Máximo 100 caracteres'

    # Capacity validation
    if any(k in data for k in ['min_capacity', 'max_capacity', 'default_capacity']):
        try:
            min_cap = int(data.get('min_capacity', 0) or 0)
            max_cap = int(data.get('max_capacity', 4) or 4)
            default_cap = int(data.get('default_capacity', 1) or 1)

            if min_cap < 0:
                errors['min_capacity'] = 'No puede ser negativo'
            if max_cap < 0:
                errors['max_capacity'] = 'No puede ser negativo'
            if max_cap > 0 and max_cap < min_cap:
                errors['max_capacity'] = 'Debe ser mayor o igual a capacidad mínima'
            if default_cap < min_cap or (max_cap > 0 and default_cap > max_cap):
                errors['default_capacity'] = 'Debe estar entre mínimo y máximo'
        except (ValueError, TypeError):
            errors['capacity'] = 'Los valores de capacidad deben ser números enteros'

    # Dimension validation
    if any(k in data for k in ['default_width', 'default_height']):
        try:
            if 'default_width' in data:
                width = float(data.get('default_width', 60) or 60)
                if width <= 0 or width > 500:
                    errors['default_width'] = 'Ancho debe ser entre 1 y 500'
            if 'default_height' in data:
                height = float(data.get('default_height', 40) or 40)
                if height <= 0 or height > 500:
                    errors['default_height'] = 'Alto debe ser entre 1 y 500'
        except (ValueError, TypeError):
            errors['dimensions'] = 'Las dimensiones deben ser números válidos'

    # SVG shape validation
    if 'map_shape' in data:
        map_shape = data.get('map_shape', 'rounded_rect')
        valid_shapes = ['rounded_rect', 'rectangle', 'circle', 'ellipse', 'custom']
        if map_shape and map_shape not in valid_shapes:
            errors['map_shape'] = f'Forma debe ser: {", ".join(valid_shapes)}'

    # Custom SVG validation
    if data.get('map_shape') == 'custom' or data.get('custom_svg'):
        custom_svg = data.get('custom_svg', '').strip() if data.get('custom_svg') else ''
        if data.get('map_shape') == 'custom' and not custom_svg:
            errors['custom_svg'] = 'Código SVG requerido para forma personalizada'
        # Basic XSS prevention
        if custom_svg:
            dangerous_tags = ['<script', 'javascript:', 'onclick', 'onerror', 'onload']
            for tag in dangerous_tags:
                if tag.lower() in custom_svg.lower():
                    errors['custom_svg'] = 'Código SVG contiene elementos no permitidos'
                    break

    # Status colors validation (JSON)
    if 'status_colors' in data and data.get('status_colors'):
        status_colors = data.get('status_colors', '')
        if status_colors:
            try:
                colors = json.loads(status_colors) if isinstance(status_colors, str) else status_colors
                required_states = ['available', 'reserved', 'occupied', 'maintenance']
                for state in required_states:
                    if state not in colors:
                        errors['status_colors'] = f'Falta color para estado: {state}'
                        break
            except json.JSONDecodeError:
                errors['status_colors'] = 'Formato JSON inválido'

    # Decorative element capacity check
    if data.get('is_decorative') and int(data.get('is_decorative', 0)):
        cap_fields = ['min_capacity', 'max_capacity', 'default_capacity']
        for field in cap_fields:
            if field in data:
                try:
                    val = int(data.get(field, 0) or 0)
                    if val > 0:
                        errors['is_decorative'] = 'Elementos decorativos deben tener capacidad 0'
                        break
                except (ValueError, TypeError):
                    pass

    return (len(errors) == 0, errors)


# =============================================================================
# DISPLAY ORDER
# =============================================================================

def update_furniture_types_order(type_ids: list) -> bool:
    """
    Update display order for multiple furniture types.

    Args:
        type_ids: List of type IDs in desired order

    Returns:
        True if updated successfully
    """
    if not type_ids:
        return False

    with get_db() as conn:
        cursor = conn.cursor()

        conn.execute('BEGIN IMMEDIATE')
        try:
            for order, type_id in enumerate(type_ids, start=1):
                cursor.execute('''
                    UPDATE beach_furniture_types SET display_order = ?
                    WHERE id = ?
                ''', (order, type_id))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
