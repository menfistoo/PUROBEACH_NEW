"""
Reservation data access functions.
Handles reservation CRUD operations, furniture assignments, state management,
and availability checking. Implements RESERVATIONS_SYSTEM_SPEC.md

Phase 6A: Core CRUD + State Management
"""

from database import get_db
from datetime import datetime, timedelta, date as date_type


# =============================================================================
# CONSTANTS
# =============================================================================

RESERVATION_STATE_DISPLAY_PRIORITY = {
    'Cobrada': 5,      # Highest priority
    'Sentada': 4,
    'Confirmada': 3,
    'Cancelada': 2,
    'No-Show': 1,
    'Liberada': 0      # Lowest priority
}


# =============================================================================
# TICKET NUMBER GENERATION (SPEC Section 2)
# =============================================================================

def generate_reservation_number(reservation_date: str = None, cursor=None, max_retries: int = 5) -> str:
    """
    Generate unique reservation number with race condition protection.

    Format: YYMMDDRR where:
    - YY = Year (2 digits)
    - MM = Month (2 digits)
    - DD = Day (2 digits)
    - RR = Daily sequential (01-99)

    Example: 25011601 = First reservation on Jan 16, 2025

    Args:
        reservation_date: Date for reservation (default: today)
        cursor: Active transaction cursor
        max_retries: Max attempts on collision

    Returns:
        str: Unique reservation number (YYMMDDRR)

    Raises:
        ValueError: If unable to generate unique number
    """
    if not reservation_date:
        reservation_date = datetime.now().strftime('%Y-%m-%d')

    date_obj = datetime.strptime(reservation_date, '%Y-%m-%d')
    date_prefix = date_obj.strftime('%y%m%d')  # YYMMDD

    db = get_db()
    cur = cursor or db.cursor()

    for attempt in range(max_retries):
        # Find max sequential for the day
        cur.execute('''
            SELECT MAX(CAST(SUBSTR(ticket_number, 7, 2) AS INTEGER)) as max_seq
            FROM beach_reservations
            WHERE ticket_number LIKE ?
        ''', (f'{date_prefix}%',))

        result = cur.fetchone()
        next_seq = (result['max_seq'] or 0) + 1

        if next_seq > 99:
            raise ValueError(f"Máximo de reservas diarias (99) alcanzado para {reservation_date}")

        ticket_number = f"{date_prefix}{next_seq:02d}"

        # Verify uniqueness
        cur.execute('SELECT id FROM beach_reservations WHERE ticket_number = ?', (ticket_number,))
        if not cur.fetchone():
            return ticket_number

    raise ValueError("No se pudo generar número único después de varios intentos")


def generate_child_reservation_number(parent_number: str, child_index: int) -> str:
    """
    Generate ticket number for child reservation.

    Format: YYMMDDRR-C where C = index (1, 2, 3...)
    Example: 25011601-1, 25011601-2

    Args:
        parent_number: Parent ticket number
        child_index: Child index (1-based)

    Returns:
        str: Child ticket number
    """
    return f"{parent_number}-{child_index}"


# =============================================================================
# STATE MANAGEMENT (SPEC Section 4)
# =============================================================================

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


