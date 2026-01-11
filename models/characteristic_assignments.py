"""
Characteristic assignment functions.
Handles assigning characteristics to furniture, reservations, and customers.
"""

from database import get_db


# =============================================================================
# FURNITURE CHARACTERISTICS
# =============================================================================

def get_furniture_characteristics(furniture_id: int) -> list:
    """
    Get characteristics assigned to a furniture item.

    Args:
        furniture_id: Furniture ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_furniture_characteristics fc ON c.id = fc.characteristic_id
            WHERE fc.furniture_id = ?
            ORDER BY c.display_order, c.name
        ''', (furniture_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_furniture_characteristic_ids(furniture_id: int) -> list[int]:
    """
    Get characteristic IDs assigned to a furniture item.

    Args:
        furniture_id: Furniture ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_furniture_characteristics
            WHERE furniture_id = ?
        ''', (furniture_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_furniture_characteristics(furniture_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set characteristics for a furniture item (replaces existing).

    Args:
        furniture_id: Furniture ID
        characteristic_ids: List of characteristic IDs to assign

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_furniture_characteristics WHERE furniture_id = ?',
            (furniture_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_furniture_characteristics (furniture_id, characteristic_id)
                VALUES (?, ?)
            ''', (furniture_id, char_id))

        conn.commit()
        return True


# =============================================================================
# RESERVATION CHARACTERISTICS
# =============================================================================

def get_reservation_characteristics(reservation_id: int) -> list:
    """
    Get characteristics requested by a reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_reservation_characteristics rc ON c.id = rc.characteristic_id
            WHERE rc.reservation_id = ?
            ORDER BY c.display_order, c.name
        ''', (reservation_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_reservation_characteristic_ids(reservation_id: int) -> list[int]:
    """
    Get characteristic IDs requested by a reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_reservation_characteristics
            WHERE reservation_id = ?
        ''', (reservation_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_reservation_characteristics(reservation_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set characteristics for a reservation (replaces existing).

    Args:
        reservation_id: Reservation ID
        characteristic_ids: List of characteristic IDs to request

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_reservation_characteristics WHERE reservation_id = ?',
            (reservation_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_reservation_characteristics (reservation_id, characteristic_id)
                VALUES (?, ?)
            ''', (reservation_id, char_id))

        conn.commit()
        return True


# =============================================================================
# CUSTOMER CHARACTERISTICS (DEFAULT PREFERENCES)
# =============================================================================

def get_customer_characteristics(customer_id: int) -> list:
    """
    Get default characteristics for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_customer_characteristics cc ON c.id = cc.characteristic_id
            WHERE cc.customer_id = ?
            ORDER BY c.display_order, c.name
        ''', (customer_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_customer_characteristic_ids(customer_id: int) -> list[int]:
    """
    Get default characteristic IDs for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_customer_characteristics
            WHERE customer_id = ?
        ''', (customer_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_customer_characteristics(customer_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set default characteristics for a customer (replaces existing).

    Args:
        customer_id: Customer ID
        characteristic_ids: List of characteristic IDs

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_customer_characteristics WHERE customer_id = ?',
            (customer_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_customer_characteristics (customer_id, characteristic_id)
                VALUES (?, ?)
            ''', (customer_id, char_id))

        conn.commit()
        return True


# =============================================================================
# SCORING (FOR SUGGESTION ALGORITHM)
# =============================================================================

def score_characteristic_match(furniture_id: int, requested_ids: list[int]) -> dict:
    """
    Calculate how well furniture matches requested characteristics.

    Args:
        furniture_id: Furniture ID to score
        requested_ids: List of characteristic IDs requested

    Returns:
        dict: {
            'score': float (0.0 to 1.0),
            'matched': list of matched characteristic IDs,
            'missing': list of missing characteristic IDs
        }
    """
    if not requested_ids:
        return {'score': 1.0, 'matched': [], 'missing': []}

    furniture_ids = set(get_furniture_characteristic_ids(furniture_id))
    requested_set = set(requested_ids)

    matched = list(furniture_ids & requested_set)
    missing = list(requested_set - furniture_ids)

    score = len(matched) / len(requested_ids) if requested_ids else 1.0

    return {
        'score': score,
        'matched': matched,
        'missing': missing
    }


# =============================================================================
# HELPER FUNCTIONS (CODE-BASED)
# =============================================================================

