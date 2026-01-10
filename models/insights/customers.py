"""
Customer analytics queries.
Customer statistics, segmentation, and preference analytics.
"""

from database import get_db


# =============================================================================
# CUSTOMER ANALYTICS
# =============================================================================

def get_customer_stats(start_date: str, end_date: str) -> dict:
    """
    Get customer statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - unique_customers: int (distinct customers with reservations)
            - avg_group_size: float (average num_people per reservation)
            - returning_rate: float (percentage of customers with >1 reservation ever)
    """
    with get_db() as conn:
        # Unique customers with reservations in the date range
        unique_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.customer_id)
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (start_date, end_date))
        unique_customers = unique_cursor.fetchone()[0] or 0

        # Average group size (num_people)
        avg_cursor = conn.execute('''
            SELECT AVG(r.num_people)
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
        ''', (start_date, end_date))
        avg_result = avg_cursor.fetchone()[0]
        avg_group_size = round(float(avg_result), 1) if avg_result else 0.0

        # Returning rate: percentage of customers who have more than one reservation ever
        # Get customers from this period who have multiple reservations total
        repeat_cursor = conn.execute('''
            SELECT
                COUNT(DISTINCT CASE
                    WHEN total_res > 1 THEN customer_id
                    ELSE NULL
                END) as repeat_customers,
                COUNT(DISTINCT customer_id) as total_customers
            FROM (
                SELECT
                    r.customer_id,
                    (SELECT COUNT(*)
                     FROM beach_reservations r2
                     LEFT JOIN beach_reservation_states s2 ON r2.current_state = s2.name
                     WHERE r2.customer_id = r.customer_id
                       AND (s2.is_availability_releasing = 0 OR s2.is_availability_releasing IS NULL)
                    ) as total_res
                FROM beach_reservations r
                LEFT JOIN beach_reservation_states s ON r.current_state = s.name
                WHERE r.start_date BETWEEN ? AND ?
                  AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
                GROUP BY r.customer_id
            )
        ''', (start_date, end_date))
        repeat_row = repeat_cursor.fetchone()
        returning_count = repeat_row[0] or 0
        total_count = repeat_row[1] or 0

        returning_rate = 0.0
        if total_count > 0:
            returning_rate = round((returning_count / total_count) * 100, 1)

        return {
            'unique_customers': unique_customers,
            'avg_group_size': avg_group_size,
            'returning_rate': returning_rate
        }


def get_customer_segmentation(start_date: str, end_date: str) -> dict:
    """
    Get customer segmentation data for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - by_status: list of {status: 'new'/'returning', count, percentage}
            - by_type: list of {type: 'interno'/'externo', count, percentage}
    """
    with get_db() as conn:
        # By status (new vs returning)
        # A customer is "returning" if they have reservations before the start_date
        status_cursor = conn.execute('''
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM beach_reservations r2
                        LEFT JOIN beach_reservation_states s2 ON r2.current_state = s2.name
                        WHERE r2.customer_id = r.customer_id
                          AND r2.start_date < ?
                          AND (s2.is_availability_releasing = 0 OR s2.is_availability_releasing IS NULL)
                    ) THEN 'returning'
                    ELSE 'new'
                END as status,
                COUNT(DISTINCT r.customer_id) as count
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY status
        ''', (start_date, start_date, end_date))

        by_status = []
        status_total = 0
        for row in status_cursor:
            by_status.append({
                'status': row[0],
                'count': row[1]
            })
            status_total += row[1]

        for item in by_status:
            item['percentage'] = round((item['count'] / status_total) * 100, 1) if status_total > 0 else 0

        # By type (interno vs externo)
        type_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(DISTINCT r.customer_id) as count
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_type = []
        type_total = 0
        for row in type_cursor:
            by_type.append({
                'type': row[0],
                'count': row[1]
            })
            type_total += row[1]

        for item in by_type:
            item['percentage'] = round((item['count'] / type_total) * 100, 1) if type_total > 0 else 0

        return {
            'by_status': by_status,
            'by_type': by_type
        }


def get_top_customers(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get top customers by total spend in a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of customers to return

    Returns:
        list of dicts with customer_id, customer_name, customer_type,
        reservation_count, total_spend
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                c.id as customer_id,
                c.first_name || ' ' || c.last_name as customer_name,
                c.customer_type,
                COUNT(r.id) as reservation_count,
                COALESCE(SUM(r.final_price), 0) as total_spend
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY c.id, c.first_name, c.last_name, c.customer_type
            ORDER BY total_spend DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            results.append({
                'customer_id': row[0],
                'customer_name': row[1],
                'customer_type': row[2],
                'reservation_count': row[3],
                'total_spend': float(row[4])
            })

        return results


def get_popular_preferences(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get most popular customer preferences for customers with reservations in a date range.
    Preferences are linked to customers via beach_customer_preferences.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of preferences to return

    Returns:
        list of dicts with preference_id, preference_name, preference_code, count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                p.id as preference_id,
                p.name as preference_name,
                p.code as preference_code,
                COUNT(DISTINCT cp.customer_id) as count
            FROM beach_preferences p
            JOIN beach_customer_preferences cp ON p.id = cp.preference_id
            JOIN beach_reservations r ON r.customer_id = cp.customer_id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND p.active = 1
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY p.id, p.name, p.code
            ORDER BY count DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            results.append({
                'preference_id': row[0],
                'preference_name': row[1],
                'preference_code': row[2],
                'count': row[3]
            })

        return results


def get_popular_tags(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get most popular customer tags for customers with reservations in a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of tags to return

    Returns:
        list of dicts with tag_id, tag_name, tag_color, count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                t.id as tag_id,
                t.name as tag_name,
                t.color as tag_color,
                COUNT(DISTINCT ct.customer_id) as count
            FROM beach_tags t
            JOIN beach_customer_tags ct ON t.id = ct.tag_id
            JOIN beach_reservations r ON r.customer_id = ct.customer_id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND t.active = 1
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY t.id, t.name, t.color
            ORDER BY count DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            results.append({
                'tag_id': row[0],
                'tag_name': row[1],
                'tag_color': row[2],
                'count': row[3]
            })

        return results
