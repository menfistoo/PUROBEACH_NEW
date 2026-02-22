"""
Beach tag data access functions.
Handles tag CRUD operations for customers and reservations.
"""

from database import get_db


def get_all_tags(active_only: bool = True) -> list:
    """
    Get all tags.

    Args:
        active_only: If True, only return active tags

    Returns:
        List of tag dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT t.*,
                   (SELECT COUNT(*) FROM beach_customer_tags WHERE tag_id = t.id) as customer_count,
                   (SELECT COUNT(*) FROM beach_reservation_tags WHERE tag_id = t.id) as reservation_count
            FROM beach_tags t
        '''

        if active_only:
            query += ' WHERE t.active = 1'

        query += ' ORDER BY t.name'

        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_tag_by_id(tag_id: int) -> dict:
    """
    Get tag by ID.

    Args:
        tag_id: Tag ID

    Returns:
        Tag dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_tags WHERE id = ?', (tag_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_tag_by_name(name: str) -> dict:
    """
    Get tag by name.

    Args:
        name: Tag name

    Returns:
        Tag dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_tags WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_tag(name: str, color: str = '#6C757D', description: str = None) -> int:
    """
    Create new tag.

    Args:
        name: Tag name (must be unique)
        color: Tag color (hex)
        description: Tag description

    Returns:
        New tag ID

    Raises:
        ValueError if name already exists
    """
    # Check if name exists
    existing = get_tag_by_name(name)
    if existing:
        raise ValueError(f'Ya existe una etiqueta con el nombre "{name}"')

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO beach_tags (name, color, description)
            VALUES (?, ?, ?)
        ''', (name, color, description))

        conn.commit()
        return cursor.lastrowid


def update_tag(tag_id: int, **kwargs) -> bool:
    """
    Update tag fields.

    Args:
        tag_id: Tag ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    allowed_fields = ['name', 'color', 'description', 'active']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(tag_id)
    query = f'UPDATE beach_tags SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        return cursor.rowcount > 0


def delete_tag(tag_id: int) -> bool:
    """
    Soft delete tag (set active = 0).

    Args:
        tag_id: Tag ID to delete

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE beach_tags SET active = 0
            WHERE id = ?
        ''', (tag_id,))

        conn.commit()
        return cursor.rowcount > 0


# Customer tag operations

def get_customer_tags(customer_id: int) -> list:
    """
    Get tags assigned to a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of tag dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*
            FROM beach_tags t
            JOIN beach_customer_tags ct ON t.id = ct.tag_id
            WHERE ct.customer_id = ?
            ORDER BY t.name
        ''', (customer_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def assign_tag_to_customer(customer_id: int, tag_id: int) -> bool:
    """
    Assign a tag to a customer.

    Args:
        customer_id: Customer ID
        tag_id: Tag ID

    Returns:
        True if assigned successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO beach_customer_tags (customer_id, tag_id)
                VALUES (?, ?)
            ''', (customer_id, tag_id))
            conn.commit()
            return True
        except Exception:
            return False


def remove_tag_from_customer(customer_id: int, tag_id: int) -> bool:
    """
    Remove a tag from a customer.

    Args:
        customer_id: Customer ID
        tag_id: Tag ID

    Returns:
        True if removed successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM beach_customer_tags
            WHERE customer_id = ? AND tag_id = ?
        ''', (customer_id, tag_id))

        conn.commit()
        return cursor.rowcount > 0


# Reservation tag operations

def get_reservation_tags(reservation_id: int) -> list:
    """
    Get tags assigned to a reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        List of tag dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*
            FROM beach_tags t
            JOIN beach_reservation_tags rt ON t.id = rt.tag_id
            WHERE rt.reservation_id = ?
            ORDER BY t.name
        ''', (reservation_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def assign_tag_to_reservation(reservation_id: int, tag_id: int) -> bool:
    """
    Assign a tag to a reservation.

    Args:
        reservation_id: Reservation ID
        tag_id: Tag ID

    Returns:
        True if assigned successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR IGNORE INTO beach_reservation_tags (reservation_id, tag_id)
                VALUES (?, ?)
            ''', (reservation_id, tag_id))
            conn.commit()
            return True
        except Exception:
            return False


def set_reservation_tags(reservation_id: int, tag_ids: list) -> None:
    """
    Set reservation tags (replaces existing).

    Args:
        reservation_id: Reservation ID
        tag_ids: List of tag IDs to assign
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM beach_reservation_tags WHERE reservation_id = ?',
            (reservation_id,)
        )
        for tag_id in tag_ids:
            cursor.execute('''
                INSERT OR IGNORE INTO beach_reservation_tags (reservation_id, tag_id)
                VALUES (?, ?)
            ''', (reservation_id, int(tag_id)))
        conn.commit()


def sync_reservation_tags_to_customer(reservation_id: int, tag_ids: list, replace: bool = False) -> None:
    """
    Sync reservation tags to the customer.

    Args:
        reservation_id: Reservation ID (to look up customer_id)
        tag_ids: List of tag IDs from the reservation
        replace: If True, replaces customer tags entirely.
                 If False, only adds new tags (merge/append).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # Get customer_id from reservation
        cursor.execute(
            'SELECT customer_id FROM beach_reservations WHERE id = ?',
            (reservation_id,)
        )
        row = cursor.fetchone()
        if not row or not row['customer_id']:
            return
        customer_id = row['customer_id']

        if replace:
            cursor.execute(
                'DELETE FROM beach_customer_tags WHERE customer_id = ?',
                (customer_id,)
            )

        for tag_id in tag_ids:
            cursor.execute('''
                INSERT OR IGNORE INTO beach_customer_tags (customer_id, tag_id)
                VALUES (?, ?)
            ''', (customer_id, int(tag_id)))
        conn.commit()


def sync_customer_tags_to_reservations(customer_id: int, tag_ids: list, replace: bool = False) -> None:
    """
    Sync customer tags to all active/future reservations.

    Args:
        customer_id: Customer ID
        tag_ids: List of tag IDs from the customer
        replace: If True, replaces reservation tags entirely.
                 If False, only adds new tags (merge/append).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # Get active/future reservations for this customer
        cursor.execute('''
            SELECT id FROM beach_reservations
            WHERE customer_id = ?
            AND (start_date >= date('now') OR end_date >= date('now'))
        ''', (customer_id,))
        reservation_ids = [r['id'] for r in cursor.fetchall()]

        for res_id in reservation_ids:
            if replace:
                # Remove existing tags first
                cursor.execute(
                    'DELETE FROM beach_reservation_tags WHERE reservation_id = ?',
                    (res_id,)
                )
            # Add tags
            for tag_id in tag_ids:
                cursor.execute('''
                    INSERT OR IGNORE INTO beach_reservation_tags (reservation_id, tag_id)
                    VALUES (?, ?)
                ''', (res_id, int(tag_id)))
        conn.commit()


def remove_tag_from_reservation(reservation_id: int, tag_id: int) -> bool:
    """
    Remove a tag from a reservation.

    Args:
        reservation_id: Reservation ID
        tag_id: Tag ID

    Returns:
        True if removed successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM beach_reservation_tags
            WHERE reservation_id = ? AND tag_id = ?
        ''', (reservation_id, tag_id))

        conn.commit()
        return cursor.rowcount > 0
