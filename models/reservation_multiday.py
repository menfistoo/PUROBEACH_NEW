"""
Multi-day (linked) reservation management.
Handles creation, update, and cancellation of parent/child reservation groups.

Phase 6B - Module 2
"""

from database import get_db
from .reservation_crud import (
    generate_reservation_number,
    generate_child_reservation_number,
    sync_preferences_to_customer
)
from .reservation_state import (
    add_reservation_state,
    get_active_releasing_states,
    update_customer_statistics
)
from .reservation_availability import (
    check_furniture_availability_bulk,
    check_duplicate_reservation
)


# =============================================================================
# MULTI-DAY RESERVATION CREATION
# =============================================================================

def create_linked_multiday_reservations(
    customer_id: int,
    dates: list,
    num_people: int,
    furniture_ids: list = None,
    furniture_by_date: dict = None,
    time_slot: str = 'all_day',
    payment_status: str = 'NO',
    charge_to_room: int = 0,
    charge_reference: str = '',
    price: float = 0.0,
    preferences: str = '',
    observations: str = '',
    created_by: str = None,
    check_in_date: str = None,
    check_out_date: str = None,
    hamaca_included: int = 1,
    validate_availability: bool = True,
    validate_duplicates: bool = True
) -> dict:
    """
    Create linked reservations for multiple consecutive days.

    Strategy:
    - First date → parent reservation (normal ticket YYMMDDRR)
    - Following dates → child reservations (ticket YYMMDDRR-1, YYMMDDRR-2, ...)
    - All linked via parent_reservation_id

    Args:
        customer_id: Customer ID
        dates: List of dates ['2025-01-16', '2025-01-17', ...]
        num_people: Number of people (same for all days)
        furniture_ids: Same furniture for all days (list of IDs)
        furniture_by_date: Different furniture per day {date: [furniture_ids]}
        time_slot: 'all_day', 'morning', 'afternoon'
        payment_status: 'SI' or 'NO'
        charge_to_room: 1 to charge to room
        charge_reference: Reference for room charge
        price: Base price per day
        preferences: CSV of preference codes
        observations: Notes
        created_by: Username creating reservation
        check_in_date: Hotel check-in date
        check_out_date: Hotel check-out date
        hamaca_included: 1 if included free
        validate_availability: Check furniture availability (default True)
        validate_duplicates: Check for duplicate reservations (default True)

    Returns:
        dict: {
            'success': bool,
            'parent_id': int,
            'parent_ticket': str,
            'children': [{'id': int, 'ticket': str, 'date': str}],
            'total_created': int,
            'error': str or None
        }

    Raises:
        ValueError: If validation fails
    """
    if not dates:
        raise ValueError('Se requiere al menos una fecha')

    if not customer_id:
        raise ValueError('Se requiere customer_id')

    # Sort dates to ensure correct order
    dates = sorted(dates)

    # Determine furniture for each date
    if furniture_by_date:
        # Different furniture per day
        all_furniture_ids = set()
        for date_furniture in furniture_by_date.values():
            all_furniture_ids.update(date_furniture)
        all_furniture_ids = list(all_furniture_ids)
    elif furniture_ids:
        # Same furniture for all days
        all_furniture_ids = furniture_ids
        furniture_by_date = {d: furniture_ids for d in dates}
    else:
        raise ValueError('Se requiere furniture_ids o furniture_by_date')

    # Validate availability
    if validate_availability:
        avail_result = check_furniture_availability_bulk(all_furniture_ids, dates)
        if not avail_result['all_available']:
            unavail = avail_result['unavailable'][0]
            raise ValueError(
                f"Mobiliario {unavail['furniture_id']} no disponible el {unavail['date']} "
                f"(reserva {unavail['ticket_number']})"
            )

    # Check for duplicates
    if validate_duplicates:
        is_dup, existing = check_duplicate_reservation(customer_id, dates)
        if is_dup:
            raise ValueError(
                f"Ya existe una reserva para este cliente el {existing['date']} "
                f"(ticket {existing['ticket_number']})"
            )

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('BEGIN IMMEDIATE')

        parent_id = None
        parent_ticket = None
        children = []

        for i, date in enumerate(dates):
            date_furniture = furniture_by_date.get(date, furniture_ids)

            if i == 0:
                # First date: create parent reservation
                ticket_number = generate_reservation_number(date, cursor)

                cursor.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, ticket_number, reservation_date, start_date, end_date,
                        num_people, time_slot, current_states, current_state,
                        payment_status, price, charge_to_room, charge_reference,
                        hamaca_included, preferences, notes,
                        check_in_date, check_out_date,
                        parent_reservation_id, reservation_type, created_by, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, 'Confirmada', 'Confirmada',
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        NULL, 'normal', ?, CURRENT_TIMESTAMP
                    )
                ''', (
                    customer_id, ticket_number, date, dates[0], dates[-1],
                    num_people, time_slot,
                    payment_status, price, charge_to_room, charge_reference,
                    hamaca_included, preferences, observations,
                    check_in_date, check_out_date,
                    created_by
                ))

                parent_id = cursor.lastrowid
                parent_ticket = ticket_number

                # Record initial state
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, status_type, action, changed_by, notes, created_at)
                    VALUES (?, 'Confirmada', 'added', ?, 'Creacion de reserva multi-dia (parent)', CURRENT_TIMESTAMP)
                ''', (parent_id, created_by))

            else:
                # Following dates: create child reservations
                child_ticket = generate_child_reservation_number(parent_ticket, i)

                cursor.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, ticket_number, reservation_date, start_date, end_date,
                        num_people, time_slot, current_states, current_state,
                        payment_status, price, charge_to_room, charge_reference,
                        hamaca_included, preferences, notes,
                        check_in_date, check_out_date,
                        parent_reservation_id, reservation_type, created_by, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, 'Confirmada', 'Confirmada',
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, 'normal', ?, CURRENT_TIMESTAMP
                    )
                ''', (
                    customer_id, child_ticket, date, dates[0], dates[-1],
                    num_people, time_slot,
                    payment_status, price, charge_to_room, charge_reference,
                    hamaca_included, preferences, observations,
                    check_in_date, check_out_date,
                    parent_id, created_by
                ))

                child_id = cursor.lastrowid

                # Record initial state
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, status_type, action, changed_by, notes, created_at)
                    VALUES (?, 'Confirmada', 'added', ?, 'Creacion de reserva multi-dia (child)', CURRENT_TIMESTAMP)
                ''', (child_id, created_by))

                children.append({
                    'id': child_id,
                    'ticket': child_ticket,
                    'date': date
                })

            # Assign furniture for this date
            reservation_id = parent_id if i == 0 else child_id
            for furn_id in date_furniture:
                cursor.execute('''
                    INSERT INTO beach_reservation_furniture
                    (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, ?)
                ''', (reservation_id, furn_id, date))

        db.commit()

        # Sync preferences to customer profile
        if preferences:
            sync_preferences_to_customer(customer_id, preferences)

        return {
            'success': True,
            'parent_id': parent_id,
            'parent_ticket': parent_ticket,
            'children': children,
            'total_created': 1 + len(children),
            'error': None
        }

    except Exception as e:
        db.rollback()
        raise


