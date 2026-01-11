"""
Reservation query functions.
Handles listing, filtering, statistics, and availability checks.
"""

from database import get_db
from datetime import datetime
from .reservation_state import calculate_reservation_color, get_active_releasing_states


# =============================================================================
# LIST QUERIES
# =============================================================================

def get_all_beach_reservations(
    date: str = None,
    date_from: str = None,
    date_to: str = None,
    status_filter: str = None,
    room_number: str = None,
    guest_name: str = None,
    customer_type: str = None,
    ticket_number: str = None
) -> list:
    """
    List reservations with filters.

    Args:
        date: Exact date
        date_from: Range start
        date_to: Range end
        status_filter: State name filter
        room_number: Filter by room
        guest_name: Search by name
        customer_type: 'interno' or 'externo'
        ticket_number: Search by ticket

    Returns:
        list: Reservations with customer data
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT r.*,
                   c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                   c.customer_type,
                   c.room_number,
                   CASE WHEN r.original_room IS NOT NULL
                        AND r.original_room != c.room_number
                        THEN 1 ELSE 0 END as room_changed
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE 1=1
        '''
        params = []

        if date:
            query += ' AND r.reservation_date = ?'
            params.append(date)
        elif date_from and date_to:
            query += ' AND r.reservation_date BETWEEN ? AND ?'
            params.extend([date_from, date_to])
        elif date_from:
            query += ' AND r.reservation_date >= ?'
            params.append(date_from)
        elif date_to:
            query += ' AND r.reservation_date <= ?'
            params.append(date_to)

        if status_filter:
            query += ' AND r.current_state = ?'
            params.append(status_filter)

        if room_number:
            query += ' AND c.room_number = ?'
            params.append(room_number)

        if guest_name:
            query += ' AND (c.first_name LIKE ? OR c.last_name LIKE ?)'
            params.extend([f'%{guest_name}%', f'%{guest_name}%'])

        if customer_type:
            query += ' AND c.customer_type = ?'
            params.append(customer_type)

        if ticket_number:
            query += ' AND r.ticket_number LIKE ?'
            params.append(f'%{ticket_number}%')

        query += ' ORDER BY r.reservation_date DESC, r.created_at DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()

        reservations = []
        for row in rows:
            res = dict(row)
            res['display_color'] = calculate_reservation_color(res.get('current_states', ''))
            reservations.append(res)

        return reservations


def get_reservations_filtered(
    date_from: str = None,
    date_to: str = None,
    customer_type: str = None,
    state: str = None,
    search: str = None,
    page: int = 1,
    per_page: int = 50
) -> dict:
    """
    Get filtered reservations with pagination (for list view).

    Args:
        date_from: Start date filter
        date_to: End date filter
        customer_type: 'interno' or 'externo'
        state: State name filter
        search: Search term (name, ticket, room)
        page: Page number
        per_page: Items per page

    Returns:
        dict: {items: list, total: int, page: int, per_page: int, pages: int}
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Build base query with furniture names subquery
        query = '''
            SELECT r.*,
                   c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                   c.customer_type,
                   c.room_number,
                   (SELECT GROUP_CONCAT(f.number, ', ')
                    FROM beach_reservation_furniture rf
                    JOIN beach_furniture f ON rf.furniture_id = f.id
                    WHERE rf.reservation_id = r.id) as furniture_names,
                   CASE WHEN r.original_room IS NOT NULL
                        AND r.original_room != c.room_number
                        THEN 1 ELSE 0 END as room_changed
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE 1=1
        '''
        count_query = '''
            SELECT COUNT(*) as total
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE 1=1
        '''
        params = []

        if date_from:
            query += ' AND r.reservation_date >= ?'
            count_query += ' AND r.reservation_date >= ?'
            params.append(date_from)

        if date_to:
            query += ' AND r.reservation_date <= ?'
            count_query += ' AND r.reservation_date <= ?'
            params.append(date_to)

        if customer_type:
            query += ' AND c.customer_type = ?'
            count_query += ' AND c.customer_type = ?'
            params.append(customer_type)

        if state:
            query += ' AND r.current_state = ?'
            count_query += ' AND r.current_state = ?'
            params.append(state)

        if search:
            search_clause = ''' AND (
                c.first_name LIKE ? OR c.last_name LIKE ? OR
                c.room_number LIKE ? OR r.ticket_number LIKE ?
            )'''
            query += search_clause
            count_query += search_clause
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])

        # Get total count
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        # Add pagination
        query += ' ORDER BY r.reservation_date DESC, r.created_at DESC'
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, (page - 1) * per_page])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        items = []
        for row in rows:
            res = dict(row)
            res['display_color'] = calculate_reservation_color(res.get('current_states', ''))
            items.append(res)

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }


