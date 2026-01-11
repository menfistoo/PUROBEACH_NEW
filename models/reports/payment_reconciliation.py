"""Payment reconciliation report queries."""
from typing import Any
from database import get_db


def get_reconciliation_data(
    date: str,
    payment_status: str | None = None,
    payment_method: str | None = None,
    zone_id: int | None = None,
    has_ticket: bool | None = None
) -> list[dict[str, Any]]:
    """
    Get reservations for payment reconciliation report.

    Args:
        date: Date string in YYYY-MM-DD format
        payment_status: 'paid', 'pending', or None for all
        payment_method: 'efectivo', 'tarjeta', 'cargo_habitacion', or None
        zone_id: Filter by zone ID, or None for all
        has_ticket: True for with ticket, False for without, None for all

    Returns:
        List of reservation dicts with customer, furniture, zone, payment info
    """
    query = """
        SELECT
            r.id,
            r.reservation_type,
            r.final_price,
            r.paid,
            r.payment_method,
            r.payment_ticket_number,
            r.num_people,
            r.created_at,
            c.id as customer_id,
            c.first_name,
            c.last_name,
            c.customer_type,
            f.number as furniture_name,
            ft.display_name as furniture_type_name,
            z.id as zone_id,
            z.name as zone_name,
            p.package_name,
            rs.name as state_name,
            rs.color as state_color
        FROM beach_reservations r
        LEFT JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
            AND rf.assignment_date = r.start_date
        LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_packages p ON r.package_id = p.id
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.start_date = ?
        AND r.reservation_type IN ('paquete', 'consumo_minimo')
        AND COALESCE(rs.is_availability_releasing, 0) = 0
    """

    params: list[Any] = [date]

    if payment_status == 'paid':
        query += " AND r.paid = 1"
    elif payment_status == 'pending':
        query += " AND r.paid = 0"

    if payment_method:
        query += " AND r.payment_method = ?"
        params.append(payment_method)

    if zone_id:
        query += " AND z.id = ?"
        params.append(zone_id)

    if has_ticket is True:
        query += " AND r.payment_ticket_number IS NOT NULL AND r.payment_ticket_number != ''"
    elif has_ticket is False:
        query += " AND (r.payment_ticket_number IS NULL OR r.payment_ticket_number = '')"

    query += " ORDER BY r.paid ASC, r.created_at DESC"

    with get_db() as conn:
        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_payment_summary(date: str) -> dict[str, Any]:
    """
    Get payment summary totals for a date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        Dict with totals by method and ticket counts
    """
    with get_db() as conn:
        # Get totals by payment method
        cursor = conn.execute("""
            SELECT
                r.payment_method,
                COUNT(*) as count,
                COALESCE(SUM(r.final_price), 0) as total
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
            WHERE r.start_date = ?
            AND r.reservation_type IN ('paquete', 'consumo_minimo')
            AND COALESCE(rs.is_availability_releasing, 0) = 0
            AND r.paid = 1
            GROUP BY r.payment_method
        """, (date,))

        method_totals = {
            'efectivo': {'count': 0, 'total': 0.0},
            'tarjeta': {'count': 0, 'total': 0.0},
            'cargo_habitacion': {'count': 0, 'total': 0.0}
        }

        for row in cursor.fetchall():
            method = row[0]
            if method in method_totals:
                method_totals[method] = {'count': row[1], 'total': float(row[2])}

        # Get pending totals
        pending_cursor = conn.execute("""
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(r.final_price), 0) as total
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
            WHERE r.start_date = ?
            AND r.reservation_type IN ('paquete', 'consumo_minimo')
            AND COALESCE(rs.is_availability_releasing, 0) = 0
            AND r.paid = 0
        """, (date,))

        pending_row = pending_cursor.fetchone()
        pending = {'count': pending_row[0], 'total': float(pending_row[1])}

        # Get ticket counts (paid with ticket vs paid without)
        ticket_cursor = conn.execute("""
            SELECT
                COUNT(*) as total_paid,
                SUM(CASE WHEN r.payment_ticket_number IS NOT NULL
                         AND r.payment_ticket_number != '' THEN 1 ELSE 0 END) as with_ticket
            FROM beach_reservations r
            LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
            WHERE r.start_date = ?
            AND r.reservation_type IN ('paquete', 'consumo_minimo')
            AND COALESCE(rs.is_availability_releasing, 0) = 0
            AND r.paid = 1
        """, (date,))

        ticket_row = ticket_cursor.fetchone()
        tickets = {
            'total_paid': ticket_row[0] or 0,
            'with_ticket': ticket_row[1] or 0,
            'missing': (ticket_row[0] or 0) - (ticket_row[1] or 0)
        }

        return {
            'by_method': method_totals,
            'pending': pending,
            'tickets': tickets
        }


def mark_reservation_paid(
    reservation_id: int,
    payment_method: str,
    ticket_number: str | None = None
) -> bool:
    """
    Mark a reservation as paid.

    Args:
        reservation_id: ID of the reservation
        payment_method: 'efectivo', 'tarjeta', or 'cargo_habitacion'
        ticket_number: Optional POS ticket number

    Returns:
        True if updated successfully
    """
    if payment_method not in ('efectivo', 'tarjeta', 'cargo_habitacion'):
        return False

    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE beach_reservations
            SET paid = 1,
                payment_method = ?,
                payment_ticket_number = ?
            WHERE id = ?
            AND paid = 0
        """, (payment_method, ticket_number, reservation_id))

        conn.commit()
        return cursor.rowcount > 0