def get_active_releasing_states() -> list:
    """
    Get states that release availability.

    Returns:
        list: Names of states with is_availability_releasing=1
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT name FROM beach_reservation_states
        WHERE is_availability_releasing = 1 AND active = 1
    ''')
    return [row['name'] for row in cursor.fetchall()]


def add_reservation_state(reservation_id: int, state_type: str, changed_by: str, notes: str = '') -> bool:
    """
    Add state to reservation (accumulative CSV).

    Behavior:
    1. Adds to current_states CSV
    2. Updates current_state to new state
    3. Records in history
    4. If No-Show: creates automatic incident
    5. Updates customer statistics

    Args:
        reservation_id: Reservation ID
        state_type: State name to add
        changed_by: Username making change
        notes: Optional notes

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Get current reservation data
        cursor.execute('SELECT customer_id, current_states FROM beach_reservations WHERE id = ?',
                      (reservation_id,))
        row = cursor.fetchone()
        if not row:
            return False

        customer_id = row['customer_id']
        current_states = row['current_states'] or ''

        # Add to CSV (avoid duplicates)
        states_list = [s.strip() for s in current_states.split(',') if s.strip()]
        if state_type not in states_list:
            states_list.append(state_type)

        new_states_csv = ', '.join(states_list)

        # Update reservation
        cursor.execute('''
            UPDATE beach_reservations
            SET current_states = ?,
                current_state = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_states_csv, state_type, reservation_id))

        # Record in history
        cursor.execute('''
            INSERT INTO reservation_status_history
            (reservation_id, status_type, action, changed_by, notes, created_at)
            VALUES (?, ?, 'added', ?, ?, CURRENT_TIMESTAMP)
        ''', (reservation_id, state_type, changed_by, notes))

        # Auto-create incident for No-Show
        if state_type == 'No-Show':
            _create_noshow_incident(cursor, customer_id, reservation_id, changed_by)

        db.commit()

        # Update customer statistics
        update_customer_statistics(customer_id)

        return True

    except Exception as e:
        db.rollback()
        raise


def remove_reservation_state(reservation_id: int, state_type: str, changed_by: str, notes: str = '') -> bool:
    """
    Remove state from reservation.

    Behavior:
    1. Removes from current_states CSV
    2. Recalculates current_state by priority
    3. Records in history
    4. Updates customer statistics

    Args:
        reservation_id: Reservation ID
        state_type: State name to remove
        changed_by: Username making change
        notes: Optional notes

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Get current reservation data
        cursor.execute('SELECT customer_id, current_states FROM beach_reservations WHERE id = ?',
                      (reservation_id,))
        row = cursor.fetchone()
        if not row:
            return False

        customer_id = row['customer_id']
        current_states = row['current_states'] or ''

        # Remove from CSV
        states_list = [s.strip() for s in current_states.split(',') if s.strip()]
        if state_type in states_list:
            states_list.remove(state_type)

        new_states_csv = ', '.join(states_list)

        # Recalculate current_state by priority
        new_current_state = _get_highest_priority_state(states_list)

        # Update reservation
        cursor.execute('''
            UPDATE beach_reservations
            SET current_states = ?,
                current_state = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_states_csv, new_current_state, reservation_id))

        # Record in history
        cursor.execute('''
            INSERT INTO reservation_status_history
            (reservation_id, status_type, action, changed_by, notes, created_at)
            VALUES (?, ?, 'removed', ?, ?, CURRENT_TIMESTAMP)
        ''', (reservation_id, state_type, changed_by, notes))

        db.commit()

        # Update customer statistics
        update_customer_statistics(customer_id)

        return True

    except Exception as e:
        db.rollback()
        raise


def cancel_beach_reservation(reservation_id: int, cancelled_by: str, notes: str = '') -> bool:
    """Shortcut to add 'Cancelada' state."""
    return add_reservation_state(reservation_id, 'Cancelada', cancelled_by, notes)


def calculate_reservation_color(current_states_str: str) -> str:
    """
    Calculate display color based on states.

    Priority rules:
    1. If has Cobrada → Cobrada color
    2. If has Cancelada/No-Show → respective color
    3. Else → highest priority state color

    Args:
        current_states_str: CSV of states

    Returns:
        str: Hex color code
    """
    states_list = [s.strip() for s in current_states_str.split(',') if s.strip()]

    # Priority color checks
    if 'Cobrada' in states_list:
        return _get_state_color('Cobrada')
    if 'Cancelada' in states_list:
        return _get_state_color('Cancelada')
    if 'No-Show' in states_list:
        return _get_state_color('No-Show')

    # Use highest priority state
    if states_list:
        top_state = max(states_list, key=lambda s: RESERVATION_STATE_DISPLAY_PRIORITY.get(s, 0))
        return _get_state_color(top_state)

    return '#CCCCCC'  # Default


