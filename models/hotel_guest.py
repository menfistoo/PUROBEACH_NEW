"""
Hotel guest model and data access functions.
Handles hotel guest CRUD operations and Excel import functionality.
"""

from database import get_db
from datetime import date
from typing import Optional, List, Dict, Any
import unicodedata


def normalize_guest_name(name: str) -> str:
    """Normalize a guest name for robust matching across PMS exports.

    Lowercases, trims, collapses whitespace, strips accents, and converts
    "Last, First" to "first last". Conservative (no fuzzy/substring matching),
    so it only unifies the same name written differently — e.g.
    "José García", "JOSE GARCIA", "GARCIA, JOSE" all normalize equal.
    """
    if not name:
        return ''
    s = str(name).strip().lower()
    if ',' in s:
        parts = [p.strip() for p in s.split(',', 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            s = f"{parts[1]} {parts[0]}"
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


def get_all_hotel_guests(
    active_only: bool = True,
    search: str = None,
    room_filter: str = None,
    date_filter: date = None
) -> List[Dict[str, Any]]:
    """
    Get all hotel guests with optional filtering.

    Args:
        active_only: If True, only return guests with departure >= today
        search: Search term for name
        room_filter: Filter by room number
        date_filter: Filter guests staying on this date

    Returns:
        List of hotel guest dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM hotel_guests WHERE 1=1'
        params = []

        if active_only:
            query += ' AND departure_date >= date("now")'

        if search:
            query += ' AND (guest_name LIKE ? OR room_number LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])

        if room_filter:
            query += ' AND room_number = ?'
            params.append(room_filter)

        if date_filter:
            query += ' AND arrival_date <= ? AND departure_date >= ?'
            params.extend([date_filter.isoformat(), date_filter.isoformat()])

        query += ' ORDER BY room_number, arrival_date DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_hotel_guest_by_id(guest_id: int) -> Optional[Dict[str, Any]]:
    """
    Get hotel guest by ID.

    Args:
        guest_id: Hotel guest ID

    Returns:
        Hotel guest dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM hotel_guests WHERE id = ?', (guest_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_guests_by_room(room_number: str, check_date: date = None,
                       main_per_booking: bool = False) -> List[Dict[str, Any]]:
    """
    Get hotel guests by room number.

    Args:
        room_number: Room number to search
        check_date: Optional date to filter active guests (adds checkin/checkout flags)
        main_per_booking: If True, return only the main guest (is_main_guest=1)
            for each booking_reference. Each booking appears as one entry,
            representing its principal guest.

    Returns:
        List of hotel guest dicts. When main_per_booking=True, one entry per
        booking sorted by: check-in today first, then check-out today last.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if check_date:
            cursor.execute('''
                SELECT * FROM hotel_guests
                WHERE room_number = ?
                  AND arrival_date <= ?
                  AND departure_date >= ?
                ORDER BY arrival_date DESC, is_main_guest DESC, id DESC
            ''', (room_number, check_date.isoformat(), check_date.isoformat()))
        else:
            cursor.execute('''
                SELECT * FROM hotel_guests
                WHERE room_number = ?
                ORDER BY arrival_date DESC, is_main_guest DESC, id DESC
            ''', (room_number,))

        rows = cursor.fetchall()

        seen_names = set()
        seen_bookings = set()
        unique_guests = []

        for row in rows:
            guest = dict(row)

            # Deduplicate by guest_name (case-insensitive)
            name_key = guest['guest_name'].upper().strip() if guest['guest_name'] else ''
            if not name_key or name_key in seen_names:
                continue
            seen_names.add(name_key)

            # When main_per_booking: 1 main guest per booking_reference
            if main_per_booking:
                booking = guest.get('booking_reference')
                if booking:
                    if booking in seen_bookings:
                        continue
                    seen_bookings.add(booking)
                # Skip non-main guests (they won't represent the booking)
                if not guest.get('is_main_guest', 0):
                    continue

            # Add checkin/checkout flags when filtering by date.
            # NOTE: arrival_date/departure_date come back as date objects (the SQLite
            # connection parses DATE columns), so normalise to ISO strings before
            # comparing — comparing a date to a string is always False (old bug).
            if check_date:
                check_str = check_date.isoformat()
                arr = guest.get('arrival_date')
                dep = guest.get('departure_date')
                arr_str = arr.isoformat() if hasattr(arr, 'isoformat') else (str(arr) if arr else '')
                dep_str = dep.isoformat() if hasattr(dep, 'isoformat') else (str(dep) if dep else '')
                guest['is_checkin_today'] = (arr_str == check_str)
                guest['is_checkout_today'] = (dep_str == check_str)

            unique_guests.append(guest)

        # Changeover day: keep both the incoming and the departing guests (a checkout
        # guest may still use the beach in the morning, so staff must be able to pick
        # either). The sort below puts the incoming/staying guest first and the
        # checkout-today guest last (it carries an is_checkout_today flag for its badge).

        # Sort: check-in first, then in-house, then check-out last
        unique_guests.sort(key=lambda g: (
            not g.get('is_checkin_today', False),
            g.get('is_checkout_today', False),
            -g.get('is_main_guest', 0),
            g.get('guest_name', '')
        ))

        return unique_guests


def get_room_guest_count(room_number: str, check_date: date = None) -> int:
    """
    Get the count of unique guests in a room.

    Uses the same deduplication logic as get_guests_by_room for consistency.

    Args:
        room_number: Room number
        check_date: Optional date to filter active guests

    Returns:
        Number of unique guests in the room
    """
    # Reuse get_guests_by_room for consistent deduplication
    guests = get_guests_by_room(room_number, check_date)
    return len(guests)


def search_guests(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search hotel guests by name or room number for autocomplete.

    Args:
        query: Search query
        limit: Max results to return

    Returns:
        List of matching hotel guest dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        search_term = f'%{query}%'

        cursor.execute('''
            SELECT * FROM hotel_guests
            WHERE (guest_name LIKE ? OR room_number LIKE ?)
              AND departure_date >= date("now")
              AND arrival_date <= date("now")
            ORDER BY room_number, guest_name
            LIMIT ?
        ''', (search_term, search_term, limit))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_hotel_guest(
    room_number: str,
    guest_name: str,
    arrival_date: date,
    departure_date: date,
    num_adults: int = 1,
    num_children: int = 0,
    vip_code: str = None,
    guest_type: str = None,
    nationality: str = None,
    email: str = None,
    phone: str = None,
    notes: str = None,
    source_file: str = None,
    is_main_guest: int = 0,
    booking_reference: str = None
) -> int:
    """
    Create new hotel guest record.

    Args:
        room_number: Room number
        guest_name: Guest full name
        arrival_date: Check-in date
        departure_date: Check-out date
        num_adults: Number of adults
        num_children: Number of children
        vip_code: VIP code if applicable
        guest_type: Guest type (AD, CH, etc.)
        nationality: Guest nationality/country
        email: Email address
        phone: Phone number
        notes: Additional notes
        source_file: Source file name if imported
        is_main_guest: Whether this is the main guest (1) or additional guest (0)
        booking_reference: Hotel PMS reservation number

    Returns:
        New hotel guest ID
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO hotel_guests (
                room_number, guest_name, arrival_date, departure_date,
                num_adults, num_children, vip_code, guest_type,
                nationality, email, phone, notes, source_file, is_main_guest, booking_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            room_number, guest_name,
            arrival_date.isoformat() if isinstance(arrival_date, date) else arrival_date,
            departure_date.isoformat() if isinstance(departure_date, date) else departure_date,
            num_adults, num_children, vip_code, guest_type,
            nationality, email, phone, notes, source_file, is_main_guest, booking_reference
        ))

        conn.commit()
        return cursor.lastrowid