def set_customer_characteristics_by_codes(customer_id: int, codes: list[str]) -> bool:
    """
    Set customer characteristics using code strings.
    Converts codes to IDs and sets characteristics.

    Args:
        customer_id: Customer ID
        codes: List of characteristic codes

    Returns:
        True if successful
    """
    from models.characteristic import get_characteristic_by_code

    char_ids = []
    for code in codes:
        char = get_characteristic_by_code(code)
        if char:
            char_ids.append(char['id'])

    return set_customer_characteristics(customer_id, char_ids)


def set_reservation_characteristics_by_codes(reservation_id: int, codes: list[str]) -> bool:
    """
    Set reservation characteristics using code strings.
    Converts codes to IDs and sets characteristics.

    Args:
        reservation_id: Reservation ID
        codes: List of characteristic codes

    Returns:
        True if successful
    """
    from models.characteristic import get_characteristic_by_code

    char_ids = []
    for code in codes:
        char = get_characteristic_by_code(code)
        if char:
            char_ids.append(char['id'])

    return set_reservation_characteristics(reservation_id, char_ids)


# =============================================================================
# BACKWARD COMPATIBILITY (PREFERENCE SYNC)
# =============================================================================

def sync_preferences_to_customer(customer_id: int, preferences_csv: str, replace: bool = False) -> bool:
    """
    Sync preferences from reservation to customer (backward compatibility).

    Args:
        customer_id: Customer ID
        preferences_csv: Comma-separated characteristic codes
        replace: If True, replace all. If False, merge with existing.

    Returns:
        True if successful
    """
    if not preferences_csv:
        if replace:
            return set_customer_characteristics(customer_id, [])
        return True

    codes = [c.strip() for c in preferences_csv.split(',') if c.strip()]
    return set_customer_characteristics_by_codes(customer_id, codes)


def get_customer_preference_codes(customer_id: int) -> list[str]:
    """
    Get customer preference codes (backward compatibility).

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic codes
    """
    characteristics = get_customer_characteristics(customer_id)
    return [c['code'] for c in characteristics]


def sync_preferences_to_reservation(reservation_id: int, preferences_csv: str) -> bool:
    """
    Sync preferences to reservation characteristics junction table.

    Args:
        reservation_id: Reservation ID
        preferences_csv: Comma-separated characteristic codes

    Returns:
        True if successful
    """
    if not preferences_csv:
        return set_reservation_characteristics(reservation_id, [])

    codes = [c.strip() for c in preferences_csv.split(',') if c.strip()]
    return set_reservation_characteristics_by_codes(reservation_id, codes)


def sync_customer_preferences_to_reservations(customer_id: int, preferences_csv: str = None) -> int:
    """
    Sync customer preferences to all active/future reservations.

    Updates both the preferences CSV column and the
    beach_reservation_characteristics junction table.

    Args:
        customer_id: Customer ID
        preferences_csv: Optional new preferences to sync (if None, uses customer's current)

    Returns:
        Number of reservations updated
    """
    from models.characteristic import get_characteristic_by_code

    with get_db() as conn:
        cursor = conn.cursor()

        # Get preference codes to sync
        if preferences_csv is None:
            # Use customer's current preferences
            codes = get_customer_preference_codes(customer_id)
        else:
            codes = [c.strip() for c in preferences_csv.split(',') if c.strip()]

        # Get characteristic IDs for the codes
        char_ids = []
        for code in codes:
            char = get_characteristic_by_code(code)
            if char:
                char_ids.append(char['id'])

        # Get all active/future reservations for this customer
        cursor.execute('''
            SELECT id FROM beach_reservations
            WHERE customer_id = ?
            AND reservation_date >= date('now')
        ''', (customer_id,))

        reservations = cursor.fetchall()
        updated_count = 0

        for res in reservations:
            res_id = res['id']

            # Update preferences CSV column
            csv_value = ','.join(codes) if codes else ''
            cursor.execute('''
                UPDATE beach_reservations
                SET preferences = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (csv_value, res_id))

            # Clear existing reservation characteristics
            cursor.execute('''
                DELETE FROM beach_reservation_characteristics
                WHERE reservation_id = ?
            ''', (res_id,))

            # Insert new characteristics
            for char_id in char_ids:
                cursor.execute('''
                    INSERT INTO beach_reservation_characteristics
                    (reservation_id, characteristic_id)
                    VALUES (?, ?)
                ''', (res_id, char_id))

            updated_count += 1

        conn.commit()
        return updated_count