def _get_highest_priority_state(states_list: list) -> str:
    """Get state with highest display priority from list."""
    if not states_list:
        return 'Confirmada'
    return max(states_list, key=lambda s: RESERVATION_STATE_DISPLAY_PRIORITY.get(s, 0))


def _get_state_color(state_name: str) -> str:
    """Get color for state name from database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT color FROM beach_reservation_states WHERE name = ?', (state_name,))
    row = cursor.fetchone()
    return row['color'] if row else '#CCCCCC'


def _create_noshow_incident(cursor, customer_id: int, reservation_id: int, reported_by: str):
    """Create automatic incident for No-Show."""
    # Check if beach_customer_incidents table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='beach_customer_incidents'")
    if cursor.fetchone():
        cursor.execute('''
            INSERT INTO beach_customer_incidents
            (customer_id, description, incident_type, reservation_id, reported_by, created_at)
            VALUES (?, ?, 'no_show', ?, ?, CURRENT_TIMESTAMP)
        ''', (customer_id, f'No-Show automático para reserva {reservation_id}', reservation_id, reported_by))


# =============================================================================
# RESERVATION CRUD (SPEC Section 3)
# =============================================================================

def create_beach_reservation(
    customer_id: int,
    reservation_date: str,
    num_people: int,
    furniture_ids: list = None,
    time_slot: str = 'all_day',
    payment_status: str = 'NO',
    charge_to_room: int = 0,
    charge_reference: str = '',
    price: float = 0.0,
    preferences: str = '',
    observations: str = '',
    created_by: str = None,
    ticket_number: str = None,
    check_in_date: str = None,
    check_out_date: str = None,
    hamaca_included: int = 1,
    price_catalog_id: int = None,
    final_price: float = 0.0,
    paid: int = 0,
    parent_reservation_id: int = None,
    minimum_consumption_policy_id: int = None,
    minimum_consumption_amount: float = 0.0,
    reservation_type: str = 'normal'
) -> tuple:
    """
    Create a complete reservation with all validations.

    Args:
        customer_id: Customer ID
        reservation_date: Reservation date (YYYY-MM-DD)
        num_people: Number of people
        furniture_ids: List of furniture IDs to assign
        time_slot: 'all_day', 'morning', or 'afternoon'
        payment_status: 'SÍ' or 'NO'
        charge_to_room: 1 to charge to room, 0 otherwise
        charge_reference: Reference for room charge
        price: Base price
        preferences: CSV of preference codes
        observations: Notes/observations
        created_by: Username creating reservation
        ticket_number: Pre-generated ticket (or auto-generate)
        check_in_date: Hotel check-in date
        check_out_date: Hotel check-out date
        hamaca_included: 1 if included free, 0 if charged
        price_catalog_id: Price catalog item ID
        final_price: Final calculated price
        paid: 1 if paid, 0 otherwise
        parent_reservation_id: Parent reservation ID for multi-day
        minimum_consumption_policy_id: Consumption policy ID
        minimum_consumption_amount: Minimum consumption amount
        reservation_type: 'normal' or 'bloqueo'

    Returns:
        tuple: (reservation_id, ticket_number)

    Raises:
        ValueError: If validations fail
    """
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('BEGIN IMMEDIATE')

        # Generate ticket number if not provided
        if not ticket_number:
            ticket_number = generate_reservation_number(reservation_date, cursor)

        # Insert reservation
        cursor.execute('''
            INSERT INTO beach_reservations (
                customer_id, ticket_number, reservation_date, start_date, end_date,
                num_people, time_slot, current_states, current_state,
                payment_status, price, final_price, hamaca_included, price_catalog_id, paid,
                charge_to_room, charge_reference,
                minimum_consumption_amount, minimum_consumption_policy_id,
                check_in_date, check_out_date, preferences, notes,
                parent_reservation_id, reservation_type, created_by, created_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, 'Confirmada', 'Confirmada',
                ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, CURRENT_TIMESTAMP
            )
        ''', (
            customer_id, ticket_number, reservation_date, reservation_date, reservation_date,
            num_people, time_slot,
            payment_status, price, final_price, hamaca_included, price_catalog_id, paid,
            charge_to_room, charge_reference,
            minimum_consumption_amount, minimum_consumption_policy_id,
            check_in_date, check_out_date, preferences, observations,
            parent_reservation_id, reservation_type, created_by
        ))

        reservation_id = cursor.lastrowid

        # Assign furniture
        if furniture_ids:
            for furniture_id in furniture_ids:
                cursor.execute('''
                    INSERT INTO beach_reservation_furniture
                    (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, ?)
                ''', (reservation_id, furniture_id, reservation_date))

        # Record initial state in history
        cursor.execute('''
            INSERT INTO reservation_status_history
            (reservation_id, status_type, action, changed_by, notes, created_at)
            VALUES (?, 'Confirmada', 'added', ?, 'Creación de reserva', CURRENT_TIMESTAMP)
        ''', (reservation_id, created_by))

        db.commit()

        # Sync preferences to customer profile
        if preferences:
            sync_preferences_to_customer(customer_id, preferences)

        return reservation_id, ticket_number

    except Exception as e:
        db.rollback()
        raise


def get_beach_reservation_by_id(reservation_id: int) -> dict:
    """
    Get reservation by ID with all related data.

    Args:
        reservation_id: Reservation ID

    Returns:
        dict: Reservation with customer, state, and furniture info
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT r.*,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.customer_type,
               c.room_number as customer_room,
               c.email as customer_email,
               c.phone as customer_phone
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE r.id = ?
    ''', (reservation_id,))

    row = cursor.fetchone()
    if not row:
        return None

    reservation = dict(row)

    # Get furniture assignments
    cursor.execute('''
        SELECT rf.*, f.number, f.furniture_type, f.capacity,
               z.name as zone_name
        FROM beach_reservation_furniture rf
        JOIN beach_furniture f ON rf.furniture_id = f.id
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        WHERE rf.reservation_id = ?
        ORDER BY rf.assignment_date, f.number
    ''', (reservation_id,))
    reservation['furniture'] = [dict(r) for r in cursor.fetchall()]

    # Get tags
    cursor.execute('''
        SELECT t.* FROM beach_tags t
        JOIN beach_reservation_tags rt ON t.id = rt.tag_id
        WHERE rt.reservation_id = ?
    ''', (reservation_id,))
    reservation['tags'] = [dict(r) for r in cursor.fetchall()]

    # Calculate display color
    reservation['display_color'] = calculate_reservation_color(reservation.get('current_states', ''))

    return reservation


def get_beach_reservation_by_ticket(ticket_number: str) -> dict:
    """
    Get reservation by ticket number.

    Args:
        ticket_number: Ticket number (YYMMDDRR or YYMMDDRR-N)

    Returns:
        dict: Reservation or None
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id FROM beach_reservations WHERE ticket_number = ?', (ticket_number,))
    row = cursor.fetchone()
    if row:
        return get_beach_reservation_by_id(row['id'])
    return None


def update_beach_reservation(reservation_id: int, **kwargs) -> bool:
    """
    Update reservation fields.

    Args:
        reservation_id: Reservation ID
        **kwargs: Fields to update

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    allowed_fields = [
        'reservation_date', 'num_people', 'time_slot',
        'payment_status', 'price', 'final_price', 'hamaca_included',
        'price_catalog_id', 'paid', 'charge_to_room', 'charge_reference',
        'minimum_consumption_amount', 'minimum_consumption_policy_id',
        'check_in_date', 'check_out_date', 'preferences', 'notes', 'observations'
    ]

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

    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_reservation(reservation_id: int) -> bool:
    """
    Delete reservation (cascades to furniture assignments).

    Args:
        reservation_id: Reservation ID

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM beach_reservations WHERE id = ?', (reservation_id,))
    db.commit()
    return cursor.rowcount > 0


# =============================================================================
# RESERVATION QUERIES
# =============================================================================

def get_all_beach_reservations(
    date: str = None,
    date_from: str = None,
    date_to: str = None,
    status_filter: str = None,
    room_number: str = None,
    guest_name: str = None,
    customer_type: str = None,
    ticket_number: str = None
) -> list:
    """
    List reservations with filters.

    Args:
        date: Exact date
        date_from: Range start
        date_to: Range end
        status_filter: State name filter
        room_number: Filter by room
        guest_name: Search by name
        customer_type: 'interno' or 'externo'
        ticket_number: Search by ticket

    Returns:
        list: Reservations with customer data
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT r.*,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.customer_type,
               c.room_number
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE 1=1
    '''
    params = []

    if date:
        query += ' AND r.reservation_date = ?'
        params.append(date)
    elif date_from and date_to:
        query += ' AND r.reservation_date BETWEEN ? AND ?'
        params.extend([date_from, date_to])
    elif date_from:
        query += ' AND r.reservation_date >= ?'
        params.append(date_from)
    elif date_to:
        query += ' AND r.reservation_date <= ?'
        params.append(date_to)

    if status_filter:
        query += ' AND r.current_state = ?'
        params.append(status_filter)

    if room_number:
        query += ' AND c.room_number = ?'
        params.append(room_number)

    if guest_name:
        query += ' AND (c.first_name LIKE ? OR c.last_name LIKE ?)'
        params.extend([f'%{guest_name}%', f'%{guest_name}%'])

    if customer_type:
        query += ' AND c.customer_type = ?'
        params.append(customer_type)

    if ticket_number:
        query += ' AND r.ticket_number LIKE ?'
        params.append(f'%{ticket_number}%')

    query += ' ORDER BY r.reservation_date DESC, r.created_at DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    reservations = []
    for row in rows:
        res = dict(row)
        res['display_color'] = calculate_reservation_color(res.get('current_states', ''))
        reservations.append(res)

    return reservations


