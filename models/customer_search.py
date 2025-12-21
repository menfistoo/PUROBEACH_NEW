"""
Customer search and integration functions.
Handles unified search, hotel guest integration, and customer merging.
"""

from database import get_db
from .customer_crud import get_customer_by_id, set_customer_preferences


# =============================================================================
# UNIFIED SEARCH
# =============================================================================

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
            SELECT h.*,
                   'hotel_guest' as source,
                   (SELECT COUNT(*) FROM hotel_guests h2
                    WHERE h2.room_number = h.room_number
                      AND h2.arrival_date = h.arrival_date
                      AND h2.departure_date >= date('now')) as room_guest_count
            FROM hotel_guests h
            WHERE (h.guest_name LIKE ? OR h.room_number LIKE ? OR
                   h.email LIKE ? OR h.phone LIKE ?)
              AND h.departure_date >= date('now')
            ORDER BY h.room_number, h.is_main_guest DESC, h.guest_name
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


# =============================================================================
# HOTEL GUEST INTEGRATION
# =============================================================================

def create_customer_from_hotel_guest(hotel_guest_id: int, additional_data: dict = None) -> dict:
    """
    Create a beach_customer from a hotel_guest record.
    Parses guest_name into first_name/last_name and copies relevant fields.

    Args:
        hotel_guest_id: ID of the hotel guest to convert
        additional_data: Optional dict with additional fields (phone, email, language, notes, preferences)

    Returns:
        Dict with 'customer_id' and 'customer' data

    Raises:
        ValueError if hotel guest not found or customer already exists for room
    """
    db = get_db()
    cursor = db.cursor()
    additional_data = additional_data or {}

    # Get hotel guest
    cursor.execute('SELECT * FROM hotel_guests WHERE id = ?', (hotel_guest_id,))
    guest = cursor.fetchone()

    if not guest:
        raise ValueError('Huesped no encontrado')

    guest = dict(guest)

    # Check if customer already exists for this room with this name
    cursor.execute('''
        SELECT id FROM beach_customers
        WHERE customer_type = 'interno' AND room_number = ?
          AND (first_name || ' ' || COALESCE(last_name, '')) LIKE ?
    ''', (guest['room_number'], f"%{guest['guest_name']}%"))
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

    # Map nationality to language
    nationality_to_language = {
        'DE': 'DE', 'AT': 'DE', 'CH': 'DE',
        'GB': 'EN', 'US': 'EN', 'AU': 'EN', 'UK': 'EN', 'IE': 'EN',
        'ES': 'ES', 'MX': 'ES', 'AR': 'ES', 'CO': 'ES',
        'FR': 'FR', 'BE': 'FR',
        'IT': 'IT',
        'PT': 'PT', 'BR': 'PT',
        'NL': 'NL',
        'RU': 'RU',
    }
    nationality = guest.get('nationality', '').upper().strip() if guest.get('nationality') else None
    language = additional_data.get('language') or nationality_to_language.get(nationality)

    # Use additional data if provided, otherwise use hotel guest data
    email = additional_data.get('email') or guest.get('email')
    phone = additional_data.get('phone') or guest.get('phone')
    country_code = additional_data.get('country_code', '+34')
    notes = additional_data.get('notes') or f"Huesped hotel (llegada: {guest.get('arrival_date')}, salida: {guest.get('departure_date')})"

    # Create beach_customer
    cursor.execute('''
        INSERT INTO beach_customers
        (customer_type, first_name, last_name, email, phone, room_number, notes, vip_status, language, country_code)
        VALUES ('interno', ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        first_name, last_name,
        email, phone,
        guest['room_number'],
        notes,
        vip_status,
        language,
        country_code
    ))

    db.commit()
    customer_id = cursor.lastrowid

    # Set preferences if provided
    if additional_data.get('preferences'):
        set_customer_preferences(customer_id, additional_data['preferences'])

    return {
        'customer_id': customer_id,
        'customer': get_customer_by_id(customer_id),
        'action': 'created'
    }


# =============================================================================
# CUSTOMER MERGE
# =============================================================================

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
