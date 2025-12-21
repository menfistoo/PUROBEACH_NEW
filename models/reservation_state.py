"""
Reservation state management functions.
Handles state transitions, history, and color calculations.
"""

from database import get_db


# =============================================================================
# CONSTANTS
# =============================================================================

RESERVATION_STATE_DISPLAY_PRIORITY = {
    'Activa': 7,       # Highest priority - customer is present
    'Sentada': 6,      # Customer physically at the beach
    'Cobrada': 5,      # Payment received
    'Check-in': 4,     # Customer arrived
    'Confirmada': 3,   # Confirmed reservation
    'Pendiente': 2,    # Pending confirmation
    'Completada': 1,   # Session completed
    'Cancelada': 0,    # Cancelled
    'No-Show': 0,      # No show
    'Liberada': 0      # Released/freed
}


# =============================================================================
# STATE QUERIES
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


# =============================================================================
# STATE TRANSITIONS
# =============================================================================

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


def cancel_beach_reservation(reservation_id: int, cancelled_by: str, notes: str = '') -> bool:
    """Shortcut to add 'Cancelada' state."""
    return add_reservation_state(reservation_id, 'Cancelada', cancelled_by, notes)


# =============================================================================
# COLOR CALCULATION
# =============================================================================

def calculate_reservation_color(current_states_str: str) -> str:
    """
    Calculate display color based on states.

    Priority rules:
    1. If has Cobrada -> Cobrada color
    2. If has Cancelada/No-Show -> respective color
    3. Else -> highest priority state color

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
        ''', (customer_id, f'No-Show automatico para reserva {reservation_id}', reservation_id, reported_by))


# =============================================================================
# CUSTOMER STATISTICS
# =============================================================================

def update_customer_statistics(customer_id: int) -> bool:
    """
    Update customer statistics based on reservations.

    Calculates:
    - total_visits: Reservations with 'Sentada' state
    - last_visit: Most recent visit date
    - no_shows: Count of reservations with No-Show state
    - cancellations: Count of reservations with Cancelada state
    - total_reservations: All reservations excluding cancelled/no-show

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

        # Count no-shows
        cursor.execute('''
            SELECT COUNT(*) as no_shows
            FROM beach_reservations
            WHERE customer_id = ?
              AND current_states LIKE '%No-Show%'
        ''', (customer_id,))
        no_shows = cursor.fetchone()['no_shows']

        # Count cancellations
        cursor.execute('''
            SELECT COUNT(*) as cancellations
            FROM beach_reservations
            WHERE customer_id = ?
              AND current_states LIKE '%Cancelada%'
        ''', (customer_id,))
        cancellations = cursor.fetchone()['cancellations']

        # Count total reservations (excluding cancelled and no-show)
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM beach_reservations
            WHERE customer_id = ?
              AND current_states NOT LIKE '%Cancelada%'
              AND current_states NOT LIKE '%No-Show%'
        ''', (customer_id,))
        total_reservations = cursor.fetchone()['total']

        # Update customer
        cursor.execute('''
            UPDATE beach_customers
            SET total_visits = ?,
                last_visit = ?,
                no_shows = ?,
                cancellations = ?,
                total_reservations = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (visits, last_visit, no_shows, cancellations, total_reservations, customer_id))

        db.commit()
        return True

    except Exception:
        db.rollback()
        return False


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