def get_linked_reservations(reservation_id: int) -> list:
    """
    Get all linked reservations (parent + children).

    Args:
        reservation_id: Any reservation in the group

    Returns:
        list: All reservations in the group
    """
    db = get_db()
    cursor = db.cursor()

    # First check if this is a parent or child
    cursor.execute('''
        SELECT id, parent_reservation_id FROM beach_reservations WHERE id = ?
    ''', (reservation_id,))
    row = cursor.fetchone()
    if not row:
        return []

    # Determine the parent ID
    if row['parent_reservation_id']:
        parent_id = row['parent_reservation_id']
    else:
        parent_id = reservation_id

    # Get parent and all children
    cursor.execute('''
        SELECT * FROM beach_reservations
        WHERE id = ? OR parent_reservation_id = ?
        ORDER BY reservation_date
    ''', (parent_id, parent_id))

    return [dict(r) for r in cursor.fetchall()]


def get_status_history(reservation_id: int) -> list:
    """
    Get state change history for reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        list: History entries ordered by date desc
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM reservation_status_history
        WHERE reservation_id = ?
        ORDER BY created_at DESC
    ''', (reservation_id,))
    return [dict(r) for r in cursor.fetchall()]


# =============================================================================
# BLUEPRINT COMPATIBILITY FUNCTIONS
# =============================================================================

def get_reservations_filtered(
    date_from: str = None,
    date_to: str = None,
    customer_type: str = None,
    state: str = None,
    search: str = None,
    page: int = 1,
    per_page: int = 50
) -> dict:
    """
    Get filtered reservations with pagination (for list view).

    Args:
        date_from: Start date filter
        date_to: End date filter
        customer_type: 'interno' or 'externo'
        state: State name filter
        search: Search term (name, ticket, room)
        page: Page number
        per_page: Items per page

    Returns:
        dict: {items: list, total: int, page: int, per_page: int, pages: int}
    """
    db = get_db()
    cursor = db.cursor()

    # Build base query
    query = '''
        SELECT r.*,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.customer_type,
               c.room_number
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE 1=1
    '''
    count_query = '''
        SELECT COUNT(*) as total
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE 1=1
    '''
    params = []

    if date_from:
        query += ' AND r.reservation_date >= ?'
        count_query += ' AND r.reservation_date >= ?'
        params.append(date_from)

    if date_to:
        query += ' AND r.reservation_date <= ?'
        count_query += ' AND r.reservation_date <= ?'
        params.append(date_to)

    if customer_type:
        query += ' AND c.customer_type = ?'
        count_query += ' AND c.customer_type = ?'
        params.append(customer_type)

    if state:
        query += ' AND r.current_state = ?'
        count_query += ' AND r.current_state = ?'
        params.append(state)

    if search:
        search_clause = ''' AND (
            c.first_name LIKE ? OR c.last_name LIKE ? OR
            c.room_number LIKE ? OR r.ticket_number LIKE ?
        )'''
        query += search_clause
        count_query += search_clause
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])

    # Get total count
    cursor.execute(count_query, params)
    total = cursor.fetchone()['total']

    # Add pagination
    query += ' ORDER BY r.reservation_date DESC, r.created_at DESC'
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    items = []
    for row in rows:
        res = dict(row)
        res['display_color'] = calculate_reservation_color(res.get('current_states', ''))
        items.append(res)

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_reservation_with_details(reservation_id: int) -> dict:
    """Alias for get_beach_reservation_by_id."""
    return get_beach_reservation_by_id(reservation_id)


def get_reservation_by_id(reservation_id: int) -> dict:
    """Alias for get_beach_reservation_by_id."""
    return get_beach_reservation_by_id(reservation_id)


def get_reservation_stats(date_from: str = None, date_to: str = None) -> dict:
    """
    Get reservation statistics.

    Args:
        date_from: Start date
        date_to: End date

    Returns:
        dict: Statistics (total, by_state, by_type, etc.)
    """
    db = get_db()
    cursor = db.cursor()

    # Use today as default
    if not date_from:
        date_from = datetime.now().strftime('%Y-%m-%d')
    if not date_to:
        date_to = date_from

    # Total count
    cursor.execute('''
        SELECT COUNT(*) as total FROM beach_reservations
        WHERE reservation_date BETWEEN ? AND ?
    ''', (date_from, date_to))
    total = cursor.fetchone()['total']

    # By state
    cursor.execute('''
        SELECT current_state, COUNT(*) as count
        FROM beach_reservations
        WHERE reservation_date BETWEEN ? AND ?
        GROUP BY current_state
    ''', (date_from, date_to))
    by_state = {row['current_state']: row['count'] for row in cursor.fetchall()}

    # By customer type
    cursor.execute('''
        SELECT c.customer_type, COUNT(*) as count
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE r.reservation_date BETWEEN ? AND ?
        GROUP BY c.customer_type
    ''', (date_from, date_to))
    by_type = {row['customer_type']: row['count'] for row in cursor.fetchall()}

    # Total people
    cursor.execute('''
        SELECT SUM(num_people) as total_people
        FROM beach_reservations
        WHERE reservation_date BETWEEN ? AND ?
    ''', (date_from, date_to))
    total_people = cursor.fetchone()['total_people'] or 0

    return {
        'total': total,
        'by_state': by_state,
        'by_type': by_type,
        'interno': by_type.get('interno', 0),
        'externo': by_type.get('externo', 0),
        'total_people': total_people,
        'confirmadas': by_state.get('Confirmada', 0),
        'canceladas': by_state.get('Cancelada', 0)
    }


def get_available_furniture(date: str, zone_id: int = None, furniture_type: str = None) -> list:
    """
    Get available furniture for a date.

    Args:
        date: Date to check (YYYY-MM-DD)
        zone_id: Filter by zone
        furniture_type: Filter by type

    Returns:
        list: Available furniture items
    """
    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()

    query = '''
        SELECT f.*, z.name as zone_name, ft.display_name as type_name
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        WHERE f.active = 1
          AND f.id NOT IN (
              SELECT rf.furniture_id
              FROM beach_reservation_furniture rf
              JOIN beach_reservations r ON rf.reservation_id = r.id
              WHERE rf.assignment_date = ?
    '''
    params = [date]

    # Exclude only non-releasing states
    if releasing_states:
        placeholders = ','.join('?' * len(releasing_states))
        query += f'''
                AND r.current_state NOT IN ({placeholders})
        '''
        params.extend(releasing_states)

    query += ')'

    if zone_id:
        query += ' AND f.zone_id = ?'
        params.append(zone_id)

    if furniture_type:
        query += ' AND f.furniture_type = ?'
        params.append(furniture_type)

    query += ' ORDER BY f.zone_id, f.number'

    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def create_reservation_with_furniture(
    customer_id: int,
    start_date: str,
    end_date: str,
    num_people: int,
    furniture_ids: list,
    preferences: str = '',
    notes: str = '',
    internal_notes: str = '',
    created_by: str = None
) -> int:
    """
    Create reservation with furniture assignments.
    Wrapper for create_beach_reservation for backward compatibility.

    Args:
        customer_id: Customer ID
        start_date: Start date
        end_date: End date
        num_people: Number of people
        furniture_ids: Furniture to assign
        preferences: CSV of preferences
        notes: Notes
        internal_notes: Internal notes
        created_by: Creator username

    Returns:
        int: Reservation ID
    """
    reservation_id, ticket = create_beach_reservation(
        customer_id=customer_id,
        reservation_date=start_date,
        num_people=num_people,
        furniture_ids=furniture_ids,
        preferences=preferences,
        observations=notes,
        created_by=created_by
    )
    return reservation_id


def update_reservation_with_furniture(
    reservation_id: int,
    furniture_ids: list,
    **kwargs
) -> bool:
    """
    Update reservation and furniture assignments.

    Args:
        reservation_id: Reservation ID
        furniture_ids: New furniture list
        **kwargs: Other fields to update

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Update reservation fields
        if kwargs:
            update_beach_reservation(reservation_id, **kwargs)

        # Get reservation date
        cursor.execute('SELECT reservation_date FROM beach_reservations WHERE id = ?',
                      (reservation_id,))
        row = cursor.fetchone()
        if not row:
            return False
        res_date = row['reservation_date']

        # Clear existing assignments
        cursor.execute('''
            DELETE FROM beach_reservation_furniture
            WHERE reservation_id = ? AND assignment_date = ?
        ''', (reservation_id, res_date))

        # Add new assignments
        for furniture_id in furniture_ids:
            cursor.execute('''
                INSERT INTO beach_reservation_furniture
                (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, ?)
            ''', (reservation_id, furniture_id, res_date))

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def change_reservation_state(reservation_id: int, new_state: str, changed_by: str, reason: str = '') -> bool:
    """
    Change reservation state (replaces current state).
    For single-state changes, use add_reservation_state for multi-state.

    Args:
        reservation_id: Reservation ID
        new_state: New state name
        changed_by: Username
        reason: Change reason

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Get current state
        cursor.execute('SELECT current_state, customer_id FROM beach_reservations WHERE id = ?',
                      (reservation_id,))
        row = cursor.fetchone()
        if not row:
            return False

        old_state = row['current_state']
        customer_id = row['customer_id']

        # Update to new state
        cursor.execute('''
            UPDATE beach_reservations
            SET current_state = ?,
                current_states = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_state, new_state, reservation_id))

        # Record history
        cursor.execute('''
            INSERT INTO reservation_status_history
            (reservation_id, status_type, action, changed_by, notes, created_at)
            VALUES (?, ?, 'changed', ?, ?, CURRENT_TIMESTAMP)
        ''', (reservation_id, new_state, changed_by, f'Cambio de {old_state} a {new_state}. {reason}'))

        db.commit()

        # Update customer stats
        update_customer_statistics(customer_id)

        return True

    except Exception:
        db.rollback()
        raise


# =============================================================================
# PREFERENCE SYNC
# =============================================================================

def sync_preferences_to_customer(customer_id: int, preferences_csv: str) -> bool:
    """
    Sync reservation preferences to customer profile.

    Args:
        customer_id: Customer ID
        preferences_csv: CSV of preference codes

    Returns:
        bool: Success status
    """
    if not preferences_csv:
        return True

    db = get_db()
    cursor = db.cursor()

    try:
        pref_codes = [p.strip() for p in preferences_csv.split(',') if p.strip()]

        for code in pref_codes:
            # Get preference ID
            cursor.execute('SELECT id FROM beach_preferences WHERE code = ?', (code,))
            row = cursor.fetchone()
            if row:
                # Insert if not exists
                cursor.execute('''
                    INSERT OR IGNORE INTO beach_customer_preferences
                    (customer_id, preference_id)
                    VALUES (?, ?)
                ''', (customer_id, row['id']))

        db.commit()
        return True

    except Exception:
        db.rollback()
        return False


def get_customer_preference_codes(customer_id: int) -> list:
    """
    Get preference codes for customer.

    Args:
        customer_id: Customer ID

    Returns:
        list: Preference codes
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.code FROM beach_preferences p
        JOIN beach_customer_preferences cp ON p.id = cp.preference_id
        WHERE cp.customer_id = ?
    ''', (customer_id,))
    return [row['code'] for row in cursor.fetchall()]


# =============================================================================
# CUSTOMER STATISTICS
# =============================================================================

def update_customer_statistics(customer_id: int) -> bool:
    """
    Update customer statistics based on reservations.

    Calculates:
    - total_visits: Reservations with 'Sentada' state
    - last_visit: Most recent visit date

    Args:
        customer_id: Customer ID

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Count visits (reservations with Sentada state)
        cursor.execute('''
            SELECT COUNT(*) as visits
            FROM beach_reservations
            WHERE customer_id = ?
              AND current_states LIKE '%Sentada%'
        ''', (customer_id,))
        visits = cursor.fetchone()['visits']

        # Get last visit date
        cursor.execute('''
            SELECT MAX(reservation_date) as last_visit
            FROM beach_reservations
            WHERE customer_id = ?
              AND current_states LIKE '%Sentada%'
        ''', (customer_id,))
        last_visit = cursor.fetchone()['last_visit']

        # Update customer
        cursor.execute('''
            UPDATE beach_customers
            SET total_visits = ?,
                last_visit = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (visits, last_visit, customer_id))

        db.commit()
        return True

    except Exception:
        db.rollback()
        return False


