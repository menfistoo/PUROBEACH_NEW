"""
Customer CRUD operations.
Handles create, read, update, delete, and preferences/tags management.
"""

from database import get_db


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_all_customers(customer_type: str = None) -> list:
    """
    Get all customers.

    Args:
        customer_type: Filter by type ('interno'/'externo'), None for all

    Returns:
        List of customer dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT c.*,
                   (SELECT COUNT(*) FROM beach_reservations WHERE customer_id = c.id) as reservation_count
            FROM beach_customers c
            WHERE 1=1
        '''

        params = []

        if customer_type:
            query += ' AND c.customer_type = ?'
            params.append(customer_type)

        query += ' ORDER BY c.created_at DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_customer_by_id(customer_id: int) -> dict:
    """
    Get customer by ID.

    Args:
        customer_id: Customer ID

    Returns:
        Customer dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_customers WHERE id = ?', (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def search_customers(query: str, customer_type: str = None) -> list:
    """
    Search customers by name, phone, or email.

    Args:
        query: Search query string
        customer_type: Filter by type (optional)

    Returns:
        List of matching customer dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        search_query = '''
            SELECT * FROM beach_customers
            WHERE (first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone LIKE ? OR room_number LIKE ?)
        '''

        params = [f'%{query}%'] * 5

        if customer_type:
            search_query += ' AND customer_type = ?'
            params.append(customer_type)

        search_query += ' ORDER BY created_at DESC LIMIT 50'

        cursor.execute(search_query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# =============================================================================
# CREATE / UPDATE / DELETE
# =============================================================================

def create_customer(customer_type: str, first_name: str, last_name: str = None, **kwargs) -> int:
    """
    Create new customer.

    Args:
        customer_type: 'interno' or 'externo'
        first_name: First name (required)
        last_name: Last name
        **kwargs: Optional fields (email, phone, room_number, notes, vip_status, language, country_code)

    Returns:
        New customer ID

    Raises:
        ValueError if interno customer missing room_number
    """
    if customer_type == 'interno' and not kwargs.get('room_number'):
        raise ValueError('El número de habitación es requerido para clientes internos')

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO beach_customers
            (customer_type, first_name, last_name, email, phone, room_number, notes, vip_status, language, country_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_type, first_name, last_name,
              kwargs.get('email'), kwargs.get('phone'), kwargs.get('room_number'),
              kwargs.get('notes'), kwargs.get('vip_status', 0),
              kwargs.get('language'), kwargs.get('country_code', '+34')))

        conn.commit()
        return cursor.lastrowid


def update_customer(customer_id: int, **kwargs) -> bool:
    """
    Update customer fields.

    Args:
        customer_id: Customer ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'room_number',
                      'notes', 'vip_status', 'total_visits', 'total_spent', 'last_visit',
                      'language', 'country_code', 'no_shows', 'cancellations', 'total_reservations']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(customer_id)

    query = f'UPDATE beach_customers SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        return cursor.rowcount > 0


def delete_customer(customer_id: int) -> bool:
    """
    Delete customer (hard delete).
    Only allowed if no active reservations.

    Handles cascade deletion of:
    - Past reservations (and their furniture, daily_states, tags via CASCADE)
    - Reservation status history
    - Waitlist converted_reservation_id references

    Args:
        customer_id: Customer ID to delete

    Returns:
        True if deleted successfully

    Raises:
        ValueError if customer has active reservations
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check for active reservations
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM beach_reservations
            WHERE customer_id = ?
              AND end_date >= date('now')
        ''', (customer_id,))

        if cursor.fetchone()['count'] > 0:
            raise ValueError('No se puede eliminar cliente con reservas activas')

        # Get all reservation IDs for this customer (to clean up references)
        cursor.execute(
            'SELECT id FROM beach_reservations WHERE customer_id = ?',
            (customer_id,)
        )
        reservation_ids = [row['id'] for row in cursor.fetchall()]

        if reservation_ids:
            placeholders = ','.join('?' * len(reservation_ids))

            # Clear parent_reservation_id references (child reservations pointing to these)
            cursor.execute(f'''
                UPDATE beach_reservations
                SET parent_reservation_id = NULL
                WHERE parent_reservation_id IN ({placeholders})
            ''', reservation_ids)

            # Clear converted_reservation_id in waitlist
            cursor.execute(f'''
                UPDATE beach_waitlist
                SET converted_reservation_id = NULL
                WHERE converted_reservation_id IN ({placeholders})
            ''', reservation_ids)

            # Delete reservation status history
            cursor.execute(f'''
                DELETE FROM reservation_status_history
                WHERE reservation_id IN ({placeholders})
            ''', reservation_ids)

            # Delete reservations (furniture, daily_states, tags cascade automatically)
            cursor.execute(f'''
                DELETE FROM beach_reservations
                WHERE id IN ({placeholders})
            ''', reservation_ids)

        # Delete customer (customer_tags, customer_preferences, waitlist cascade automatically)
        cursor.execute('DELETE FROM beach_customers WHERE id = ?', (customer_id,))
        conn.commit()

        return cursor.rowcount > 0


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def find_duplicates(phone: str, customer_type: str, room_number: str = None) -> list:
    """
    Find potential duplicate customers.

    Args:
        phone: Phone number to check
        customer_type: Customer type
        room_number: Room number (for interno customers)

    Returns:
        List of potential duplicate customer dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if customer_type == 'interno' and room_number:
            cursor.execute('''
                SELECT * FROM beach_customers
                WHERE customer_type = 'interno'
                  AND (phone = ? OR room_number = ?)
                ORDER BY created_at DESC
            ''', (phone, room_number))
        else:
            cursor.execute('''
                SELECT * FROM beach_customers
                WHERE customer_type = 'externo' AND phone = ?
                ORDER BY created_at DESC
            ''', (phone,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# =============================================================================
# PREFERENCES (NOW CHARACTERISTICS)
# =============================================================================

def get_customer_preferences(customer_id: int) -> list:
    """
    Get customer preferences (characteristics).

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_customer_characteristics cc ON c.id = cc.characteristic_id
            WHERE cc.customer_id = ?
            ORDER BY c.display_order, c.name
        ''', (customer_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def set_customer_preferences(customer_id: int, preference_ids: list) -> None:
    """
    Set customer preferences (characteristics) - replaces existing.

    Args:
        customer_id: Customer ID
        preference_ids: List of characteristic IDs to assign
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Remove existing characteristics
        cursor.execute('DELETE FROM beach_customer_characteristics WHERE customer_id = ?', (customer_id,))

        # Add new characteristics
        for char_id in preference_ids:
            cursor.execute('''
                INSERT INTO beach_customer_characteristics (customer_id, characteristic_id)
                VALUES (?, ?)
            ''', (customer_id, char_id))

        conn.commit()


# =============================================================================
# TAGS
# =============================================================================

def get_customer_tags(customer_id: int) -> list:
    """
    Get customer tags.

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


def set_customer_tags(customer_id: int, tag_ids: list) -> None:
    """
    Set customer tags (replaces existing).

    Args:
        customer_id: Customer ID
        tag_ids: List of tag IDs to assign
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Remove existing tags
        cursor.execute('DELETE FROM beach_customer_tags WHERE customer_id = ?', (customer_id,))

        # Add new tags
        for tag_id in tag_ids:
            cursor.execute('''
                INSERT INTO beach_customer_tags (customer_id, tag_id)
                VALUES (?, ?)
            ''', (customer_id, tag_id))

        conn.commit()
