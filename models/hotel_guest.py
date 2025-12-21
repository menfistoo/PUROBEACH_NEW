"""
Hotel guest model and data access functions.
Handles hotel guest CRUD operations and Excel import functionality.
"""

from database import get_db
from datetime import datetime, date
from typing import Optional, List, Dict, Any


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
    db = get_db()
    cursor = db.cursor()

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
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM hotel_guests WHERE id = ?', (guest_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_guests_by_room(room_number: str, check_date: date = None) -> List[Dict[str, Any]]:
    """
    Get hotel guests by room number.

    Args:
        room_number: Room number to search
        check_date: Optional date to filter active guests

    Returns:
        List of hotel guest dicts for the room (main guest first)
    """
    db = get_db()
    cursor = db.cursor()

    if check_date:
        cursor.execute('''
            SELECT * FROM hotel_guests
            WHERE room_number = ?
              AND arrival_date <= ?
              AND departure_date >= ?
            ORDER BY is_main_guest DESC, guest_name
        ''', (room_number, check_date.isoformat(), check_date.isoformat()))
    else:
        cursor.execute('''
            SELECT * FROM hotel_guests
            WHERE room_number = ?
            ORDER BY is_main_guest DESC, guest_name
        ''', (room_number,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_room_guest_count(room_number: str, check_date: date = None) -> int:
    """
    Get the count of guests in a room.

    Args:
        room_number: Room number
        check_date: Optional date to filter active guests

    Returns:
        Number of guests in the room
    """
    db = get_db()
    cursor = db.cursor()

    if check_date:
        cursor.execute('''
            SELECT COUNT(*) as count FROM hotel_guests
            WHERE room_number = ?
              AND arrival_date <= ?
              AND departure_date >= ?
        ''', (room_number, check_date.isoformat(), check_date.isoformat()))
    else:
        cursor.execute('''
            SELECT COUNT(*) as count FROM hotel_guests
            WHERE room_number = ?
        ''', (room_number,))

    return cursor.fetchone()['count']


def search_guests(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search hotel guests by name or room number for autocomplete.

    Args:
        query: Search query
        limit: Max results to return

    Returns:
        List of matching hotel guest dicts
    """
    db = get_db()
    cursor = db.cursor()
    search_term = f'%{query}%'

    cursor.execute('''
        SELECT * FROM hotel_guests
        WHERE (guest_name LIKE ? OR room_number LIKE ?)
          AND departure_date >= date("now")
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
    db = get_db()
    cursor = db.cursor()

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

    db.commit()
    return cursor.lastrowid


def upsert_hotel_guest(
    room_number: str,
    guest_name: str,
    arrival_date: date,
    departure_date: date,
    **kwargs
) -> Dict[str, Any]:
    """
    Insert or update hotel guest based on room_number + arrival_date + guest_name.

    Supports multiple guests per room - uniqueness is by (room, date, name).
    First guest in a room is marked as main guest.

    Args:
        room_number: Room number
        guest_name: Guest full name
        arrival_date: Check-in date
        departure_date: Check-out date
        **kwargs: Additional fields to update (including is_main_guest)

    Returns:
        Dict with 'id', 'action' ('created' or 'updated'), 'is_main_guest'
    """
    db = get_db()
    cursor = db.cursor()

    arrival_str = arrival_date.isoformat() if isinstance(arrival_date, date) else arrival_date
    departure_str = departure_date.isoformat() if isinstance(departure_date, date) else departure_date

    # Check if this exact guest exists (room + date + name)
    cursor.execute('''
        SELECT id, is_main_guest FROM hotel_guests
        WHERE room_number = ? AND arrival_date = ? AND guest_name = ?
    ''', (room_number, arrival_str, guest_name))

    existing = cursor.fetchone()

    if existing:
        # Update existing record
        guest_id = existing['id']
        is_main = existing['is_main_guest']
        update_fields = ['departure_date = ?', 'updated_at = CURRENT_TIMESTAMP']
        update_values = [departure_str]

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

        db.commit()
        return {'id': guest_id, 'action': 'updated', 'is_main_guest': is_main}
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
            **{k: v for k, v in kwargs.items() if k != 'is_main_guest'}
        )
        return {'id': guest_id, 'action': 'created', 'is_main_guest': is_main_guest}


def delete_hotel_guest(guest_id: int) -> bool:
    """
    Delete hotel guest record.

    Args:
        guest_id: Hotel guest ID to delete

    Returns:
        True if deleted successfully
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM hotel_guests WHERE id = ?', (guest_id,))
    db.commit()
    return cursor.rowcount > 0


def delete_guests_by_source(source_file: str) -> int:
    """
    Delete all guests imported from a specific source file.

    Args:
        source_file: Source file name

    Returns:
        Number of records deleted
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM hotel_guests WHERE source_file = ?', (source_file,))
    db.commit()
    return cursor.rowcount


def get_guest_count() -> Dict[str, int]:
    """
    Get guest statistics.

    Returns:
        Dict with 'total', 'active', 'arriving_today', 'departing_today'
    """
    db = get_db()
    cursor = db.cursor()

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
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT DISTINCT room_number FROM hotel_guests
        WHERE departure_date >= date("now")
        ORDER BY CAST(room_number AS INTEGER), room_number
    ''')
    return [row['room_number'] for row in cursor.fetchall()]