# =============================================================================
# AVAILABILITY CHECK (Basic - Full implementation in Phase 6B)
# =============================================================================

def check_furniture_availability(furniture_id: int, start_date: str, end_date: str,
                                  exclude_reservation_id: int = None) -> bool:
    """
    Check if furniture is available for date range.
    Excludes reservations with releasing states.

    Args:
        furniture_id: Furniture ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        exclude_reservation_id: Reservation ID to exclude (for updates)

    Returns:
        bool: True if available
    """
    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()

    query = '''
        SELECT COUNT(*) as count
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE rf.furniture_id = ?
          AND rf.assignment_date >= ?
          AND rf.assignment_date <= ?
    '''
    params = [furniture_id, start_date, end_date]

    # Exclude releasing states
    if releasing_states:
        placeholders = ','.join('?' * len(releasing_states))
        query += f' AND r.current_state NOT IN ({placeholders})'
        params.extend(releasing_states)

    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    cursor.execute(query, params)
    return cursor.fetchone()['count'] == 0


def get_reservation_furniture(reservation_id: int, date: str = None) -> list:
    """
    Get furniture assigned to reservation.

    Args:
        reservation_id: Reservation ID
        date: Specific date (optional)

    Returns:
        list: Furniture assignments
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
    return [dict(row) for row in cursor.fetchall()]


def get_reservations_by_furniture(furniture_id: int, date: str) -> list:
    """
    Get reservations for specific furniture on a date.

    Args:
        furniture_id: Furniture ID
        date: Date (YYYY-MM-DD)

    Returns:
        list: Reservations
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT r.*, c.first_name, c.last_name
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE rf.furniture_id = ? AND rf.assignment_date = ?
        ORDER BY r.created_at
    ''', (furniture_id, date))
    return [dict(row) for row in cursor.fetchall()]
