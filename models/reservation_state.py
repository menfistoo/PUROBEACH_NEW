"""
Reservation state management functions.
Handles state transitions, history, and color calculations.

State properties are now fully configurable via the database.
Use models/state.py for state CRUD operations and property lookups.

State transition validation enforces valid workflow flows.
"""

from database import get_db
from models.state import (
    get_state_priority_map,
    get_default_state,
    get_state_by_name,
    get_incident_states,
)


# =============================================================================
# STATE TRANSITION VALIDATION
# =============================================================================

class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


# Valid state transitions matrix.
# Key: current state name -> Value: set of allowed target state names.
# None key represents initial state (new reservation with no prior state).
# Terminal states (Completada, Liberada) have no outgoing transitions.
# Cancelada and No-Show can reopen to Confirmada for corrections.
VALID_TRANSITIONS = {
    None: {'Confirmada', 'Cancelada'},
    '': {'Confirmada', 'Cancelada'},
    'Confirmada': {'Sentada', 'Cancelada', 'No-Show'},
    'Sentada': {'Completada', 'Cancelada', 'Liberada'},
    'Completada': set(),  # Terminal state
    'Cancelada': {'Confirmada'},  # Allow reopen
    'No-Show': {'Confirmada'},  # Allow reopen
    'Liberada': set(),  # Terminal state
}


def get_valid_transitions() -> dict:
    """
    Get the valid transitions matrix.

    Returns a copy so callers cannot modify the module-level constant.

    Returns:
        dict: {current_state_name: set of allowed target state names}
    """
    return {k: set(v) for k, v in VALID_TRANSITIONS.items()}


def get_allowed_transitions(current_state: str) -> set:
    """
    Get allowed target states for a given current state.

    Args:
        current_state: Current state name (or None/empty for new reservations)

    Returns:
        set: Allowed target state names, empty set if state is terminal
    """
    return set(VALID_TRANSITIONS.get(current_state, set()))


def validate_state_transition(current_state: str, new_state: str, bypass_validation: bool = False) -> None:
    """
    Validate that a state transition is allowed.

    Args:
        current_state: Current state name (or None/empty for new reservations)
        new_state: Target state name
        bypass_validation: If True, skip validation (for admin override)

    Raises:
        InvalidStateTransitionError: If transition is not allowed
    """
    if bypass_validation:
        return

    # Normalize empty/None current state
    normalized_current = current_state if current_state else None

    allowed = VALID_TRANSITIONS.get(normalized_current)

    # If current state is not in the matrix at all, allow any transition
    # (handles custom/user-created states that aren't in the matrix)
    if allowed is None:
        return

    if new_state not in allowed:
        current_display = current_state or 'Sin estado'
        if not allowed:
            raise InvalidStateTransitionError(
                f'No se puede cambiar de "{current_display}" a "{new_state}". '
                f'"{current_display}" es un estado terminal sin transiciones permitidas.'
            )
        allowed_list = ', '.join(sorted(allowed))
        raise InvalidStateTransitionError(
            f'No se puede cambiar de "{current_display}" a "{new_state}". '
            f'Transiciones permitidas desde "{current_display}": {allowed_list}'
        )


# =============================================================================
# STATE QUERIES
# =============================================================================

