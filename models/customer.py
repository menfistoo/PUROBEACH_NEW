"""
Beach customer data access functions.
Handles customer CRUD operations, preferences, and tags.
"""

from database import get_db
from datetime import datetime


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


def create_customer(customer_type: str, first_name: str, last_name: str = None, **kwargs) -> int:
    """
    Create new customer.

    Args:
        customer_type: 'interno' or 'externo'
        first_name: First name (required)
        last_name: Last name
        **kwargs: Optional fields (email, phone, room_number, notes, vip_status)

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
        (customer_type, first_name, last_name, email, phone, room_number, notes, vip_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_type, first_name, last_name,
          kwargs.get('email'), kwargs.get('phone'), kwargs.get('room_number'),
          kwargs.get('notes'), kwargs.get('vip_status', 0)))

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
                      'notes', 'vip_status', 'total_visits', 'total_spent', 'last_visit']
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


def get_customers_filtered(
    search: str = None,
    customer_type: str = None,
    vip_only: bool = False,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """
    Get customers with advanced filtering and pagination.

    Args:
        search: Search term for name, phone, email, room
        customer_type: Filter by type ('interno'/'externo')
        vip_only: Only return VIP customers
        limit: Max results to return
        offset: Results offset for pagination

    Returns:
        Dict with 'customers' list and 'total' count
    """
    db = get_db()
    cursor = db.cursor()

    base_query = '''
        SELECT c.*,
               (SELECT COUNT(*) FROM beach_reservations WHERE customer_id = c.id) as reservation_count
        FROM beach_customers c
        WHERE 1=1
    '''
    count_query = 'SELECT COUNT(*) as total FROM beach_customers c WHERE 1=1'
    params = []
    count_params = []

    if search:
        search_clause = ''' AND (
            c.first_name LIKE ? OR c.last_name LIKE ? OR
            c.email LIKE ? OR c.phone LIKE ? OR c.room_number LIKE ?
        )'''
        base_query += search_clause
        count_query += search_clause
        search_term = f'%{search}%'
        params.extend([search_term] * 5)
        count_params.extend([search_term] * 5)

    if customer_type:
        base_query += ' AND c.customer_type = ?'
        count_query += ' AND c.customer_type = ?'
        params.append(customer_type)
        count_params.append(customer_type)

    if vip_only:
        base_query += ' AND c.vip_status = 1'
        count_query += ' AND c.vip_status = 1'

    # Get total count
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()['total']

    # Get paginated results
    base_query += ' ORDER BY c.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(base_query, params)
    rows = cursor.fetchall()

    return {
        'customers': [dict(row) for row in rows],
        'total': total
    }


def get_customer_with_details(customer_id: int) -> dict:
    """
    Get customer with full details including preferences, tags, and reservation history.

    Args:
        customer_id: Customer ID

    Returns:
        Customer dict with preferences, tags, and reservations or None
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return None

    db = get_db()
    cursor = db.cursor()

    # Get preferences
    customer['preferences'] = get_customer_preferences(customer_id)

    # Get tags
    customer['tags'] = get_customer_tags(customer_id)

    # Get recent reservations
    cursor.execute('''
        SELECT r.*, rs.name as state_name, rs.color as state_color
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.customer_id = ?
        ORDER BY r.start_date DESC
        LIMIT 10
    ''', (customer_id,))
    customer['recent_reservations'] = [dict(row) for row in cursor.fetchall()]

    # Get reservation stats
    cursor.execute('''
        SELECT
            COUNT(*) as total_reservations,
            SUM(CASE WHEN end_date >= date('now') THEN 1 ELSE 0 END) as active_reservations
        FROM beach_reservations
        WHERE customer_id = ?
    ''', (customer_id,))
    stats = cursor.fetchone()
    customer['total_reservations'] = stats['total_reservations'] or 0
    customer['active_reservations'] = stats['active_reservations'] or 0

    return customer