def upsert_hotel_guest(
    room_number: str,
    guest_name: str,
    arrival_date: date,
    departure_date: date,
    booking_reference: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Insert or update hotel guest.

    Matching priority:
    1. If booking_reference provided: match by (booking_reference + guest_name)
    2. Fallback: match by (room_number + arrival_date + guest_name)

    Supports multiple guests per room. First guest in a room is marked as main guest.
    Detects room changes when booking_reference matches but room_number differs.

    Args:
        room_number: Room number
        guest_name: Guest full name
        arrival_date: Check-in date
        departure_date: Check-out date
        booking_reference: Hotel PMS reservation number (preferred for matching)
        **kwargs: Additional fields to update (including is_main_guest)

    Returns:
        Dict with 'id', 'action', 'is_main_guest', 'room_changed', 'old_room', 'new_room'
    """
    with get_db() as conn:
        cursor = conn.cursor()

        arrival_str = arrival_date.isoformat() if isinstance(arrival_date, date) else arrival_date
        departure_str = departure_date.isoformat() if isinstance(departure_date, date) else departure_date

        existing = None
        room_changed = False
        old_room = None

        # Priority 1: Match by booking_reference + guest_name (if booking_reference provided).
        # Compare names NORMALIZED so spelling/accents/"Last, First" differences between
        # exports don't create duplicate guests or miss a room change.
        if booking_reference:
            cursor.execute('''
                SELECT id, room_number, is_main_guest, guest_name FROM hotel_guests
                WHERE booking_reference = ?
            ''', (booking_reference,))
            target_name = normalize_guest_name(guest_name)
            for cand in cursor.fetchall():
                if normalize_guest_name(cand['guest_name']) == target_name:
                    existing = cand
                    break

            if existing and existing['room_number'] != room_number:
                room_changed = True
                old_room = existing['room_number']

        # Priority 2: Fallback to room + date + name matching
        if not existing:
            cursor.execute('''
                SELECT id, room_number, is_main_guest FROM hotel_guests
                WHERE room_number = ? AND arrival_date = ? AND guest_name = ?
            ''', (room_number, arrival_str, guest_name))
            existing = cursor.fetchone()

        if existing:
            # Update existing record
            guest_id = existing['id']
            is_main = existing['is_main_guest']
            update_fields = ['departure_date = ?', 'updated_at = CURRENT_TIMESTAMP']
            update_values = [departure_str]

            # Update room_number if changed
            if room_changed:
                update_fields.append('room_number = ?')
                update_values.append(room_number)

            # Update booking_reference if provided and not already set
            if booking_reference:
                update_fields.append('booking_reference = ?')
                update_values.append(booking_reference)

            for field, value in kwargs.items():
                if value is not None and field != 'is_main_guest':
                    update_fields.append(f'{field} = ?')
                    update_values.append(value)

            update_values.append(guest_id)

            cursor.execute(f'''
                UPDATE hotel_guests
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', update_values)

            conn.commit()
            return {
                'id': guest_id,
                'action': 'updated',
                'is_main_guest': is_main,
                'room_changed': room_changed,
                'old_room': old_room,
                'new_room': room_number if room_changed else None
            }
        else:
            # Check if this is the first guest for this room+date
            cursor.execute('''
                SELECT COUNT(*) as count FROM hotel_guests
                WHERE room_number = ? AND arrival_date = ?
            ''', (room_number, arrival_str))
            existing_count = cursor.fetchone()['count']

            # First guest becomes main guest, others are additional
            is_main_guest = 1 if existing_count == 0 else kwargs.get('is_main_guest', 0)

            # Create new record
            guest_id = create_hotel_guest(
                room_number=room_number,
                guest_name=guest_name,
                arrival_date=arrival_date,
                departure_date=departure_date,
                is_main_guest=is_main_guest,
                booking_reference=booking_reference,
                **{k: v for k, v in kwargs.items() if k != 'is_main_guest'}
            )
            return {
                'id': guest_id,
                'action': 'created',
                'is_main_guest': is_main_guest,
                'room_changed': False,
                'old_room': None,
                'new_room': None
            }


def propagate_room_change(
    guest_name: str,
    old_room: str,
    new_room: str
) -> Dict[str, Any]:
    """
    Propagate room change to beach_customers and future reservations.

    When a hotel guest changes rooms, this function updates:
    1. The beach_customer record (interno with matching name and old room)
    2. Current and future reservations (end_date >= today)

    Past reservations are left unchanged for historical accuracy.

    Args:
        guest_name: Guest full name to match
        old_room: Previous room number
        new_room: New room number

    Returns:
        Dict with 'customer_updated', 'customer_id', 'reservations_updated'
    """
    with get_db() as conn:
        cursor = conn.cursor()

        result = {
            'customer_updated': False,
            'customer_id': None,
            'reservations_updated': 0
        }

        # Find the beach_customer (interno with old room + name match)
        # Use flexible name matching (guest_name could be "First Last" or "Last, First")
        cursor.execute('''
            SELECT id, first_name, last_name FROM beach_customers
            WHERE customer_type = 'interno'
              AND room_number = ?
        ''', (old_room,))

        customers = cursor.fetchall()

        # Find best match by name
        matched_customer = None
        guest_name_normalized = guest_name.lower().strip()

        for customer in customers:
            first = (customer['first_name'] or '').lower().strip()
            last = (customer['last_name'] or '').lower().strip()
            full_name = f"{first} {last}".strip()
            full_name_reversed = f"{last} {first}".strip()

            # Check if guest_name matches any combination
            if (guest_name_normalized == full_name or
                guest_name_normalized == full_name_reversed or
                guest_name_normalized in full_name or
                full_name in guest_name_normalized):
                matched_customer = customer
                break

        if not matched_customer:
            return result

        customer_id = matched_customer['id']
        result['customer_id'] = customer_id

        # Update customer's room_number
        cursor.execute('''
            UPDATE beach_customers
            SET room_number = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_room, customer_id))

        result['customer_updated'] = cursor.rowcount > 0

        # Update current and future reservations (end_date >= today)
        # Using end_date ensures active multi-day reservations (started before today
        # but ending today or later) are also updated, and avoids timezone edge cases
        # when comparing start_date across UTC/local timezone boundaries.
        from utils.datetime_helpers import get_today
        today = get_today().isoformat()
        cursor.execute('''
            UPDATE beach_reservations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE customer_id = ?
              AND end_date >= ?
        ''', (customer_id, today))

        result['reservations_updated'] = cursor.rowcount

        conn.commit()
        return result


def sync_customer_room_by_booking(booking_reference: str, room_number: str) -> Dict[str, Any]:
    """
    Keep interno beach_customers' room in sync with the hotel guest list, matched on
    the STABLE booking_reference (hotel reservation number).

    This is the robust replacement for propagate_room_change(): because the public
    reservation number never changes when the physical room changes (or when a room is
    first assigned to a pre-arrival booking), matching on it reliably updates the room
    for the right customer — and the room then flows to every reservation/display that
    joins beach_customers.room_number.

    Returns {'updated': n, 'changes': [{'customer_id', 'old_room', 'new_room'}, ...]}.

    Scope: only customers that have a CURRENT/FUTURE reservation anchored to this exact
    booking_reference. We deliberately do NOT match on beach_customers.booking_reference
    alone, because a room can be reused by many guests over time and that column can be
    ambiguous; the reservation's booking_reference (set accurately at creation) is the
    trustworthy anchor, and past reservations are left untouched.
    """
    result = {'updated': 0, 'changes': []}
    if not booking_reference or not room_number:
        return result

    from utils.datetime_helpers import get_today
    today = get_today().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        # Customers tied to an active reservation for this booking, whose room is stale.
        cursor.execute('''
            SELECT DISTINCT c.id, c.room_number
            FROM beach_customers c
            JOIN beach_reservations r ON r.customer_id = c.id
            WHERE c.customer_type = 'interno'
              AND r.booking_reference = ?
              AND r.end_date >= ?
              AND (c.room_number IS NULL OR c.room_number = '' OR c.room_number != ?)
        ''', (booking_reference, today, room_number))
        stale = cursor.fetchall()
        if not stale:
            return result

        ids = [r['id'] for r in stale]
        placeholders = ','.join('?' for _ in ids)
        cursor.execute(f'''
            UPDATE beach_customers
            SET room_number = ?, booking_reference = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', (room_number, booking_reference, *ids))
        conn.commit()

        result['updated'] = len(stale)
        result['changes'] = [
            {'customer_id': r['id'], 'old_room': r['room_number'], 'new_room': room_number}
            for r in stale
        ]
        return result


def set_booking_preferences(booking_reference: str, preferences: str) -> int:
    """Store the PMS preference text on all guests of a booking. Returns rows updated."""
    if not booking_reference or not preferences:
        return 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE hotel_guests SET preferences = ?, updated_at = CURRENT_TIMESTAMP
            WHERE booking_reference = ?
        ''', (preferences, booking_reference))
        conn.commit()
        return cursor.rowcount


def set_guest_preferences(guest_id: int, preferences: str) -> bool:
    """Store preference text on a single guest (fallback when there's no booking ref)."""
    if not guest_id or not preferences:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE hotel_guests SET preferences = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (preferences, guest_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_hotel_guest(guest_id: int) -> bool:
    """
    Delete hotel guest record.

    Args:
        guest_id: Hotel guest ID to delete

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM hotel_guests WHERE id = ?', (guest_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_guests_by_source(source_file: str) -> int:
    """
    Delete all guests imported from a specific source file.

    Args:
        source_file: Source file name

    Returns:
        Number of records deleted
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM hotel_guests WHERE source_file = ?', (source_file,))
        conn.commit()
        return cursor.rowcount


def get_guest_count() -> Dict[str, int]:
    """
    Get guest statistics.

    Returns:
        Dict with 'total', 'active', 'arriving_today', 'departing_today'
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM hotel_guests')
        total = cursor.fetchone()['count']

        cursor.execute('''
            SELECT COUNT(*) as count FROM hotel_guests
            WHERE departure_date >= date("now")
        ''')
        active = cursor.fetchone()['count']

        cursor.execute('''
            SELECT COUNT(*) as count FROM hotel_guests
            WHERE arrival_date = date("now")
        ''')
        arriving = cursor.fetchone()['count']

        cursor.execute('''
            SELECT COUNT(*) as count FROM hotel_guests
            WHERE departure_date = date("now")
        ''')
        departing = cursor.fetchone()['count']

        return {
            'total': total,
            'active': active,
            'arriving_today': arriving,
            'departing_today': departing
        }


def get_distinct_rooms() -> List[str]:
    """
    Get list of distinct room numbers with active guests.

    Returns:
        List of room numbers
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT room_number FROM hotel_guests
            WHERE departure_date >= date("now")
            ORDER BY CAST(room_number AS INTEGER), room_number
        ''')
        return [row['room_number'] for row in cursor.fetchall()]
