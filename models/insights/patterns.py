"""
Booking patterns analytics queries.
Lead time, day-of-week, and cancellation pattern analytics.
"""

from database import get_db


# =============================================================================
# BOOKING PATTERNS
# =============================================================================

def get_pattern_stats(start_date: str, end_date: str) -> dict:
    """
    Get booking pattern statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - avg_lead_time: float (average days between created_at and start_date)
            - cancellation_rate: float (percentage with state 'cancelada')
            - noshow_rate: float (percentage with state 'noshow')
    """
    with get_db() as conn:
        # Total reservations in range
        total_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        total_count = total_cursor.fetchone()[0]

        if total_count == 0:
            return {
                'avg_lead_time': 0.0,
                'cancellation_rate': 0.0,
                'noshow_rate': 0.0
            }

        # Average lead time (days between created_at and start_date)
        lead_time_cursor = conn.execute('''
            SELECT AVG(JULIANDAY(r.start_date) - JULIANDAY(DATE(r.created_at)))
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        avg_lead_time = lead_time_cursor.fetchone()[0]
        avg_lead_time = round(float(avg_lead_time), 1) if avg_lead_time else 0.0

        # Cancellation count
        cancel_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'cancelada'
        ''', (start_date, end_date))
        cancel_count = cancel_cursor.fetchone()[0]

        # No-show count
        noshow_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'noshow'
        ''', (start_date, end_date))
        noshow_count = noshow_cursor.fetchone()[0]

        cancellation_rate = round((cancel_count / total_count) * 100, 1)
        noshow_rate = round((noshow_count / total_count) * 100, 1)

        return {
            'avg_lead_time': avg_lead_time,
            'cancellation_rate': cancellation_rate,
            'noshow_rate': noshow_rate
        }


def get_reservations_by_day_of_week(start_date: str, end_date: str) -> list:
    """
    Get reservation counts by day of week for a date range.
    Only counts non-releasing state reservations.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        list of dicts with day_of_week (0-6), name ('Dom','Lun',...), count
    """
    # Spanish day names (0=Sunday to 6=Saturday)
    day_names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

    with get_db() as conn:
        # SQLite strftime('%w') returns 0=Sunday, 1=Monday, ..., 6=Saturday
        cursor = conn.execute('''
            SELECT
                CAST(strftime('%w', r.start_date) AS INTEGER) as day_of_week,
                COUNT(*) as count
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
              AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
            GROUP BY day_of_week
        ''', (start_date, end_date))

        counts_by_day = {row[0]: row[1] for row in cursor}

        # Build result for all 7 days
        results = []
        for day_num in range(7):
            results.append({
                'day_of_week': day_num,
                'name': day_names[day_num],
                'count': counts_by_day.get(day_num, 0)
            })

        return results


def get_lead_time_distribution(start_date: str, end_date: str) -> list:
    """
    Get distribution of reservations by lead time buckets.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        list of dicts with bucket, name, count, percentage
        Buckets: 'same_day', '1_2_days', '3_7_days', '8_14_days', '15_plus_days'
    """
    bucket_config = [
        ('same_day', 'Mismo día', 0, 0),
        ('1_2_days', '1-2 días', 1, 2),
        ('3_7_days', '3-7 días', 3, 7),
        ('8_14_days', '8-14 días', 8, 14),
        ('15_plus_days', '15+ días', 15, 999999)
    ]

    with get_db() as conn:
        # Get lead time for each reservation
        cursor = conn.execute('''
            SELECT
                JULIANDAY(r.start_date) - JULIANDAY(DATE(r.created_at)) as lead_time
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))

        # Count reservations in each bucket
        bucket_counts = {bucket[0]: 0 for bucket in bucket_config}
        total_count = 0

        for row in cursor:
            lead_time = row[0] if row[0] is not None else 0
            lead_time = max(0, int(lead_time))  # Ensure non-negative integer
            total_count += 1

            for bucket_id, _, min_days, max_days in bucket_config:
                if min_days <= lead_time <= max_days:
                    bucket_counts[bucket_id] += 1
                    break

        # Build result with percentages
        results = []
        for bucket_id, bucket_name, _, _ in bucket_config:
            count = bucket_counts[bucket_id]
            percentage = round((count / total_count) * 100, 1) if total_count > 0 else 0.0
            results.append({
                'bucket': bucket_id,
                'name': bucket_name,
                'count': count,
                'percentage': percentage
            })

        return results


def get_cancellation_breakdown(start_date: str, end_date: str) -> dict:
    """
    Get cancellation rate breakdown by customer type and lead time.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - by_customer_type: list of {type, rate}
            - by_lead_time: list of {bucket, name, rate}
    """
    bucket_config = [
        ('same_day', 'Mismo día', 0, 0),
        ('1_2_days', '1-2 días', 1, 2),
        ('3_7_days', '3-7 días', 3, 7),
        ('8_14_days', '8-14 días', 8, 14),
        ('15_plus_days', '15+ días', 15, 999999)
    ]

    with get_db() as conn:
        # By customer type
        type_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(*) as total,
                SUM(CASE WHEN s.code = 'cancelada' THEN 1 ELSE 0 END) as cancelled
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_customer_type = []
        for row in type_cursor:
            customer_type = row[0]
            total = row[1]
            cancelled = row[2]
            rate = round((cancelled / total) * 100, 1) if total > 0 else 0.0
            by_customer_type.append({
                'type': customer_type,
                'rate': rate
            })

        # By lead time bucket
        lead_time_cursor = conn.execute('''
            SELECT
                JULIANDAY(r.start_date) - JULIANDAY(DATE(r.created_at)) as lead_time,
                CASE WHEN s.code = 'cancelada' THEN 1 ELSE 0 END as is_cancelled
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states s ON r.current_state = s.name
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))

        # Count total and cancelled in each bucket
        bucket_total = {bucket[0]: 0 for bucket in bucket_config}
        bucket_cancelled = {bucket[0]: 0 for bucket in bucket_config}

        for row in lead_time_cursor:
            lead_time = row[0] if row[0] is not None else 0
            lead_time = max(0, int(lead_time))
            is_cancelled = row[1]

            for bucket_id, _, min_days, max_days in bucket_config:
                if min_days <= lead_time <= max_days:
                    bucket_total[bucket_id] += 1
                    if is_cancelled:
                        bucket_cancelled[bucket_id] += 1
                    break

        by_lead_time = []
        for bucket_id, bucket_name, _, _ in bucket_config:
            total = bucket_total[bucket_id]
            cancelled = bucket_cancelled[bucket_id]
            rate = round((cancelled / total) * 100, 1) if total > 0 else 0.0
            by_lead_time.append({
                'bucket': bucket_id,
                'name': bucket_name,
                'rate': rate
            })

        return {
            'by_customer_type': by_customer_type,
            'by_lead_time': by_lead_time
        }
