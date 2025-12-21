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
    db = get_db()
    cursor = db.cursor()

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
    db = get_db()
    cursor = db.cursor()
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
    db = get_db()
    cursor = db.cursor()

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

    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        INSERT INTO beach_customers
        (customer_type, first_name, last_name, email, phone, room_number, notes, vip_status, language, country_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_type, first_name, last_name,
          kwargs.get('email'), kwargs.get('phone'), kwargs.get('room_number'),
          kwargs.get('notes'), kwargs.get('vip_status', 0),
          kwargs.get('language'), kwargs.get('country_code', '+34')))

    db.commit()
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
    db = get_db()

    allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'room_number',
                      'notes', 'vip_status', 'total_visits', 'total_spent', 'last_visit',
                      'language', 'country_code']
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

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_customer(customer_id: int) -> bool:
    """
    Delete customer (hard delete).
    Only allowed if no active reservations.

    Args:
        customer_id: Customer ID to delete

    Returns:
        True if deleted successfully

    Raises:
        ValueError if customer has active reservations
    """
    db = get_db()
    cursor = db.cursor()

    # Check for active reservations
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_reservations
        WHERE customer_id = ?
          AND end_date >= date('now')
    ''', (customer_id,))

    if cursor.fetchone()['count'] > 0:
        raise ValueError('No se puede eliminar cliente con reservas activas')

    cursor.execute('DELETE FROM beach_customers WHERE id = ?', (customer_id,))
    db.commit()

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
    db = get_db()
    cursor = db.cursor()

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
# PREFERENCES
# =============================================================================

def get_customer_preferences(customer_id: int) -> list:
    """
    Get customer preferences.

    Args:
        customer_id: Customer ID

    Returns:
        List of preference dicts
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.*
        FROM beach_preferences p
        JOIN beach_customer_preferences cp ON p.id = cp.preference_id
        WHERE cp.customer_id = ?
        ORDER BY p.name
    ''', (customer_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def set_customer_preferences(customer_id: int, preference_ids: list) -> None:
    """
    Set customer preferences (replaces existing).

    Args:
        customer_id: Customer ID
        preference_ids: List of preference IDs to assign
    """
    db = get_db()
    cursor = db.cursor()

    # Remove existing preferences
    cursor.execute('DELETE FROM beach_customer_preferences WHERE customer_id = ?', (customer_id,))

    # Add new preferences
    for pref_id in preference_ids:
        cursor.execute('''
            INSERT INTO beach_customer_preferences (customer_id, preference_id)
            VALUES (?, ?)
        ''', (customer_id, pref_id))

    db.commit()


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
    db = get_db()
    cursor = db.cursor()
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
    db = get_db()
    cursor = db.cursor()

    # Remove existing tags
    cursor.execute('DELETE FROM beach_customer_tags WHERE customer_id = ?', (customer_id,))

    # Add new tags
    for tag_id in tag_ids:
        cursor.execute('''
            INSERT INTO beach_customer_tags (customer_id, tag_id)
            VALUES (?, ?)
        ''', (customer_id, tag_id))

    db.commit()