def get_linked_reservations(reservation_id: int) -> list:
    """
    Get all linked reservations (parent + children).

    Args:
        reservation_id: Any reservation in the group

    Returns:
        list: All reservations in the group
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # First check if this is a parent or child
        cursor.execute('''
            SELECT id, parent_reservation_id FROM beach_reservations WHERE id = ?
        ''', (reservation_id,))
        row = cursor.fetchone()
        if not row:
            return []

        # Determine the parent ID
        if row['parent_reservation_id']:
            parent_id = row['parent_reservation_id']
        else:
            parent_id = reservation_id

        # Get parent and all children
        cursor.execute('''
            SELECT * FROM beach_reservations
            WHERE id = ? OR parent_reservation_id = ?
            ORDER BY reservation_date
        ''', (parent_id, parent_id))

        return [dict(r) for r in cursor.fetchall()]


# =============================================================================
# STATISTICS
# =============================================================================

def get_reservation_stats(date_from: str = None, date_to: str = None) -> dict:
    """
    Get reservation statistics.

    Args:
        date_from: Start date
        date_to: End date

    Returns:
        dict: Statistics (total, by_state, by_type, etc.)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Use today as default
        if not date_from:
            date_from = datetime.now().strftime('%Y-%m-%d')
        if not date_to:
            date_to = date_from

        # Total count
        cursor.execute('''
            SELECT COUNT(*) as total FROM beach_reservations
            WHERE reservation_date BETWEEN ? AND ?
        ''', (date_from, date_to))
        total = cursor.fetchone()['total']

        # By state
        cursor.execute('''
            SELECT current_state, COUNT(*) as count
            FROM beach_reservations
            WHERE reservation_date BETWEEN ? AND ?
            GROUP BY current_state
        ''', (date_from, date_to))
        by_state = {row['current_state']: row['count'] for row in cursor.fetchall()}

        # By customer type
        cursor.execute('''
            SELECT c.customer_type, COUNT(*) as count
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE r.reservation_date BETWEEN ? AND ?
            GROUP BY c.customer_type
        ''', (date_from, date_to))
        by_type = {row['customer_type']: row['count'] for row in cursor.fetchall()}

        # Total people
        cursor.execute('''
            SELECT SUM(num_people) as total_people
            FROM beach_reservations
            WHERE reservation_date BETWEEN ? AND ?
        ''', (date_from, date_to))
        total_people = cursor.fetchone()['total_people'] or 0

        return {
            'total': total,
            'by_state': by_state,
            'by_type': by_type,
            'interno': by_type.get('interno', 0),
            'externo': by_type.get('externo', 0),
            'total_people': total_people,
            'confirmadas': by_state.get('Confirmada', 0),
            'canceladas': by_state.get('Cancelada', 0)
        }


# =============================================================================
# AVAILABILITY
# =============================================================================

