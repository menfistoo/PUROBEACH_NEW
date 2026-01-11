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
