"""
Move mode model functions.

Handles furniture assignment changes during move mode operations.
"""

from database import get_db
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union


def _parse_date(value: Union[str, date]) -> date:
    """Parse a date value from SQLite which may be string or date object."""
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()
    return value


def _date_to_str(value: Union[str, date]) -> str:
    """Convert a date value to ISO format string."""
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def unassign_furniture_for_date(
    reservation_id: int,
    furniture_ids: List[int],
    assignment_date: str
) -> Dict[str, Any]:
    """
    Unassign furniture from a reservation for a specific date.

    Args:
        reservation_id: The reservation to modify
        furniture_ids: List of furniture IDs to unassign
        assignment_date: Date in YYYY-MM-DD format

    Returns:
        Dict with success status and unassigned furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if reservation is locked
        cursor.execute(
            "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        row = cursor.fetchone()
        if row and row['is_furniture_locked']:
            return {
                'success': False,
                'error': 'locked',
                'message': 'El mobiliario de esta reserva está bloqueado'
            }

        unassigned = []
        not_found = []
        for furniture_id in furniture_ids:
            cursor.execute("""
                DELETE FROM beach_reservation_furniture
                WHERE reservation_id = ?
                AND furniture_id = ?
                AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.rowcount > 0:
                unassigned.append(furniture_id)
            else:
                not_found.append(furniture_id)

        conn.commit()

        # Log warning if some furniture wasn't found (helps debug move mode issues)
        if not_found:
            import logging
            logging.warning(
                f"[MoveMode] unassign: furniture {not_found} not found for "
                f"reservation {reservation_id} on {assignment_date}"
            )

        return {
            'success': True,
            'unassigned_count': len(unassigned),
            'furniture_ids': unassigned,
            'not_found': not_found,  # Include for debugging
            'reservation_id': reservation_id,
            'date': assignment_date
        }


def assign_furniture_for_date(
    reservation_id: int,
    furniture_ids: List[int],
    assignment_date: str
) -> Dict[str, Any]:
    """
    Assign furniture to a reservation for a specific date.

    Args:
        reservation_id: The reservation to modify
        furniture_ids: List of furniture IDs to assign
        assignment_date: Date in YYYY-MM-DD format

    Returns:
        Dict with success status and assigned furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check availability first
        placeholders = ','.join('?' * len(furniture_ids))
        cursor.execute(f"""
            SELECT rf.furniture_id, r.id as res_id, c.first_name, c.last_name
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE rf.furniture_id IN ({placeholders})
            AND rf.assignment_date = ?
            AND rf.reservation_id != ?
        """, (*furniture_ids, assignment_date, reservation_id))

        conflicts = cursor.fetchall()
        if conflicts:
            conflict = conflicts[0]
            return {
                'success': False,
                'error': f"Mobiliario ocupado por {conflict['first_name']} {conflict['last_name']}",
                'conflicts': [dict(c) for c in conflicts]
            }

        # Assign furniture
        assigned = []
        for furniture_id in furniture_ids:
            # Check if already assigned to this reservation
            cursor.execute("""
                SELECT id FROM beach_reservation_furniture
                WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.fetchone():
                # Already assigned, skip but count as assigned (idempotent)
                assigned.append(furniture_id)
                continue

            cursor.execute("""
                INSERT INTO beach_reservation_furniture
                (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, ?)
            """, (reservation_id, furniture_id, assignment_date))
            assigned.append(furniture_id)

        conn.commit()

        return {
            'success': True,
            'assigned_count': len(assigned),
            'furniture_ids': assigned,
            'reservation_id': reservation_id,
            'date': assignment_date
        }


