"""
Revenue analytics queries.
Revenue statistics and breakdown analytics.
"""

from database import get_db


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
