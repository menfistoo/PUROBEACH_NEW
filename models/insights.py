"""
Insights model.
Analytics queries for dashboard and advanced analytics.
"""

from database import get_db
from datetime import date, timedelta
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


def get_occupancy_by_zone(target_date: Optional[str] = None) -> list:
    """
    Get occupancy breakdown by zone.

    Args:
        target_date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        list of dicts with keys:
            - zone_id: int
            - zone_name: str
            - occupied: int
            - total: int
            - rate: float (0-100)
    """
    if target_date is None:
        target_date = date.today().isoformat()

    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                z.id as zone_id,
                z.name as zone_name,
                COUNT(DISTINCT f.id) as total,
                COUNT(DISTINCT CASE
                    WHEN rf.id IS NOT NULL AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
                    THEN f.id
                END) as occupied
            FROM beach_zones z
            LEFT JOIN beach_furniture f ON f.zone_id = z.id AND f.active = 1
            LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id
                AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE z.active = 1
            GROUP BY z.id, z.name
            ORDER BY z.display_order
        ''', (target_date,))

        results = []
        for row in cursor:
            total = row[2] or 0
            occupied = row[3] or 0
            rate = round((occupied / total) * 100, 1) if total > 0 else 0.0
            results.append({
                'zone_id': row[0],
                'zone_name': row[1],
                'total': total,
                'occupied': occupied,
                'rate': rate
            })

        return results


def get_pending_checkins_count(target_date: Optional[str] = None) -> int:
    """
    Get count of reservations pending check-in for a date.

    Args:
        target_date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        int: Number of reservations in 'confirmada' or 'pendiente' state
    """
    if target_date is None:
        target_date = date.today().isoformat()

    with get_db() as conn:
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date <= ?
              AND r.end_date >= ?
              AND s.code IN ('pendiente', 'confirmada')
        ''', (target_date, target_date))
        return cursor.fetchone()[0]


def get_occupancy_comparison() -> dict:
    """
    Get today's occupancy compared to yesterday.

    Returns:
        dict with keys:
            - today_rate: float
            - yesterday_rate: float
            - difference: float (positive = improvement)
            - trend: str ('up', 'down', 'same')
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    today_data = _get_occupancy_for_date(today.isoformat())
    yesterday_data = _get_occupancy_for_date(yesterday.isoformat())

    today_rate = today_data['rate']
    yesterday_rate = yesterday_data['rate']
    difference = round(today_rate - yesterday_rate, 1)

    if difference > 0:
        trend = 'up'
    elif difference < 0:
        trend = 'down'
    else:
        trend = 'same'

    return {
        'today_rate': today_rate,
        'yesterday_rate': yesterday_rate,
        'difference': difference,
        'trend': trend
    }


def _get_occupancy_for_date(target_date: str) -> dict:
    """
    Internal helper to get occupancy for a specific date.

    Args:
        target_date: Date string (YYYY-MM-DD)

    Returns:
        dict with keys:
            - occupied: int
            - total: int
            - rate: float (0-100)
    """
    with get_db() as conn:
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE active = 1
        ''')
        total = total_cursor.fetchone()[0]

        if total == 0:
            return {'occupied': 0, 'total': 0, 'rate': 0.0}

        occupied_cursor = conn.execute('''
            SELECT COUNT(DISTINCT rf.furniture_id)
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE rf.assignment_date = ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (target_date,))
        result = occupied_cursor.fetchone()
        occupied = result[0] if result else 0

        rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

        return {'occupied': occupied, 'total': total, 'rate': rate}


# =============================================================================
# ADVANCED ANALYTICS - OCCUPANCY
# =============================================================================

def get_occupancy_range(start_date: str, end_date: str) -> list:
    """
    Get daily occupancy for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        list of dicts with date, occupied, total, rate for each day
    """
    from datetime import datetime

    with get_db() as conn:
        # Get total active furniture (constant for all days)
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE active = 1
        ''')
        total = total_cursor.fetchone()[0]

        # Generate all dates in range
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get occupied counts for the range
        occupied_cursor = conn.execute('''
            SELECT
                rf.assignment_date,
                COUNT(DISTINCT rf.furniture_id) as occupied
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE rf.assignment_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY rf.assignment_date
        ''', (start_date, end_date))

        occupied_by_date = {row[0]: row[1] for row in occupied_cursor}

        # Build result for each day
        results = []
        current = start
        while current <= end:
            date_str = current.isoformat()
            occupied = occupied_by_date.get(date_str, 0)
            rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

            results.append({
                'date': date_str,
                'occupied': occupied,
                'total': total,
                'rate': rate
            })
            current += timedelta(days=1)

        return results


def get_occupancy_stats(start_date: str, end_date: str) -> dict:
    """
    Get summary occupancy statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - avg_occupancy: float (average daily occupancy %)
            - total_reservations: int (non-cancelled reservations)
            - noshow_rate: float (no-show percentage)
    """
    # Get daily occupancy data
    daily_data = get_occupancy_range(start_date, end_date)
    avg_occupancy = 0.0
    if daily_data:
        avg_occupancy = round(
            sum(d['rate'] for d in daily_data) / len(daily_data), 1
        )

    with get_db() as conn:
        # Total reservations (non-releasing states)
        res_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (start_date, end_date))
        total_reservations = res_cursor.fetchone()[0]

        # No-show count
        noshow_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'no_show'
        ''', (start_date, end_date))
        noshow_count = noshow_cursor.fetchone()[0]

        # Total for rate calculation (including no-shows)
        total_for_rate = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date)).fetchone()[0]

        noshow_rate = 0.0
        if total_for_rate > 0:
            noshow_rate = round((noshow_count / total_for_rate) * 100, 1)

    return {
        'avg_occupancy': avg_occupancy,
        'total_reservations': total_reservations,
        'noshow_rate': noshow_rate
    }


# =============================================================================
# REVENUE METRICS (Advanced Analytics)
# =============================================================================

def get_revenue_stats(start_date: str, end_date: str) -> dict:
    """
    Get revenue statistics for a date range.
    Only includes paquete and consumo_minimo reservation types.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - total_revenue: float
            - paid_reservations: int
            - avg_per_reservation: float
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                COALESCE(SUM(r.final_price), 0) as total_revenue,
                COUNT(*) as paid_reservations
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND r.reservation_type IN ('paquete', 'consumo_minimo')
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (start_date, end_date))

        row = cursor.fetchone()
        total_revenue = float(row[0] or 0)
        paid_reservations = row[1] or 0

        avg_per_reservation = 0.0
        if paid_reservations > 0:
            avg_per_reservation = round(total_revenue / paid_reservations, 2)

        return {
            'total_revenue': total_revenue,
            'paid_reservations': paid_reservations,
            'avg_per_reservation': avg_per_reservation
        }


