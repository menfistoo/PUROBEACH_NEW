"""
Beach reservation state data access functions.

Handles state CRUD operations for configuration UI.
Provides dynamic lookup functions for state properties.
"""

from database import get_db


def get_all_states(active_only: bool = True) -> list:
    """
    Get all reservation states.

    Args:
        active_only: If True, return only active states

    Returns:
        List of state dictionaries ordered by display_order
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT s.*,
                   (SELECT COUNT(*) FROM beach_reservations
                    WHERE current_state = s.name) as usage_count
            FROM beach_reservation_states s
        '''

        if active_only:
            query += ' WHERE s.active = 1'

        query += ' ORDER BY s.display_order'

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def get_state_by_id(state_id: int) -> dict:
    """
    Get state by ID.

    Args:
        state_id: State ID

    Returns:
        State dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_reservation_states WHERE id = ?', (state_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_state_by_code(code: str) -> dict:
    """
    Get state by code.

    Args:
        code: State code (e.g., 'confirmada', 'cancelada')

    Returns:
        State dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_reservation_states WHERE code = ?', (code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_state_by_name(name: str) -> dict:
    """
    Get state by display name.

    Args:
        name: State display name (e.g., 'Confirmada', 'Cancelada')

    Returns:
        State dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_reservation_states WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_default_state() -> dict:
    """
    Get the default state for new reservations.

    Returns:
        State record with is_default=1, or first active state as fallback
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM beach_reservation_states
            WHERE is_default = 1 AND active = 1
            LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Fallback: first active state
        cursor.execute('''
            SELECT * FROM beach_reservation_states
            WHERE active = 1
            ORDER BY display_order
            LIMIT 1
        ''')
        row = cursor.fetchone()
        return dict(row) if row else {'name': 'Confirmada', 'code': 'confirmada'}


def get_state_priority_map() -> dict:
    """
    Get display priority mapping for all active states.

    Returns:
        dict: {state_name: priority} mapping
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, display_priority
            FROM beach_reservation_states
            WHERE active = 1
        ''')
        return {row['name']: row['display_priority'] for row in cursor.fetchall()}


def get_incident_states() -> list:
    """
    Get states that trigger automatic incident creation.

    Returns:
        List of state names with creates_incident=1
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM beach_reservation_states
            WHERE creates_incident = 1 AND active = 1
        ''')
        return [row['name'] for row in cursor.fetchall()]


def get_releasing_states() -> list:
    """
    Get states that release furniture availability.

    Returns:
        List of state names with is_availability_releasing=1
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM beach_reservation_states
            WHERE is_availability_releasing = 1 AND active = 1
        ''')
        return [row['name'] for row in cursor.fetchall()]


def create_state(
    code: str,
    name: str,
    color: str = '#6C757D',
    icon: str = None,
    is_availability_releasing: int = 0,
    display_priority: int = 0,
    creates_incident: int = 0
) -> int:
    """
    Create new reservation state.

    Args:
        code: Unique state code (lowercase, no spaces)
        name: Display name (Spanish)
        color: Hex color code
        icon: FontAwesome icon class
        is_availability_releasing: 1 if state frees furniture
        display_priority: Priority for color display
        creates_incident: 1 if state creates automatic incident

    Returns:
        New state ID

    Raises:
        ValueError: If code already exists
    """
    # Check uniqueness
    existing = get_state_by_code(code)
    if existing:
        raise ValueError(f'Ya existe un estado con el codigo "{code}"')

    with get_db() as conn:
        cursor = conn.cursor()

        # Get next display_order
        cursor.execute('SELECT MAX(display_order) as max_order FROM beach_reservation_states')
        row = cursor.fetchone()
        next_order = (row['max_order'] or 0) + 1

        cursor.execute('''
            INSERT INTO beach_reservation_states
            (code, name, color, icon, is_availability_releasing, display_order,
             display_priority, creates_incident, is_system, is_default, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 1)
        ''', (code, name, color, icon, is_availability_releasing, next_order,
              display_priority, creates_incident))

        conn.commit()
        return cursor.lastrowid


def update_state(state_id: int, **kwargs) -> bool:
    """
    Update state fields.

    System states (is_system=1) cannot have code or is_system changed.

    Args:
        state_id: State ID to update
        **kwargs: Fields to update

    Returns:
        True if updated, False if no changes
    """
    # Check if system state
    state = get_state_by_id(state_id)
    if not state:
        return False

    if state['is_system']:
        # Remove protected fields for system states
        kwargs.pop('code', None)
        kwargs.pop('is_system', None)

    allowed_fields = [
        'name', 'color', 'icon', 'is_availability_releasing',
        'display_order', 'display_priority', 'creates_incident',
        'is_default', 'active'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    with get_db() as conn:
        cursor = conn.cursor()

        # If setting is_default=1, clear other defaults
        if kwargs.get('is_default') == 1:
            cursor.execute('UPDATE beach_reservation_states SET is_default = 0')

        values.append(state_id)
        query = f'UPDATE beach_reservation_states SET {", ".join(updates)} WHERE id = ?'

        cursor.execute(query, values)
        conn.commit()

        return cursor.rowcount > 0


def delete_state(state_id: int) -> bool:
    """
    Soft delete state (set active=0).

    System states cannot be deleted.

    Args:
        state_id: State ID to delete

    Returns:
        True if deleted, False otherwise

    Raises:
        ValueError: If state is a system state
    """
    # Check if system state
    state = get_state_by_id(state_id)
    if not state:
        return False

    if state['is_system']:
        raise ValueError('No se pueden eliminar estados del sistema')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE beach_reservation_states SET active = 0 WHERE id = ?', (state_id,))
        conn.commit()

        return cursor.rowcount > 0


def reorder_states(state_ids: list) -> bool:
    """
    Reorder states based on provided ID list.

    Args:
        state_ids: List of state IDs in desired order

    Returns:
        True if successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            for order, state_id in enumerate(state_ids, start=1):
                cursor.execute('''
                    UPDATE beach_reservation_states
                    SET display_order = ?
                    WHERE id = ?
                ''', (order, state_id))

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            return False
