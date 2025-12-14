"""
Reservation data access functions.
Handles reservation CRUD operations, furniture assignments, and availability.
"""

from database import get_db
from datetime import datetime, timedelta


def get_all_reservations(start_date: str = None, end_date: str = None, state_id: int = None) -> list:
    """
    Get all reservations with optional filters.

    Args:
        start_date: Filter by start date (YYYY-MM-DD)
        end_date: Filter by end date (YYYY-MM-DD)
        state_id: Filter by state ID

    Returns:
        List of reservation dicts with customer and state information
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT r.*,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.customer_type,
               c.room_number,
               s.name as state_name,
               s.color as state_color
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_states s ON r.state_id = s.id
        WHERE 1=1
    '''

    params = []

    if start_date:
        query += ' AND r.start_date >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND r.end_date <= ?'
        params.append(end_date)

    if state_id:
        query += ' AND r.state_id = ?'
        params.append(state_id)

    query += ' ORDER BY r.start_date DESC, r.created_at DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_reservation_by_id(reservation_id: int) -> dict:
    """
    Get reservation by ID with full details.

    Args:
        reservation_id: Reservation ID

    Returns:
        Reservation dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT r.*,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.customer_type,
               c.room_number,
               c.email,
               c.phone,
               s.name as state_name,
               s.color as state_color
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_states s ON r.state_id = s.id
        WHERE r.id = ?
    ''', (reservation_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_reservation(customer_id: int, start_date: str, end_date: str,
                        num_people: int, state_id: int = None, **kwargs) -> int:
    """
    Create new reservation.

    Args:
        customer_id: Customer ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        num_people: Number of people
        state_id: Reservation state ID (defaults to 'pendiente')
        **kwargs: Optional fields (preferences, notes, internal_notes, source, created_by)

    Returns:
        New reservation ID
    """
    db = get_db()
    cursor = db.cursor()

    # Get default state if not provided
    if not state_id:
        cursor.execute('SELECT id FROM beach_reservation_states WHERE code = "pendiente"')
        row = cursor.fetchone()
        state_id = row['id'] if row else None

    cursor.execute('''
        INSERT INTO beach_reservations
        (customer_id, start_date, end_date, num_people, state_id,
         preferences, notes, internal_notes, source, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_id, start_date, end_date, num_people, state_id,
          kwargs.get('preferences'), kwargs.get('notes'), kwargs.get('internal_notes'),
          kwargs.get('source', 'direct'), kwargs.get('created_by')))

    db.commit()
    return cursor.lastrowid


def update_reservation(reservation_id: int, **kwargs) -> bool:
    """
    Update reservation fields.

    Args:
        reservation_id: Reservation ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    db = get_db()

    allowed_fields = ['start_date', 'end_date', 'num_people', 'state_id',
                      'preferences', 'notes', 'internal_notes']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(reservation_id)

    query = f'UPDATE beach_reservations SET {", ".join(updates)} WHERE id = ?'

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_reservation(reservation_id: int) -> bool:
    """
    Delete reservation (hard delete, cascades to furniture assignments).

    Args:
        reservation_id: Reservation ID to delete

    Returns:
        True if deleted successfully
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM beach_reservations WHERE id = ?', (reservation_id,))
    db.commit()

    return cursor.rowcount > 0


def get_reservation_states() -> list:
    """
    Get all reservation states.

    Returns:
        List of state dicts ordered by display_order
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM beach_reservation_states
        WHERE active = 1
        ORDER BY display_order
    ''')
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_reservation_furniture(reservation_id: int, date: str = None) -> list:
    """
    Get furniture assigned to reservation.

    Args:
        reservation_id: Reservation ID
        date: Specific date (optional, YYYY-MM-DD)

    Returns:
        List of furniture assignment dicts
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT rf.*, f.number, f.furniture_type, f.capacity,
               z.name as zone_name
        FROM beach_reservation_furniture rf
        JOIN beach_furniture f ON rf.furniture_id = f.id
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        WHERE rf.reservation_id = ?
    '''

    params = [reservation_id]

    if date:
        query += ' AND rf.assignment_date = ?'
        params.append(date)

    query += ' ORDER BY rf.assignment_date, f.number'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def assign_furniture(reservation_id: int, furniture_id: int, assignment_date: str) -> bool:
    """
    Assign furniture to reservation for a specific date.

    Args:
        reservation_id: Reservation ID
        furniture_id: Furniture ID
        assignment_date: Date of assignment (YYYY-MM-DD)

    Returns:
        True if assigned successfully

    Raises:
        ValueError if furniture is not available
    """
    if not check_furniture_availability(furniture_id, assignment_date, assignment_date):
        raise ValueError('El mobiliario no está disponible para esta fecha')

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
            VALUES (?, ?, ?)
        ''', (reservation_id, furniture_id, assignment_date))
        db.commit()
        return True
    except Exception:
        return False


def remove_furniture_assignment(reservation_id: int, furniture_id: int, assignment_date: str) -> bool:
    """
    Remove furniture assignment.

    Args:
        reservation_id: Reservation ID
        furniture_id: Furniture ID
        assignment_date: Date of assignment

    Returns:
        True if removed successfully
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        DELETE FROM beach_reservation_furniture
        WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
    ''', (reservation_id, furniture_id, assignment_date))

    db.commit()
    return cursor.rowcount > 0


def get_daily_state(reservation_id: int, date: str) -> dict:
    """
    Get reservation state for a specific date.

    Args:
        reservation_id: Reservation ID
        date: Date (YYYY-MM-DD)

    Returns:
        Daily state dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT ds.*, s.name as state_name, s.color as state_color
        FROM beach_reservation_daily_states ds
        LEFT JOIN beach_reservation_states s ON ds.state_id = s.id
        WHERE ds.reservation_id = ? AND ds.date = ?
    ''', (reservation_id, date))
    row = cursor.fetchone()
    return dict(row) if row else None


def set_daily_state(reservation_id: int, date: str, state_id: int, notes: str = None) -> bool:
    """
    Set or update reservation state for a specific date.

    Args:
        reservation_id: Reservation ID
        date: Date (YYYY-MM-DD)
        state_id: State ID
        notes: Optional notes

    Returns:
        True if set successfully
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO beach_reservation_daily_states
        (reservation_id, date, state_id, notes)
        VALUES (?, ?, ?, ?)
    ''', (reservation_id, date, state_id, notes))

    db.commit()
    return True


def check_furniture_availability(furniture_id: int, start_date: str, end_date: str) -> bool:
    """
    Check if furniture is available for date range.
    Excludes reservations with releasing states (cancelada, noshow, liberada).

    Args:
        furniture_id: Furniture ID to check
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        True if available, False if occupied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_reservation_states s ON r.state_id = s.id
        WHERE rf.furniture_id = ?
          AND rf.assignment_date >= ?
          AND rf.assignment_date <= ?
          AND s.is_availability_releasing = 0
    ''', (furniture_id, start_date, end_date))

    row = cursor.fetchone()
    return row['count'] == 0


def get_reservations_by_furniture(furniture_id: int, date: str) -> list:
    """
    Get reservations for specific furniture on a specific date.
    Used for map display.

    Args:
        furniture_id: Furniture ID
        date: Date (YYYY-MM-DD)

    Returns:
        List of reservation dicts
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT r.*, c.first_name, c.last_name, s.name as state_name, s.color as state_color
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_states s ON r.state_id = s.id
        WHERE rf.furniture_id = ? AND rf.assignment_date = ?
        ORDER BY r.created_at
    ''', (furniture_id, date))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
