"""
Customer search and integration functions.
Handles unified search, hotel guest integration, and customer merging.
"""

import unicodedata
from database import get_db
from .customer_crud import get_customer_by_id, set_customer_preferences


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for accent-insensitive search.
    Removes accents and converts to lowercase.

    Examples:
        'García' -> 'garcia'
        'José María' -> 'jose maria'
    """
    if not text:
        return ''
    # Decompose unicode characters (é -> e + combining accent)
    normalized = unicodedata.normalize('NFD', text)
    # Remove combining diacritical marks (accents)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents.lower()


# =============================================================================
# UNIFIED SEARCH
# =============================================================================

def _matches_search(record: dict, search_words: list, fields: list) -> bool:
    """
    Check if a record matches all search words in any of the specified fields.
    Uses accent-insensitive matching.
    """
    # Build searchable text from all fields
    searchable_parts = []
    for field in fields:
        value = record.get(field)
        if value:
            searchable_parts.append(normalize_text(str(value)))

    searchable_text = ' '.join(searchable_parts)

    # All words must match somewhere
    return all(word in searchable_text for word in search_words)


def search_customers_unified(query: str, customer_type: str = None, limit: int = 20) -> list:
    """
    Search customers from both beach_customers and hotel_guests tables.
    Supports accent-insensitive and multi-word search.

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

    # Normalize the query for accent-insensitive search
    normalized_query = normalize_text(query)
    search_words = normalized_query.split()

    if not search_words:
        return []

    # Build SQL LIKE patterns for pre-filtering (improves performance)
    like_patterns = [f'%{word}%' for word in search_words]

    # Search beach_customers with SQL pre-filtering
    customer_query = '''
        SELECT c.*, 'customer' as source
        FROM beach_customers c
        WHERE 1=1
    '''
    params = []

    # Add SQL-level filtering for each word
    for pattern in like_patterns:
        customer_query += '''
            AND (LOWER(c.first_name || ' ' || COALESCE(c.last_name, '')) LIKE ?
                 OR LOWER(c.email) LIKE ?
                 OR c.phone LIKE ?
                 OR c.room_number LIKE ?)
        '''
        params.extend([pattern, pattern, pattern, pattern])

    if customer_type:
        customer_query += ' AND c.customer_type = ?'
        params.append(customer_type)

    customer_query += ' ORDER BY c.total_visits DESC, c.created_at DESC LIMIT ?'
    params.append(limit * 5)

    cursor.execute(customer_query, params)

    customer_fields = ['first_name', 'last_name', 'email', 'phone', 'room_number']
    for row in cursor.fetchall():
        customer = dict(row)
        # Python-side filtering for accent-insensitive matching
        if _matches_search(customer, search_words, customer_fields):
            customer['display_name'] = f"{customer['first_name']} {customer['last_name'] or ''}".strip()
            results.append(customer)
            if len(results) >= limit:
                break

    # Search hotel_guests (only if customer_type is not 'externo')
    if customer_type != 'externo' and len(results) < limit:
        guest_query = '''
            SELECT h.*,
                   'hotel_guest' as source,
                   (SELECT COUNT(*) FROM hotel_guests h2
                    WHERE h2.room_number = h.room_number
                      AND h2.arrival_date = h.arrival_date
                      AND h2.departure_date >= date('now')) as room_guest_count
            FROM hotel_guests h
            WHERE h.departure_date >= date('now')
              AND h.arrival_date <= date('now')
        '''
        guest_params = []

        # Add SQL-level filtering for each word
        for pattern in like_patterns:
            guest_query += '''
                AND (LOWER(h.guest_name) LIKE ?
                     OR h.room_number LIKE ?
                     OR LOWER(h.email) LIKE ?
                     OR h.phone LIKE ?)
            '''
            guest_params.extend([pattern, pattern, pattern, pattern])

        guest_query += '''
            ORDER BY h.room_number, h.is_main_guest DESC, h.guest_name
            LIMIT ?
        '''
        guest_params.append(limit * 5)

        cursor.execute(guest_query, guest_params)

        # Get existing customer room numbers to avoid duplicates
        existing_rooms = {c['room_number'] for c in results if c.get('room_number') and c.get('customer_type') == 'interno'}
        # Track rooms we've already added from hotel_guests (show only main guest per room)
        added_rooms = set()

        guest_fields = ['guest_name', 'room_number', 'email', 'phone']
        for row in cursor.fetchall():
            guest = dict(row)
            room = guest['room_number']
            # Skip if already have a customer with this room number
            if room in existing_rooms:
                continue
            # Skip if we already added a guest from this room (show only main guest)
            if room in added_rooms:
                continue
            # Python-side filtering for accent-insensitive matching
            if _matches_search(guest, search_words, guest_fields):
                guest_count = guest.get('room_guest_count', 1)
                guest['display_name'] = guest['guest_name'] + (f" ({guest_count} huéspedes)" if guest_count > 1 else "")
                guest['customer_type'] = 'interno'  # Hotel guests are always interno
                # Check-in/Check-out today flags (compare date objects or strings)
                from datetime import date
                today = date.today()
                arrival = guest.get('arrival_date')
                departure = guest.get('departure_date')
                # Handle both date objects and strings
                if isinstance(arrival, str):
                    guest['is_checkin_today'] = arrival == today.isoformat()
                else:
                    guest['is_checkin_today'] = arrival == today
                if isinstance(departure, str):
                    guest['is_checkout_today'] = departure == today.isoformat()
                else:
                    guest['is_checkout_today'] = departure == today
                results.append(guest)
                added_rooms.add(room)
                if len(results) >= limit:
                    break

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