def get_reservation_pool_data(
    reservation_id: int,
    target_date: str
) -> Dict[str, Any]:
    """
    Get comprehensive reservation data for the pool panel display.

    Args:
        reservation_id: The reservation ID
        target_date: The date being viewed (YYYY-MM-DD)

    Returns:
        Dict with reservation details, customer info, preferences,
        original furniture, and multi-day info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get reservation and customer info
        cursor.execute("""
            SELECT
                r.id,
                r.ticket_number,
                r.num_people,
                r.start_date,
                r.end_date,
                r.preferences,
                r.notes,
                r.parent_reservation_id,
                c.id as customer_id,
                c.first_name,
                c.last_name,
                c.room_number,
                c.customer_type,
                c.email,
                c.phone
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE r.id = ?
        """, (reservation_id,))

        res = cursor.fetchone()
        if not res:
            return {'error': 'Reserva no encontrada'}

        # Get furniture assignments for target date
        cursor.execute("""
            SELECT
                f.id,
                f.number,
                f.furniture_type,
                f.capacity,
                z.name as zone_name
            FROM beach_reservation_furniture rf
            JOIN beach_furniture f ON rf.furniture_id = f.id
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE rf.reservation_id = ? AND rf.assignment_date = ?
        """, (reservation_id, target_date))

        furniture = [dict(row) for row in cursor.fetchall()]

        # Calculate multi-day info
        start = _parse_date(res['start_date'])
        end = _parse_date(res['end_date'])
        total_days = (end - start).days + 1
        is_multiday = total_days > 1

        # Get all day assignments for multi-day
        day_assignments = {}
        if is_multiday:
            cursor.execute("""
                SELECT
                    rf.assignment_date,
                    GROUP_CONCAT(f.number) as furniture_numbers
                FROM beach_reservation_furniture rf
                JOIN beach_furniture f ON rf.furniture_id = f.id
                WHERE rf.reservation_id = ?
                GROUP BY rf.assignment_date
                ORDER BY rf.assignment_date
            """, (reservation_id,))

            for row in cursor.fetchall():
                assign_date = _date_to_str(row['assignment_date'])
                day_assignments[assign_date] = row['furniture_numbers']

        # Parse preferences (now stored in beach_characteristics)
        preferences = []
        if res['preferences']:
            pref_codes = [p.strip() for p in res['preferences'].split(',') if p.strip()]
            if pref_codes:
                placeholders = ','.join('?' * len(pref_codes))
                cursor.execute(f"""
                    SELECT code, name, icon
                    FROM beach_characteristics
                    WHERE code IN ({placeholders})
                """, pref_codes)
                preferences = [dict(row) for row in cursor.fetchall()]

        return {
            'reservation_id': res['id'],
            'ticket_number': res['ticket_number'],
            'customer_id': res['customer_id'],
            'customer_name': f"{res['first_name']} {res['last_name']}",
            'customer_type': res['customer_type'],
            'room_number': res['room_number'],
            'email': res['email'],
            'phone': res['phone'],
            'num_people': res['num_people'],
            'preferences': preferences,
            'notes': res['notes'],
            'original_furniture': furniture,
            'is_multiday': is_multiday,
            'total_days': total_days,
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'day_assignments': day_assignments,
            'target_date': target_date
        }


def get_unassigned_reservations_global(days_ahead: int = 7) -> Dict[str, Any]:
    """
    Get all reservations with insufficient furniture for the next N days.

    Args:
        days_ahead: Number of days to check from today (default 7)

    Returns:
        Dict with:
        - count: Total number of unassigned reservations
        - dates: List of dates that have unassigned reservations
        - by_date: Dict mapping date -> list of reservation IDs
        - first_date: First date with unassigned reservations (for navigation)
    """
    from datetime import datetime, timedelta

    today = datetime.now().date()
    result = {
        'count': 0,
        'dates': [],
        'by_date': {},
        'first_date': None
    }

    for i in range(days_ahead):
        check_date = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        reservation_ids = get_unassigned_reservations(check_date)

        if reservation_ids:
            result['dates'].append(check_date)
            result['by_date'][check_date] = reservation_ids
            result['count'] += len(reservation_ids)

            if result['first_date'] is None:
                result['first_date'] = check_date

    return result


def get_unassigned_reservations(target_date: str) -> List[int]:
    """
    Get all reservations for a date that have insufficient furniture capacity.

    A reservation is considered unassigned if its assigned furniture capacity
    is less than num_people and the reservation state is not availability-releasing.

    For multi-day reservations, each day has its own reservation record with
    reservation_date set to that specific day. Using reservation_date ensures
    we only check the correct record for each day (not the parent for all days).

    Args:
        target_date: Date to check (YYYY-MM-DD)

    Returns:
        List of reservation IDs that need furniture assignments
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Use reservation_date instead of start/end range to correctly handle
        # multi-day reservations where parent=day1 and children=subsequent days
        cursor.execute("""
            SELECT
                r.id as reservation_id,
                r.num_people,
                COALESCE(SUM(f.capacity), 0) as assigned_capacity
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
            LEFT JOIN beach_reservation_furniture rf
                ON r.id = rf.reservation_id AND rf.assignment_date = ?
            LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
            WHERE r.reservation_date = ?
              AND (rs.is_availability_releasing IS NULL OR rs.is_availability_releasing = 0)
            GROUP BY r.id
            HAVING assigned_capacity < r.num_people
        """, (target_date, target_date))

        return [row['reservation_id'] for row in cursor.fetchall()]


