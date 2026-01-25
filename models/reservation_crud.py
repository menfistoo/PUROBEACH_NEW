"""
Reservation CRUD operations.
Handles create, read, update, delete for reservations.

Phase 6B - Module 4 (Main CRUD with re-exports from specialized modules)
"""

from database import get_db
from datetime import datetime
from .reservation_state import calculate_reservation_color, update_customer_statistics
from .state import get_default_state
from .reservation_availability import check_furniture_availability_bulk

# Re-export preference sync functions for backward compatibility
from .characteristic_assignments import (
    sync_preferences_to_customer,
    get_customer_preference_codes,
    sync_customer_preferences_to_reservations
)


# =============================================================================
# TICKET NUMBER GENERATION
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

    with get_db() as conn:
        cur = cursor or conn.cursor()

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
                raise ValueError(f"Maximo de reservas diarias (99) alcanzado para {reservation_date}")

            ticket_number = f"{date_prefix}{next_seq:02d}"

            # Verify uniqueness
            cur.execute('SELECT id FROM beach_reservations WHERE ticket_number = ?', (ticket_number,))
            if not cur.fetchone():
                return ticket_number

        raise ValueError("No se pudo generar numero unico despues de varios intentos")


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
# CREATE
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
    reservation_type: str = 'normal',
    package_id: int = None,
    payment_ticket_number: str = None,
    payment_method: str = None
) -> tuple:
    """
    Create a complete reservation with all validations.

    Args:
        customer_id: Customer ID
        reservation_date: Reservation date (YYYY-MM-DD)
        num_people: Number of people
        furniture_ids: List of furniture IDs to assign
        time_slot: 'all_day', 'morning', or 'afternoon'
        payment_status: 'SI' or 'NO'
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
        package_id: Selected package ID
        payment_ticket_number: PMS/POS payment ticket number
        payment_method: Payment method (efectivo, tarjeta, cargo_habitacion)

    Returns:
        tuple: (reservation_id, ticket_number)

    Raises:
        ValueError: If validations fail
    """
    # Payment ticket and method are optional (for auditing purposes)

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute('BEGIN IMMEDIATE')

            # Generate ticket number if not provided
            if not ticket_number:
                ticket_number = generate_reservation_number(reservation_date, cursor)

            # Get default state from database
            default_state = get_default_state()
            initial_state = default_state.get('name', 'Confirmada')

            # Get customer's current room for original_room tracking
            cursor.execute('''
                SELECT room_number, customer_type FROM beach_customers WHERE id = ?
            ''', (customer_id,))
            customer_row = cursor.fetchone()
            original_room = None
            if customer_row and customer_row['customer_type'] == 'interno':
                original_room = customer_row['room_number']

            # Insert reservation (state_id=1 is "Confirmada" by default)
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, time_slot, current_states, current_state, state_id,
                    payment_status, price, final_price, hamaca_included, price_catalog_id, paid,
                    charge_to_room, charge_reference,
                    minimum_consumption_amount, minimum_consumption_policy_id,
                    package_id, payment_ticket_number, payment_method,
                    check_in_date, check_out_date, preferences, notes,
                    parent_reservation_id, reservation_type, created_by, created_at,
                    original_room
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 1,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, CURRENT_TIMESTAMP,
                    ?
                )
            ''', (
                customer_id, ticket_number, reservation_date, reservation_date, reservation_date,
                num_people, time_slot, initial_state, initial_state,
                payment_status, price, final_price, hamaca_included, price_catalog_id, paid,
                charge_to_room, charge_reference,
                minimum_consumption_amount, minimum_consumption_policy_id,
                package_id, payment_ticket_number, payment_method,
                check_in_date, check_out_date, preferences, observations,
                parent_reservation_id, reservation_type, created_by,
                original_room
            ))

            reservation_id = cursor.lastrowid

            # Assign furniture (with availability check)
            if furniture_ids:
                # Check furniture availability before assigning
                availability = check_furniture_availability_bulk(
                    furniture_ids=furniture_ids,
                    dates=[reservation_date],
                    exclude_reservation_id=None
                )
                if availability.get('conflicts'):
                    conflict_ids = list(availability['conflicts'].keys())
                    conn.rollback()
                    raise ValueError(f"Mobiliario no disponible: {conflict_ids}")

                for furniture_id in furniture_ids:
                    cursor.execute('''
                        INSERT INTO beach_reservation_furniture
                        (reservation_id, furniture_id, assignment_date)
                        VALUES (?, ?, ?)
                    ''', (reservation_id, furniture_id, reservation_date))

            # Record initial state in history
            state_id = default_state.get('id')
            if state_id:
                cursor.execute('''
                    INSERT INTO reservation_status_history
                    (reservation_id, old_state_id, new_state_id, changed_by, reason, created_at)
                    VALUES (?, NULL, ?, ?, 'Creacion de reserva', CURRENT_TIMESTAMP)
                ''', (reservation_id, state_id, created_by))

            conn.commit()

            # Sync preferences to reservation characteristics junction table
            if preferences:
                from models.characteristic_assignments import sync_preferences_to_reservation
                sync_preferences_to_reservation(reservation_id, preferences)

            # Sync preferences to customer profile
            if preferences:
                sync_preferences_to_customer(customer_id, preferences)

            return reservation_id, ticket_number

        except Exception as e:
            conn.rollback()
            raise


# =============================================================================
# READ
# =============================================================================

def get_beach_reservation_by_id(reservation_id: int) -> dict:
    """
    Get reservation by ID with all related data.

    Args:
        reservation_id: Reservation ID

    Returns:
        dict: Reservation with customer, state, and furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT r.*,
                   c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                   c.customer_type,
                   c.room_number as customer_room,
                   c.email as customer_email,
                   c.phone as customer_phone,
                   pkg.package_name,
                   pkg.package_description,
                   mcp.policy_name as minimum_consumption_policy_name,
                   CASE WHEN r.original_room IS NOT NULL
                        AND r.original_room != c.room_number
                        THEN 1 ELSE 0 END as room_changed
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            LEFT JOIN beach_packages pkg ON r.package_id = pkg.id
            LEFT JOIN beach_minimum_consumption_policies mcp ON r.minimum_consumption_policy_id = mcp.id
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM beach_reservations WHERE ticket_number = ?', (ticket_number,))
        row = cursor.fetchone()
        if row:
            return get_beach_reservation_by_id(row['id'])
        return None


def get_reservation_with_details(reservation_id: int) -> dict:
    """Alias for get_beach_reservation_by_id."""
    return get_beach_reservation_by_id(reservation_id)


def get_reservation_by_id(reservation_id: int) -> dict:
    """Alias for get_beach_reservation_by_id."""
    return get_beach_reservation_by_id(reservation_id)


# =============================================================================
# UPDATE
# =============================================================================

def update_beach_reservation(reservation_id: int, **kwargs) -> bool:
    """
    Update reservation fields.

    Args:
        reservation_id: Reservation ID
        **kwargs: Fields to update

    Returns:
        bool: Success status
    """
    with get_db() as conn:
        cursor = conn.cursor()

        allowed_fields = [
            'reservation_date', 'num_people', 'time_slot',
            'payment_status', 'price', 'final_price', 'hamaca_included',
            'price_catalog_id', 'paid', 'charge_to_room', 'charge_reference',
            'minimum_consumption_amount', 'minimum_consumption_policy_id',
            'package_id', 'payment_ticket_number', 'payment_method',
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
        conn.commit()

        return cursor.rowcount > 0


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
    with get_db() as conn:
        cursor = conn.cursor()

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

            # Check furniture availability (excluding current reservation)
            availability = check_furniture_availability_bulk(
                furniture_ids=furniture_ids,
                dates=[res_date],
                exclude_reservation_id=reservation_id
            )
            if availability.get('conflicts'):
                conflict_ids = list(availability['conflicts'].keys())
                raise ValueError(f"Mobiliario no disponible: {conflict_ids}")

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

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            raise


# =============================================================================
# DELETE
# =============================================================================

def delete_reservation(reservation_id: int) -> bool:
    """
    Delete reservation and all related records.

    Manually deletes from tables without CASCADE:
    - reservation_status_history

    Tables with CASCADE (auto-deleted):
    - beach_reservation_furniture
    - beach_reservation_daily_states
    - beach_reservation_tags

    Args:
        reservation_id: Reservation ID

    Returns:
        bool: Success status
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Delete from tables without CASCADE
            cursor.execute('DELETE FROM reservation_status_history WHERE reservation_id = ?',
                          (reservation_id,))

            # Delete reservation (CASCADE handles the rest)
            cursor.execute('DELETE FROM beach_reservations WHERE id = ?', (reservation_id,))

            conn.commit()
            return cursor.rowcount > 0

        except Exception:
            conn.rollback()
            raise


# =============================================================================
# COMPATIBILITY WRAPPERS
# =============================================================================

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


# =============================================================================
# FURNITURE LOCK
# =============================================================================

def toggle_furniture_lock(reservation_id: int, locked: bool) -> dict:
    """
    Toggle the furniture lock status for a reservation.

    Args:
        reservation_id: The reservation ID
        locked: True to lock, False to unlock

    Returns:
        Dict with success status and new lock state
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check reservation exists
        cursor.execute(
            "SELECT id FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        if not cursor.fetchone():
            return {
                'success': False,
                'error': 'Reserva no encontrada'
            }

        # Update lock status
        cursor.execute(
            "UPDATE beach_reservations SET is_furniture_locked = ? WHERE id = ?",
            (1 if locked else 0, reservation_id)
        )
        conn.commit()

        return {
            'success': True,
            'is_furniture_locked': locked,
            'reservation_id': reservation_id
        }


def is_furniture_locked(reservation_id: int) -> bool:
    """
    Check if a reservation's furniture is locked.

    Args:
        reservation_id: The reservation ID

    Returns:
        True if locked, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        row = cursor.fetchone()
        return bool(row and row['is_furniture_locked'])