def get_revenue_by_type(start_date: str, end_date: str) -> dict:
    """
    Get revenue breakdown by reservation type and customer type.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - by_reservation_type: list of {type, count, revenue, percentage}
            - by_customer_type: list of {type, count, revenue, percentage}
    """
    with get_db() as conn:
        # By reservation type
        res_type_cursor = conn.execute('''
            SELECT
                r.reservation_type,
                COUNT(*) as count,
                COALESCE(SUM(r.final_price), 0) as revenue
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY r.reservation_type
        ''', (start_date, end_date))

        by_res_type = []
        total_count = 0
        for row in res_type_cursor:
            by_res_type.append({
                'type': row[0] or 'incluido',
                'count': row[1],
                'revenue': float(row[2])
            })
            total_count += row[1]

        # Calculate percentages
        for item in by_res_type:
            item['percentage'] = round((item['count'] / total_count) * 100, 1) if total_count > 0 else 0

        # By customer type
        cust_type_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(DISTINCT r.id) as count,
                COALESCE(SUM(r.final_price), 0) as revenue
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_cust_type = []
        cust_total = 0
        for row in cust_type_cursor:
            by_cust_type.append({
                'type': row[0],
                'count': row[1],
                'revenue': float(row[2])
            })
            cust_total += row[1]

        for item in by_cust_type:
            item['percentage'] = round((item['count'] / cust_total) * 100, 1) if cust_total > 0 else 0

        return {
            'by_reservation_type': by_res_type,
            'by_customer_type': by_cust_type
        }


def get_top_packages(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get top packages by usage count.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of packages to return

    Returns:
        list of dicts with package_name, count, revenue
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                p.package_name,
                COUNT(r.id) as count,
                COALESCE(SUM(r.final_price), 0) as revenue
            FROM beach_reservations r
            JOIN beach_packages p ON r.package_id = p.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND r.reservation_type = 'paquete'
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY p.id, p.package_name
            ORDER BY count DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            results.append({
                'package_name': row[0],
                'count': row[1],
                'revenue': float(row[2])
            })

        return results