def get_available_furniture(date: str, zone_id: int = None, furniture_type: str = None) -> list:
    """
    Get available furniture for a date.

    Args:
        date: Date to check (YYYY-MM-DD)
        zone_id: Filter by zone
        furniture_type: Filter by type

    Returns:
        list: Available furniture items
    """
    with get_db() as conn:
        cursor = conn.cursor()

        releasing_states = get_active_releasing_states()

        query = '''
            SELECT f.*, z.name as zone_name, ft.display_name as type_name
            FROM beach_furniture f
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
            WHERE f.active = 1
              AND f.id NOT IN (
                  SELECT rf.furniture_id
                  FROM beach_reservation_furniture rf
                  JOIN beach_reservations r ON rf.reservation_id = r.id
                  WHERE rf.assignment_date = ?
        '''
        params = [date]

        # Exclude only non-releasing states
        if releasing_states:
            placeholders = ','.join('?' * len(releasing_states))
            query += f'''
                    AND r.current_state NOT IN ({placeholders})
            '''
            params.extend(releasing_states)

        query += ')'

        if zone_id:
            query += ' AND f.zone_id = ?'
            params.append(zone_id)

        if furniture_type:
            query += ' AND f.furniture_type = ?'
            params.append(furniture_type)

        query += ' ORDER BY f.zone_id, f.number'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def check_furniture_availability(furniture_id: int, start_date: str, end_date: str,
                                  exclude_reservation_id: int = None) -> bool:
    """
    Check if furniture is available for date range.
    Excludes reservations with releasing states.

    Args:
        furniture_id: Furniture ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        exclude_reservation_id: Reservation ID to exclude (for updates)

    Returns:
        bool: True if available
    """
    with get_db() as conn:
        cursor = conn.cursor()

        releasing_states = get_active_releasing_states()

        query = '''
            SELECT COUNT(*) as count
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            WHERE rf.furniture_id = ?
              AND rf.assignment_date >= ?
              AND rf.assignment_date <= ?
        '''
        params = [furniture_id, start_date, end_date]

        # Exclude releasing states
        if releasing_states:
            placeholders = ','.join('?' * len(releasing_states))
            query += f' AND r.current_state NOT IN ({placeholders})'
            params.extend(releasing_states)

        if exclude_reservation_id:
            query += ' AND r.id != ?'
            params.append(exclude_reservation_id)

        cursor.execute(query, params)
        return cursor.fetchone()['count'] == 0


def get_reservation_furniture(reservation_id: int, date: str = None) -> list:
    """
    Get furniture assigned to reservation.

    Args:
        reservation_id: Reservation ID
        date: Specific date (optional)

    Returns:
        list: Furniture assignments
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT rf.*, f.number, f.furniture_type, f.capacity,
                   z.name as zone_name
            FROM beach_reservation_furniture rf
            JOIN beach_furniture f ON rf.furniture_id = f.id
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE rf.reservation_id = ?
        '''
        params = [reservation_id]

        if date:
            query += ' AND rf.assignment_date = ?'
            params.append(date)

        query += ' ORDER BY rf.assignment_date, f.number'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_reservations_by_furniture(furniture_id: int, date: str) -> list:
    """
    Get reservations for specific furniture on a date.

    Args:
        furniture_id: Furniture ID
        date: Date (YYYY-MM-DD)

    Returns:
        list: Reservations
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, c.first_name, c.last_name
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE rf.furniture_id = ? AND rf.assignment_date = ?
            ORDER BY r.created_at
        ''', (furniture_id, date))
        return [dict(row) for row in cursor.fetchall()]


def get_customer_reservation_history(customer_id: int, limit: int = 5) -> list:
    """
    Get recent reservation history for a customer.

    Args:
        customer_id: Customer ID
        limit: Maximum number of reservations to return

    Returns:
        list: Recent reservations with furniture details
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get recent reservations with furniture
        cursor.execute('''
            SELECT r.id, r.reservation_date, r.num_people, r.current_state,
                   GROUP_CONCAT(f.number, ', ') as furniture_numbers,
                   GROUP_CONCAT(DISTINCT ft.display_name) as furniture_types,
                   COUNT(rf.id) as furniture_count
            FROM beach_reservations r
            LEFT JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
            LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
            LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
            WHERE r.customer_id = ?
            GROUP BY r.id
            ORDER BY r.reservation_date DESC
            LIMIT ?
        ''', (customer_id, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'date': row['reservation_date'],
                'num_people': row['num_people'],
                'state': row['current_state'],
                'furniture_numbers': row['furniture_numbers'],
                'furniture_types': row['furniture_types'],
                'furniture_count': row['furniture_count']
            })

        return results
