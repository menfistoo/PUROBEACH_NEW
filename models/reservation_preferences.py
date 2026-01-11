"""
Reservation preference synchronization.

Handles syncing preferences between customer profiles and their reservations,
ensuring preference consistency across the system.

Phase 6B - Module 4A (Extracted from reservation_crud.py)
"""

from database import get_db


# =============================================================================
# PREFERENCE RETRIEVAL
# =============================================================================

def get_customer_preference_codes(customer_id: int) -> list:
    """
    Get preference codes for customer.

    Args:
        customer_id: Customer ID

    Returns:
        list: Preference codes
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.code FROM beach_preferences p
            JOIN beach_customer_preferences cp ON p.id = cp.preference_id
            WHERE cp.customer_id = ?
        ''', (customer_id,))
        return [row['code'] for row in cursor.fetchall()]


# =============================================================================
# PREFERENCE SYNCHRONIZATION
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
    with get_db() as conn:
        cursor = conn.cursor()

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

            conn.commit()

            # Propagate to all active/future reservations
            sync_customer_preferences_to_reservations(customer_id, preferences_csv)

            return True

        except Exception:
            conn.rollback()
            return False


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
    with get_db() as conn:
        cursor = conn.cursor()

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

            conn.commit()
            return len(reservation_ids)

        except Exception:
            conn.rollback()
            return 0