def get_furniture_preference_matches(
    preference_codes: List[str],
    target_date: str,
    zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get all furniture with preference match scores for a given date.

    Uses beach_furniture_characteristics junction table to match
    furniture characteristics against requested preference codes.

    Args:
        preference_codes: List of characteristic codes to match
        target_date: Date to check availability (YYYY-MM-DD)
        zone_id: Optional zone to filter by

    Returns:
        Dict with furniture list including availability and match scores
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get characteristic IDs for the requested codes
        char_ids = {}
        if preference_codes:
            placeholders = ','.join('?' * len(preference_codes))
            cursor.execute(f"""
                SELECT id, code
                FROM beach_characteristics
                WHERE code IN ({placeholders})
            """, preference_codes)
            char_ids = {row['code']: row['id'] for row in cursor.fetchall()}

        # Get all active furniture with their characteristics
        zone_filter = "AND f.zone_id = ?" if zone_id else ""
        zone_params = (zone_id,) if zone_id else ()

        cursor.execute(f"""
            SELECT
                f.id,
                f.number,
                f.capacity,
                f.zone_id,
                f.furniture_type,
                z.name as zone_name
            FROM beach_furniture f
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE f.active = 1
            {zone_filter}
            ORDER BY f.zone_id, f.number
        """, zone_params)

        all_furniture = [dict(row) for row in cursor.fetchall()]

        # Get characteristics for all furniture
        furniture_chars = {}
        if all_furniture:
            furniture_ids = [f['id'] for f in all_furniture]
            placeholders = ','.join('?' * len(furniture_ids))
            cursor.execute(f"""
                SELECT fc.furniture_id, c.code
                FROM beach_furniture_characteristics fc
                JOIN beach_characteristics c ON fc.characteristic_id = c.id
                WHERE fc.furniture_id IN ({placeholders})
            """, furniture_ids)

            for row in cursor.fetchall():
                fid = row['furniture_id']
                if fid not in furniture_chars:
                    furniture_chars[fid] = set()
                furniture_chars[fid].add(row['code'])

        # Get occupied furniture for the date
        cursor.execute("""
            SELECT DISTINCT rf.furniture_id
            FROM beach_reservation_furniture rf
            WHERE rf.assignment_date = ?
        """, (target_date,))

        occupied_ids = {row['furniture_id'] for row in cursor.fetchall()}

        # Calculate match scores
        result_furniture = []
        for f in all_furniture:
            furn_char_codes = furniture_chars.get(f['id'], set())

            # Match against requested codes
            matched = [code for code in preference_codes if code in furn_char_codes]

            total_prefs = len(preference_codes) if preference_codes else 1
            match_score = len(matched) / total_prefs if total_prefs > 0 and preference_codes else 0

            result_furniture.append({
                'id': f['id'],
                'number': f['number'],
                'capacity': f['capacity'],
                'furniture_type': f['furniture_type'],
                'zone_id': f['zone_id'],
                'zone_name': f['zone_name'],
                'available': f['id'] not in occupied_ids,
                'match_score': match_score,
                'matched_preferences': matched
            })

        return {
            'furniture': result_furniture,
            'date': target_date,
            'preferences_requested': preference_codes
        }