# =============================================================================
# MULTI-DAY RESERVATION UPDATE
# =============================================================================

def update_multiday_reservations(
    parent_id: int,
    update_children: bool = True,
    **fields
) -> dict:
    """
    Update common fields across all linked reservations.

    Args:
        parent_id: Parent reservation ID
        update_children: Also update child reservations (default True)
        **fields: Fields to update (num_people, time_slot, preferences, etc.)

    Returns:
        dict: {
            'success': bool,
            'updated_count': int,
            'updated_ids': [int]
        }
    """
    db = get_db()
    cursor = db.cursor()

    # Allowed fields for bulk update
    allowed_fields = [
        'num_people', 'time_slot', 'payment_status', 'price',
        'charge_to_room', 'charge_reference', 'hamaca_included',
        'preferences', 'notes', 'check_in_date', 'check_out_date'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in fields:
            updates.append(f'{field} = ?')
            values.append(fields[field])

    if not updates:
        return {'success': True, 'updated_count': 0, 'updated_ids': []}

    updates.append('updated_at = CURRENT_TIMESTAMP')

    try:
        updated_ids = []

        # Update parent
        query = f'UPDATE beach_reservations SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, values + [parent_id])
        if cursor.rowcount > 0:
            updated_ids.append(parent_id)

        # Update children if requested
        if update_children:
            query = f'UPDATE beach_reservations SET {", ".join(updates)} WHERE parent_reservation_id = ?'
            cursor.execute(query, values + [parent_id])

            # Get child IDs
            cursor.execute(
                'SELECT id FROM beach_reservations WHERE parent_reservation_id = ?',
                (parent_id,)
            )
            for row in cursor.fetchall():
                updated_ids.append(row['id'])

        db.commit()

        # Sync preferences if updated
        if 'preferences' in fields:
            cursor.execute('SELECT customer_id FROM beach_reservations WHERE id = ?', (parent_id,))
            row = cursor.fetchone()
            if row:
                sync_preferences_to_customer(row['customer_id'], fields['preferences'])

        return {
            'success': True,
            'updated_count': len(updated_ids),
            'updated_ids': updated_ids
        }

    except Exception as e:
        db.rollback()
        raise


# =============================================================================
# MULTI-DAY RESERVATION CANCELLATION
# =============================================================================

def cancel_multiday_reservations(
    parent_id: int,
    cancelled_by: str,
    notes: str = '',
    cancel_children: bool = True
) -> dict:
    """
    Cancel all linked reservations in a multi-day group.

    Args:
        parent_id: Parent reservation ID
        cancelled_by: Username making cancellation
        notes: Cancellation reason
        cancel_children: Also cancel child reservations (default True)

    Returns:
        dict: {
            'success': bool,
            'cancelled_count': int,
            'cancelled_ids': [int]
        }
    """
    db = get_db()
    cursor = db.cursor()

    try:
        cancelled_ids = []

        # Get all reservation IDs in the group
        cursor.execute('''
            SELECT id FROM beach_reservations
            WHERE id = ? OR parent_reservation_id = ?
            ORDER BY reservation_date
        ''', (parent_id, parent_id))

        reservation_ids = [row['id'] for row in cursor.fetchall()]

        if not cancel_children:
            reservation_ids = [parent_id]

        # Cancel each reservation
        for res_id in reservation_ids:
            # Update state
            cursor.execute('''
                UPDATE beach_reservations
                SET current_state = 'Cancelada',
                    current_states = CASE
                        WHEN current_states = '' THEN 'Cancelada'
                        ELSE current_states || ', Cancelada'
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (res_id,))

            # Record in history
            cursor.execute('''
                INSERT INTO reservation_status_history
                (reservation_id, status_type, action, changed_by, notes, created_at)
                VALUES (?, 'Cancelada', 'added', ?, ?, CURRENT_TIMESTAMP)
            ''', (res_id, cancelled_by, notes or 'Cancelacion de reserva multi-dia'))

            cancelled_ids.append(res_id)

        db.commit()

        # Update customer statistics
        cursor.execute('SELECT customer_id FROM beach_reservations WHERE id = ?', (parent_id,))
        row = cursor.fetchone()
        if row:
            update_customer_statistics(row['customer_id'])

        return {
            'success': True,
            'cancelled_count': len(cancelled_ids),
            'cancelled_ids': cancelled_ids
        }

    except Exception as e:
        db.rollback()
        raise


# =============================================================================
# MULTI-DAY RESERVATION QUERIES
# =============================================================================

def get_multiday_summary(reservation_id: int) -> dict:
    """
    Get summary of a multi-day reservation group.

    Args:
        reservation_id: Any reservation ID in the group (parent or child)

    Returns:
        dict: {
            'is_multiday': bool,
            'is_parent': bool,
            'parent_id': int,
            'parent_ticket': str,
            'total_days': int,
            'date_range': {'start': str, 'end': str},
            'reservations': [
                {'id': int, 'ticket': str, 'date': str, 'state': str, 'furniture': [str]}
            ],
            'customer_id': int,
            'customer_name': str
        }
    """
    db = get_db()
    cursor = db.cursor()

    # Get the reservation
    cursor.execute('''
        SELECT r.*, c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE r.id = ?
    ''', (reservation_id,))

    row = cursor.fetchone()
    if not row:
        return None

    # Determine parent ID
    if row['parent_reservation_id']:
        parent_id = row['parent_reservation_id']
        is_parent = False
    else:
        parent_id = reservation_id
        is_parent = True

    # Get all reservations in the group
    cursor.execute('''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state,
               GROUP_CONCAT(f.number, ', ') as furniture_numbers
        FROM beach_reservations r
        LEFT JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
        LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
        WHERE r.id = ? OR r.parent_reservation_id = ?
        GROUP BY r.id
        ORDER BY r.reservation_date
    ''', (parent_id, parent_id))

    reservations = []
    dates = []
    parent_ticket = None

    for res_row in cursor.fetchall():
        reservations.append({
            'id': res_row['id'],
            'ticket': res_row['ticket_number'],
            'date': res_row['reservation_date'],
            'state': res_row['current_state'],
            'furniture': res_row['furniture_numbers'].split(', ') if res_row['furniture_numbers'] else []
        })
        dates.append(res_row['reservation_date'])

        if res_row['id'] == parent_id:
            parent_ticket = res_row['ticket_number']

    is_multiday = len(reservations) > 1

    return {
        'is_multiday': is_multiday,
        'is_parent': is_parent,
        'parent_id': parent_id,
        'parent_ticket': parent_ticket,
        'total_days': len(reservations),
        'date_range': {
            'start': min(dates) if dates else None,
            'end': max(dates) if dates else None
        },
        'reservations': reservations,
        'customer_id': row['customer_id'],
        'customer_name': row['customer_name']
    }


def is_parent_reservation(reservation_id: int) -> bool:
    """
    Check if a reservation is a parent (has children).

    Args:
        reservation_id: Reservation ID to check

    Returns:
        bool: True if parent, False otherwise
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT COUNT(*) as child_count
        FROM beach_reservations
        WHERE parent_reservation_id = ?
    ''', (reservation_id,))

    return cursor.fetchone()['child_count'] > 0


def get_child_reservations(parent_id: int) -> list:
    """
    Get all child reservations of a parent.

    Args:
        parent_id: Parent reservation ID

    Returns:
        list: Child reservations
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT r.*, GROUP_CONCAT(f.number, ', ') as furniture_numbers
        FROM beach_reservations r
        LEFT JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
        LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
        WHERE r.parent_reservation_id = ?
        GROUP BY r.id
        ORDER BY r.reservation_date
    ''', (parent_id,))

    return [dict(row) for row in cursor.fetchall()]
