"""
Move mode model functions.

Handles furniture assignment changes during move mode operations.
"""

from database import get_db
from datetime import datetime
from typing import List, Dict, Any, Optional


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

        unassigned = []
        for furniture_id in furniture_ids:
            cursor.execute("""
                DELETE FROM beach_reservation_furniture
                WHERE reservation_id = ?
                AND furniture_id = ?
                AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.rowcount > 0:
                unassigned.append(furniture_id)

        conn.commit()

        return {
            'success': True,
            'unassigned_count': len(unassigned),
            'furniture_ids': unassigned,
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
        # Handle both string and date object from SQLite
        start_date = res['start_date']
        end_date = res['end_date']
        if isinstance(start_date, str):
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start = start_date
        if isinstance(end_date, str):
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end = end_date

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
                day_assignments[row['assignment_date']] = row['furniture_numbers']

        # Parse preferences
        preferences = []
        if res['preferences']:
            pref_codes = [p.strip() for p in res['preferences'].split(',') if p.strip()]
            if pref_codes:
                placeholders = ','.join('?' * len(pref_codes))
                cursor.execute(f"""
                    SELECT code, name, icon
                    FROM beach_preferences
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
            'start_date': start.isoformat() if hasattr(start, 'isoformat') else str(start),
            'end_date': end.isoformat() if hasattr(end, 'isoformat') else str(end),
            'day_assignments': day_assignments,
            'target_date': target_date
        }


def get_furniture_preference_matches(
    preference_codes: List[str],
    target_date: str,
    zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get all furniture with preference match scores for a given date.

    Args:
        preference_codes: List of preference codes to match
        target_date: Date to check availability (YYYY-MM-DD)
        zone_id: Optional zone to filter by

    Returns:
        Dict with furniture list including availability and match scores
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get preference feature mappings
        pref_features = {}
        if preference_codes:
            placeholders = ','.join('?' * len(preference_codes))
            cursor.execute(f"""
                SELECT code, maps_to_feature
                FROM beach_preferences
                WHERE code IN ({placeholders})
            """, preference_codes)
            pref_features = {row['code']: row['maps_to_feature'] for row in cursor.fetchall()}

        # Get all active furniture
        zone_filter = "AND f.zone_id = ?" if zone_id else ""
        zone_params = (zone_id,) if zone_id else ()

        cursor.execute(f"""
            SELECT
                f.id,
                f.number,
                f.capacity,
                f.features,
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

        # Get occupied furniture for the date
        # Check for any furniture assignment, regardless of state
        # (state filtering is handled at reservation level)
        cursor.execute("""
            SELECT DISTINCT rf.furniture_id
            FROM beach_reservation_furniture rf
            WHERE rf.assignment_date = ?
        """, (target_date,))

        occupied_ids = {row['furniture_id'] for row in cursor.fetchall()}

        # Calculate match scores
        result_furniture = []
        for f in all_furniture:
            furniture_features = set()
            if f['features']:
                furniture_features = {feat.strip() for feat in f['features'].split(',') if feat.strip()}

            matched = []
            for pref_code, feature in pref_features.items():
                if feature and feature in furniture_features:
                    matched.append(pref_code)

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