def get_reservation_states() -> list:
    """
    Get all reservation states.

    Returns:
        List of state dicts ordered by display_order
    """
    with get_db() as conn:
        cursor = conn.cursor()
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM beach_reservation_states
            WHERE is_availability_releasing = 1 AND active = 1
        ''')
        return [row['name'] for row in cursor.fetchall()]


# =============================================================================
# STATE TRANSITIONS
# =============================================================================

def add_reservation_state(reservation_id: int, state_type: str, changed_by: str,
                          notes: str = '', bypass_validation: bool = False) -> bool:
    """
    Add state to reservation (accumulative CSV).

    Behavior:
    1. Validates state transition
    2. Adds to current_states CSV
    3. Updates current_state to new state
    4. Records in history
    5. If No-Show: creates automatic incident
    6. Updates customer statistics

    Args:
        reservation_id: Reservation ID
        state_type: State name to add
        changed_by: Username making change
        notes: Optional notes
        bypass_validation: If True, skip transition validation (admin override)

    Returns:
        bool: Success status

    Raises:
        InvalidStateTransitionError: If transition is not allowed
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Get current reservation data
            cursor.execute('SELECT customer_id, current_states, current_state FROM beach_reservations WHERE id = ?',
                          (reservation_id,))
            row = cursor.fetchone()
            if not row:
                return False

            customer_id = row['customer_id']
            current_states = row['current_states'] or ''
            old_state_name = row['current_state']

            # Validate state transition
            validate_state_transition(old_state_name, state_type, bypass_validation)

            # Add to CSV (avoid duplicates)
            states_list = [s.strip() for s in current_states.split(',') if s.strip()]
            if state_type not in states_list:
                states_list.append(state_type)

            new_states_csv = ', '.join(states_list)

            # Get state IDs for history and state_id sync
            old_state_id = None
            if old_state_name:
                old_state = get_state_by_name(old_state_name)
                old_state_id = old_state['id'] if old_state else None

            new_state = get_state_by_name(state_type)
            new_state_id = new_state['id'] if new_state else None

            # Update reservation - sync BOTH current_state AND state_id
            cursor.execute('''
                UPDATE beach_reservations
                SET current_states = ?,
                    current_state = ?,
                    state_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_states_csv, state_type, new_state_id, reservation_id))

            if new_state_id:
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, old_state_id, new_state_id, changed_by, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (reservation_id, old_state_id, new_state_id, changed_by, notes or 'Estado añadido'))

            # Auto-create incident for states with creates_incident=1
            state_info = get_state_by_name(state_type)
            if state_info and state_info.get('creates_incident'):
                _create_state_incident(cursor, customer_id, reservation_id, changed_by, state_type)

            conn.commit()

            # Update customer statistics
            update_customer_statistics(customer_id)

            return True

        except Exception as e:
            conn.rollback()
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
    with get_db() as conn:
        cursor = conn.cursor()

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

            # Get state IDs for history and state_id sync
            removed_state = get_state_by_name(state_type)
            removed_state_id = removed_state['id'] if removed_state else None

            new_state_id = None
            if new_current_state:
                new_state = get_state_by_name(new_current_state)
                new_state_id = new_state['id'] if new_state else None

            # Update reservation - sync BOTH current_state AND state_id
            cursor.execute('''
                UPDATE beach_reservations
                SET current_states = ?,
                    current_state = ?,
                    state_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_states_csv, new_current_state, new_state_id, reservation_id))

            if removed_state_id:
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, old_state_id, new_state_id, changed_by, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (reservation_id, removed_state_id, new_state_id, changed_by, notes or 'Estado eliminado'))

            conn.commit()

            # Update customer statistics
            update_customer_statistics(customer_id)

            return True

        except Exception as e:
            conn.rollback()
            raise


def change_reservation_state(reservation_id: int, new_state: str, changed_by: str,
                             reason: str = '', bypass_validation: bool = False) -> bool:
    """
    Change reservation state (replaces current state).
    For single-state changes, use add_reservation_state for multi-state.

    Args:
        reservation_id: Reservation ID
        new_state: New state name
        changed_by: Username
        reason: Change reason
        bypass_validation: If True, skip transition validation (admin override)

    Returns:
        bool: Success status

    Raises:
        InvalidStateTransitionError: If transition is not allowed
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Get current state
            cursor.execute('SELECT current_state, customer_id FROM beach_reservations WHERE id = ?',
                          (reservation_id,))
            row = cursor.fetchone()
            if not row:
                return False

            old_state = row['current_state']
            customer_id = row['customer_id']

            # Validate state transition
            validate_state_transition(old_state, new_state, bypass_validation)

            # Update to new state
            cursor.execute('''
                UPDATE beach_reservations
                SET current_state = ?,
                    current_states = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_state, new_state, reservation_id))

            # Record history - get state IDs
            old_state_id = None
            if old_state:
                old_state_obj = get_state_by_name(old_state)
                old_state_id = old_state_obj['id'] if old_state_obj else None

            new_state_obj = get_state_by_name(new_state)
            new_state_id = new_state_obj['id'] if new_state_obj else None

            if new_state_id:
                reason_text = f'Cambio de {old_state} a {new_state}. {reason}' if reason else f'Cambio de {old_state} a {new_state}'
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, old_state_id, new_state_id, changed_by, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (reservation_id, old_state_id, new_state_id, changed_by, reason_text))

            conn.commit()

            # Update customer stats
            update_customer_statistics(customer_id)

            return True

        except Exception:
            conn.rollback()
            raise


def cancel_beach_reservation(reservation_id: int, cancelled_by: str, notes: str = '',
                              bypass_validation: bool = False) -> bool:
    """Shortcut to add 'Cancelada' state."""
    return add_reservation_state(reservation_id, 'Cancelada', cancelled_by, notes,
                                  bypass_validation=bypass_validation)


# =============================================================================
# COLOR CALCULATION
# =============================================================================

def calculate_reservation_color(current_states_str: str) -> str:
    """
    Calculate display color based on states using database priorities.

    Uses display_priority from beach_reservation_states table.
    Higher priority states determine the displayed color.

    Args:
        current_states_str: CSV of states

    Returns:
        str: Hex color code
    """
    states_list = [s.strip() for s in current_states_str.split(',') if s.strip()]

    if not states_list:
        return '#CCCCCC'  # Default

    # Get priority map from database
    priority_map = get_state_priority_map()

    # Find highest priority state
    top_state = max(states_list, key=lambda s: priority_map.get(s, 0))
    return _get_state_color(top_state)


def _get_highest_priority_state(states_list: list) -> str:
    """Get state with highest display priority from list."""
    if not states_list:
        default = get_default_state()
        return default.get('name', 'Confirmada')

    priority_map = get_state_priority_map()
    return max(states_list, key=lambda s: priority_map.get(s, 0))


def _get_state_color(state_name: str) -> str:
    """Get color for state name from database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT color FROM beach_reservation_states WHERE name = ?', (state_name,))
        row = cursor.fetchone()
        return row['color'] if row else '#CCCCCC'


def _create_state_incident(cursor, customer_id: int, reservation_id: int, reported_by: str, state_type: str) -> None:
    """Create automatic incident for states with creates_incident=1."""
    # Check if beach_customer_incidents table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='beach_customer_incidents'")
    if cursor.fetchone():
        incident_type = state_type.lower().replace('-', '_').replace(' ', '_')
        cursor.execute('''
            INSERT INTO beach_customer_incidents
            (customer_id, description, incident_type, reservation_id, reported_by, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (customer_id, f'{state_type} automatico para reserva {reservation_id}',
              incident_type, reservation_id, reported_by))


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
    with get_db() as conn:
        cursor = conn.cursor()

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

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            return False


def get_status_history(reservation_id: int) -> list:
    """
    Get state change history for reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        list: History entries ordered by date desc
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM reservation_status_history
            WHERE reservation_id = ?
            ORDER BY created_at DESC
        ''', (reservation_id,))
        return [dict(r) for r in cursor.fetchall()]
