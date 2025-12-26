"""
Reservation CRUD operations.
Handles create, read, update, delete for reservations.
"""

from database import get_db
from datetime import datetime
from .reservation_state import calculate_reservation_color, update_customer_statistics
from .state import get_default_state
from .reservation_availability import check_furniture_availability_bulk


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

        # Get default state from database
        default_state = get_default_state()
        initial_state = default_state.get('name', 'Confirmada')

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
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, CURRENT_TIMESTAMP
            )
        ''', (
            customer_id, ticket_number, reservation_date, reservation_date, reservation_date,
            num_people, time_slot, initial_state, initial_state,
            payment_status, price, final_price, hamaca_included, price_catalog_id, paid,
            charge_to_room, charge_reference,
            minimum_consumption_amount, minimum_consumption_policy_id,
            check_in_date, check_out_date, preferences, observations,
            parent_reservation_id, reservation_type, created_by
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
                db.rollback()
                raise ValueError(f"Mobiliario no disponible: {conflict_ids}")

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
            VALUES (?, ?, 'added', ?, 'Creacion de reserva', CURRENT_TIMESTAMP)
        ''', (reservation_id, initial_state, created_by))

        db.commit()

        # Sync preferences to customer profile
        if preferences:
            sync_preferences_to_customer(customer_id, preferences)

        return reservation_id, ticket_number

    except Exception as e:
        db.rollback()
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

        db.commit()
        return True

    except Exception:
        db.rollback()
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
    db = get_db()
    cursor = db.cursor()

    try:
        # Delete from tables without CASCADE
        cursor.execute('DELETE FROM reservation_status_history WHERE reservation_id = ?',
                      (reservation_id,))

        # Delete reservation (CASCADE handles the rest)
        cursor.execute('DELETE FROM beach_reservations WHERE id = ?', (reservation_id,))

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
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
# PREFERENCE SYNC
# =============================================================================

def sync_preferences_to_customer(customer_id: int, preferences_csv: str,
                                  replace: bool = True) -> bool:
    """
    Sync reservation preferences to customer profile.
    Updates customer's preferences and propagates to all active reservations.

    Args:
        customer_id: Customer ID
        preferences_csv: CSV of preference codes (e.g., 'pref_sombra,pref_vip')
        replace: If True, replaces all existing preferences. If False, only adds.

    Returns:
        bool: Success status
    """
    db = get_db()
    cursor = db.cursor()

    try:
        pref_codes = []
        if preferences_csv:
            pref_codes = [p.strip() for p in preferences_csv.split(',') if p.strip()]

        if replace:
            # Delete existing customer preferences
            cursor.execute(
                'DELETE FROM beach_customer_preferences WHERE customer_id = ?',
                (customer_id,)
            )

        # Get preference IDs for the codes
        pref_ids = []
        for code in pref_codes:
            cursor.execute('SELECT id FROM beach_preferences WHERE code = ?', (code,))
            row = cursor.fetchone()
            if row:
                pref_ids.append(row['id'])
                cursor.execute('''
                    INSERT OR IGNORE INTO beach_customer_preferences
                    (customer_id, preference_id)
                    VALUES (?, ?)
                ''', (customer_id, row['id']))

        db.commit()

        # Propagate to all active/future reservations
        sync_customer_preferences_to_reservations(customer_id, preferences_csv)

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


def sync_customer_preferences_to_reservations(customer_id: int,
                                               preferences_csv: str = None) -> int:
    """
    Sync customer preferences to all their active/future reservations.
    Called when customer preferences are updated.

    Args:
        customer_id: Customer ID
        preferences_csv: CSV of preference codes. If None, fetches from customer profile.

    Returns:
        int: Number of reservations updated
    """
    db = get_db()
    cursor = db.cursor()

    try:
        # Get preferences CSV if not provided
        if preferences_csv is None:
            codes = get_customer_preference_codes(customer_id)
            preferences_csv = ','.join(codes) if codes else None

        # Get all active/future reservations for this customer
        # Only update reservations that haven't been completed or cancelled
        cursor.execute('''
            SELECT r.id
            FROM beach_reservations r
            LEFT JOIN beach_reservation_daily_states rds
                ON rds.reservation_id = r.id
                AND rds.state_date = r.reservation_date
            LEFT JOIN beach_reservation_states rs
                ON rs.name = rds.state_name
            WHERE r.customer_id = ?
            AND r.reservation_date >= date('now')
            AND (rs.is_availability_releasing IS NULL OR rs.is_availability_releasing = 0)
        ''', (customer_id,))

        reservation_ids = [row['id'] for row in cursor.fetchall()]

        if not reservation_ids:
            return 0

        # Update all matching reservations
        placeholders = ','.join('?' * len(reservation_ids))
        cursor.execute(f'''
            UPDATE beach_reservations
            SET preferences = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', [preferences_csv] + reservation_ids)

        db.commit()
        return len(reservation_ids)

    except Exception:
        db.rollback()
        return 0
