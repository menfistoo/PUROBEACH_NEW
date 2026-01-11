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
