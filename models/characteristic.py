"""
Characteristic data access functions.
CRUD operations for the unified caracteristicas system.
"""

from database import get_db


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_all_characteristics(active_only: bool = True) -> list:
    """
    Get all characteristics.

    Args:
        active_only: If True, only return active characteristics

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        query = '''
            SELECT c.*,
                   (SELECT COUNT(*) FROM beach_furniture_characteristics
                    WHERE characteristic_id = c.id) as furniture_count,
                   (SELECT COUNT(*) FROM beach_reservation_characteristics
                    WHERE characteristic_id = c.id) as reservation_count,
                   (SELECT COUNT(*) FROM beach_customer_characteristics
                    WHERE characteristic_id = c.id) as customer_count
            FROM beach_characteristics c
        '''

        if active_only:
            query += ' WHERE c.active = 1'

        query += ' ORDER BY c.display_order, c.name'

        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def get_characteristic_by_id(characteristic_id: int) -> dict | None:
    """
    Get characteristic by ID.

    Args:
        characteristic_id: Characteristic ID

    Returns:
        Characteristic dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.execute(
            'SELECT * FROM beach_characteristics WHERE id = ?',
            (characteristic_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_characteristic_by_code(code: str) -> dict | None:
    """
    Get characteristic by code.

    Args:
        code: Characteristic code

    Returns:
        Characteristic dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.execute(
            'SELECT * FROM beach_characteristics WHERE code = ?',
            (code,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# =============================================================================
# CREATE OPERATIONS
# =============================================================================

def create_characteristic(
    code: str,
    name: str,
    description: str = None,
    icon: str = None,
    color: str = '#D4AF37'
) -> int:
    """
    Create new characteristic.

    Args:
        code: Unique characteristic code (snake_case)
        name: Display name
        description: Description text
        icon: FontAwesome icon class
        color: Hex color for UI display

    Returns:
        New characteristic ID

    Raises:
        ValueError: If code already exists
    """
    existing = get_characteristic_by_code(code)
    if existing:
        raise ValueError(f'Ya existe una caracteristica con el codigo "{code}"')

    with get_db() as conn:
        # Get next display_order
        cursor = conn.execute(
            'SELECT COALESCE(MAX(display_order), 0) + 1 FROM beach_characteristics'
        )
        next_order = cursor.fetchone()[0]

        cursor = conn.execute('''
            INSERT INTO beach_characteristics
            (code, name, description, icon, color, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, description, icon, color, next_order))

        conn.commit()
        return cursor.lastrowid


# =============================================================================
# UPDATE OPERATIONS
# =============================================================================

def update_characteristic(characteristic_id: int, **kwargs) -> bool:
    """
    Update characteristic fields.

    Args:
        characteristic_id: Characteristic ID to update
        **kwargs: Fields to update (name, description, icon, color, active)

    Returns:
        True if updated successfully
    """
    allowed_fields = ['name', 'description', 'icon', 'color', 'active', 'display_order']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(characteristic_id)
    query = f'UPDATE beach_characteristics SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def reorder_characteristics(ordered_ids: list) -> bool:
    """
    Reorder characteristics by setting display_order.

    Args:
        ordered_ids: List of characteristic IDs in desired order

    Returns:
        True if reordered successfully
    """
    with get_db() as conn:
        for order, char_id in enumerate(ordered_ids):
            conn.execute(
                'UPDATE beach_characteristics SET display_order = ? WHERE id = ?',
                (order, char_id)
            )
        conn.commit()
        return True


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

def delete_characteristic(characteristic_id: int, hard: bool = False) -> bool:
    """
    Delete characteristic.

    Args:
        characteristic_id: Characteristic ID to delete
        hard: If True, permanently delete. If False, soft delete (set active=0)

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        if hard:
            cursor = conn.execute(
                'DELETE FROM beach_characteristics WHERE id = ?',
                (characteristic_id,)
            )
        else:
            cursor = conn.execute(
                'UPDATE beach_characteristics SET active = 0 WHERE id = ?',
                (characteristic_id,)
            )
        conn.commit()
        return cursor.rowcount > 0
