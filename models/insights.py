"""
Insights model.
Analytics queries for dashboard and advanced analytics.
"""

from database import get_db
from datetime import date
from typing import Optional


# =============================================================================
# TODAY'S METRICS (Dashboard Operativo)
# =============================================================================

def get_occupancy_today() -> dict:
    """
    Get today's occupancy metrics.

    Returns:
        dict with keys:
            - occupied: int (furniture with active reservations)
            - total: int (total active furniture)
            - rate: float (percentage 0-100)
            - by_type: dict (breakdown by furniture type)
    """
    today = date.today().isoformat()

    with get_db() as conn:
        # Total active furniture
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE active = 1
        ''')
        total = total_cursor.fetchone()[0]

        if total == 0:
            return {'occupied': 0, 'total': 0, 'rate': 0.0, 'by_type': {}}

        # Occupied furniture (non-releasing states)
        # Join with beach_reservation_states to check is_availability_releasing
        occupied_cursor = conn.execute('''
            SELECT COUNT(DISTINCT rf.furniture_id)
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE rf.assignment_date = ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (today,))
        occupied = occupied_cursor.fetchone()[0]

        # Breakdown by furniture type
        by_type_cursor = conn.execute('''
            SELECT
                ft.type_code,
                ft.display_name,
                COUNT(f.id) as total,
                COUNT(DISTINCT CASE
                    WHEN rf.assignment_date = ?
                         AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
                    THEN rf.furniture_id
                    ELSE NULL
                END) as occupied
            FROM beach_furniture_types ft
            LEFT JOIN beach_furniture f ON f.furniture_type = ft.type_code AND f.active = 1
            LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id
                AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE ft.active = 1
            GROUP BY ft.id, ft.type_code, ft.display_name
        ''', (today, today))

        by_type = {}
        for row in by_type_cursor:
            by_type[row[0]] = {
                'name': row[1],
                'total': row[2],
                'occupied': row[3] or 0,
                'free': row[2] - (row[3] or 0)
            }

        rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

        return {
            'occupied': occupied,
            'total': total,
            'rate': rate,
            'by_type': by_type
        }