def get_customer_stats() -> dict:
    """
    Get customer statistics for dashboard.

    Returns:
        Dict with customer counts by type and VIP status
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN customer_type = 'interno' THEN 1 ELSE 0 END) as interno_count,
            SUM(CASE WHEN customer_type = 'externo' THEN 1 ELSE 0 END) as externo_count,
            SUM(CASE WHEN vip_status = 1 THEN 1 ELSE 0 END) as vip_count
        FROM beach_customers
    ''')
    row = cursor.fetchone()

    return {
        'total': row['total'] or 0,
        'interno': row['interno_count'] or 0,
        'externo': row['externo_count'] or 0,
        'vip': row['vip_count'] or 0
    }


def merge_customers(source_id: int, target_id: int) -> bool:
    """
    Merge source customer into target customer.
    Transfers all reservations, tags, and preferences to target.
    Then deletes the source customer.

    Args:
        source_id: Customer ID to merge from (will be deleted)
        target_id: Customer ID to merge into (will remain)

    Returns:
        True if merged successfully

    Raises:
        ValueError if source or target not found
    """
    db = get_db()
    cursor = db.cursor()

    # Validate both customers exist
    source = get_customer_by_id(source_id)
    target = get_customer_by_id(target_id)

    if not source:
        raise ValueError('Cliente origen no encontrado')
    if not target:
        raise ValueError('Cliente destino no encontrado')
    if source_id == target_id:
        raise ValueError('No se puede fusionar un cliente consigo mismo')

    try:
        db.execute('BEGIN IMMEDIATE')

        # Transfer reservations
        cursor.execute('''
            UPDATE beach_reservations
            SET customer_id = ?
            WHERE customer_id = ?
        ''', (target_id, source_id))

        # Transfer preferences (ignore duplicates)
        cursor.execute('''
            INSERT OR IGNORE INTO beach_customer_preferences (customer_id, preference_id)
            SELECT ?, preference_id FROM beach_customer_preferences WHERE customer_id = ?
        ''', (target_id, source_id))

        # Transfer tags (ignore duplicates)
        cursor.execute('''
            INSERT OR IGNORE INTO beach_customer_tags (customer_id, tag_id)
            SELECT ?, tag_id FROM beach_customer_tags WHERE customer_id = ?
        ''', (target_id, source_id))

        # Update target stats
        cursor.execute('''
            UPDATE beach_customers
            SET total_visits = total_visits + ?,
                total_spent = total_spent + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (source['total_visits'], source['total_spent'], target_id))

        # Delete source customer preferences and tags
        cursor.execute('DELETE FROM beach_customer_preferences WHERE customer_id = ?', (source_id,))
        cursor.execute('DELETE FROM beach_customer_tags WHERE customer_id = ?', (source_id,))

        # Delete source customer
        cursor.execute('DELETE FROM beach_customers WHERE id = ?', (source_id,))

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise e


def find_potential_duplicates_for_customer(customer_id: int) -> list:
    """
    Find potential duplicate customers for a given customer.
    Matches by phone, email, or name similarity.

    Args:
        customer_id: Customer ID to find duplicates for

    Returns:
        List of potential duplicate customer dicts
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return []

    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT c.*,
               (SELECT COUNT(*) FROM beach_reservations WHERE customer_id = c.id) as reservation_count
        FROM beach_customers c
        WHERE c.id != ?
          AND (
    '''
    params = [customer_id]
    conditions = []

    if customer.get('phone'):
        conditions.append('c.phone = ?')
        params.append(customer['phone'])

    if customer.get('email'):
        conditions.append('c.email = ?')
        params.append(customer['email'])

    if customer.get('first_name') and customer.get('last_name'):
        conditions.append('(LOWER(c.first_name) = LOWER(?) AND LOWER(c.last_name) = LOWER(?))')
        params.extend([customer['first_name'], customer['last_name']])

    if not conditions:
        return []

    query += ' OR '.join(conditions) + ')'
    query += ' ORDER BY c.created_at DESC LIMIT 20'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def search_customers_unified(query: str, customer_type: str = None, limit: int = 20) -> list:
    """
    Search customers from both beach_customers and hotel_guests tables.

    Args:
        query: Search query string (name, phone, room number)
        customer_type: Filter by type ('interno'/'externo'), None for all
        limit: Maximum results to return

    Returns:
        List of dicts with 'source' field indicating origin:
        - source='customer': from beach_customers table
        - source='hotel_guest': from hotel_guests table
    """
    db = get_db()
    cursor = db.cursor()
    results = []
    search_term = f'%{query}%'

    # Search beach_customers
    customer_query = '''
        SELECT c.*, 'customer' as source
        FROM beach_customers c
        WHERE (c.first_name LIKE ? OR c.last_name LIKE ? OR
               c.email LIKE ? OR c.phone LIKE ? OR c.room_number LIKE ?)
    '''
    params = [search_term] * 5

    if customer_type:
        customer_query += ' AND c.customer_type = ?'
        params.append(customer_type)

    customer_query += ' ORDER BY c.created_at DESC LIMIT ?'
    params.append(limit)

    cursor.execute(customer_query, params)
    for row in cursor.fetchall():
        customer = dict(row)
        customer['display_name'] = f"{customer['first_name']} {customer['last_name'] or ''}".strip()
        results.append(customer)

    # Search hotel_guests (only if customer_type is not 'externo')
    if customer_type != 'externo':
        guest_query = '''
            SELECT h.*, 'hotel_guest' as source
            FROM hotel_guests h
            WHERE (h.guest_name LIKE ? OR h.room_number LIKE ? OR
                   h.email LIKE ? OR h.phone LIKE ?)
              AND h.departure_date >= date('now')
            ORDER BY h.room_number, h.guest_name
            LIMIT ?
        '''
        cursor.execute(guest_query, [search_term, search_term, search_term, search_term, limit])

        # Get existing customer room numbers to avoid duplicates
        existing_rooms = {c['room_number'] for c in results if c.get('room_number') and c.get('customer_type') == 'interno'}

        for row in cursor.fetchall():
            guest = dict(row)
            # Skip if already have a customer with this room number
            if guest['room_number'] in existing_rooms:
                continue
            guest['display_name'] = guest['guest_name']
            guest['customer_type'] = 'interno'  # Hotel guests are always interno
            results.append(guest)

    return results[:limit]


def create_customer_from_hotel_guest(hotel_guest_id: int) -> dict:
    """
    Create a beach_customer from a hotel_guest record.
    Parses guest_name into first_name/last_name and copies relevant fields.

    Args:
        hotel_guest_id: ID of the hotel guest to convert

    Returns:
        Dict with 'customer_id' and 'customer' data

    Raises:
        ValueError if hotel guest not found or customer already exists for room
    """
    db = get_db()
    cursor = db.cursor()

    # Get hotel guest
    cursor.execute('SELECT * FROM hotel_guests WHERE id = ?', (hotel_guest_id,))
    guest = cursor.fetchone()

    if not guest:
        raise ValueError('Huésped no encontrado')

    guest = dict(guest)

    # Check if customer already exists for this room
    cursor.execute('''
        SELECT id FROM beach_customers
        WHERE customer_type = 'interno' AND room_number = ?
    ''', (guest['room_number'],))
    existing = cursor.fetchone()

    if existing:
        # Return existing customer instead of creating duplicate
        return {
            'customer_id': existing['id'],
            'customer': get_customer_by_id(existing['id']),
            'action': 'existing'
        }

    # Parse guest_name into first_name and last_name
    name_parts = guest['guest_name'].strip().split(' ', 1) if guest['guest_name'] else ['', '']
    first_name = name_parts[0] if name_parts else ''
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    # Determine VIP status from vip_code
    vip_status = 1 if guest.get('vip_code') else 0

    # Create beach_customer
    cursor.execute('''
        INSERT INTO beach_customers
        (customer_type, first_name, last_name, email, phone, room_number, notes, vip_status)
        VALUES ('interno', ?, ?, ?, ?, ?, ?, ?)
    ''', (
        first_name, last_name,
        guest.get('email'), guest.get('phone'),
        guest['room_number'],
        f"Importado de huésped hotel (llegada: {guest.get('arrival_date')}, salida: {guest.get('departure_date')})",
        vip_status
    ))

    db.commit()
    customer_id = cursor.lastrowid

    return {
        'customer_id': customer_id,
        'customer': get_customer_by_id(customer_id),
        'action': 'created'
    }
