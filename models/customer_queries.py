"""
Customer query functions.
Handles filtering, statistics, and detailed customer information.
"""

from database import get_db
from .customer_crud import get_customer_by_id, get_customer_preferences, get_customer_tags


# =============================================================================
# FILTERED QUERIES
# =============================================================================

def get_customers_filtered(
    search: str = None,
    customer_type: str = None,
    vip_only: bool = False,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """
    Get customers with advanced filtering and pagination.

    Args:
        search: Search term for name, phone, email, room
        customer_type: Filter by type ('interno'/'externo')
        vip_only: Only return VIP customers
        limit: Max results to return
        offset: Results offset for pagination

    Returns:
        Dict with 'customers' list and 'total' count
    """
    db = get_db()
    cursor = db.cursor()

    base_query = '''
        SELECT c.*,
               (SELECT COUNT(*) FROM beach_reservations WHERE customer_id = c.id) as reservation_count
        FROM beach_customers c
        WHERE 1=1
    '''
    count_query = 'SELECT COUNT(*) as total FROM beach_customers c WHERE 1=1'
    params = []
    count_params = []

    if search:
        search_clause = ''' AND (
            c.first_name LIKE ? OR c.last_name LIKE ? OR
            c.email LIKE ? OR c.phone LIKE ? OR c.room_number LIKE ?
        )'''
        base_query += search_clause
        count_query += search_clause
        search_term = f'%{search}%'
        params.extend([search_term] * 5)
        count_params.extend([search_term] * 5)

    if customer_type:
        base_query += ' AND c.customer_type = ?'
        count_query += ' AND c.customer_type = ?'
        params.append(customer_type)
        count_params.append(customer_type)

    if vip_only:
        base_query += ' AND c.vip_status = 1'
        count_query += ' AND c.vip_status = 1'

    # Get total count
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()['total']

    # Get paginated results
    base_query += ' ORDER BY c.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(base_query, params)
    rows = cursor.fetchall()

    return {
        'customers': [dict(row) for row in rows],
        'total': total
    }


# =============================================================================
# DETAILED QUERIES
# =============================================================================

def get_customer_with_details(customer_id: int) -> dict:
    """
    Get customer with full details including preferences, tags, and reservation history.

    Args:
        customer_id: Customer ID

    Returns:
        Customer dict with preferences, tags, and reservations or None
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return None

    db = get_db()
    cursor = db.cursor()

    # Get preferences
    customer['preferences'] = get_customer_preferences(customer_id)

    # Get tags
    customer['tags'] = get_customer_tags(customer_id)

    # Get recent reservations
    cursor.execute('''
        SELECT r.*, rs.name as state_name, rs.color as state_color
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.customer_id = ?
        ORDER BY r.start_date DESC
        LIMIT 10
    ''', (customer_id,))
    customer['recent_reservations'] = [dict(row) for row in cursor.fetchall()]

    # Get reservation stats
    cursor.execute('''
        SELECT
            COUNT(*) as total_reservations,
            SUM(CASE WHEN end_date >= date('now') THEN 1 ELSE 0 END) as active_reservations
        FROM beach_reservations
        WHERE customer_id = ?
    ''', (customer_id,))
    stats = cursor.fetchone()
    customer['total_reservations'] = stats['total_reservations'] or 0
    customer['active_reservations'] = stats['active_reservations'] or 0

    return customer


# =============================================================================
# STATISTICS
# =============================================================================

def get_customer_stats() -> dict:
    """
    Get customer statistics for dashboard.

    Returns:
        Dict with customer counts by type and VIP status
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN customer_type = 'interno' THEN 1 ELSE 0 END) as interno_count,
            SUM(CASE WHEN customer_type = 'externo' THEN 1 ELSE 0 END) as externo_count,
            SUM(CASE WHEN vip_status = 1 THEN 1 ELSE 0 END) as vip_count
        FROM beach_customers
    ''')
    row = cursor.fetchone()

    return {
        'total': row['total'] or 0,
        'interno': row['interno_count'] or 0,
        'externo': row['externo_count'] or 0,
        'vip': row['vip_count'] or 0
    }


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def find_potential_duplicates_for_customer(customer_id: int) -> list:
    """
    Find potential duplicate customers for a given customer.
    Matches by phone, email, or name similarity.

    Args:
        customer_id: Customer ID to find duplicates for

    Returns:
        List of potential duplicate customer dicts
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return []

    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT c.*,
               (SELECT COUNT(*) FROM beach_reservations WHERE customer_id = c.id) as reservation_count
        FROM beach_customers c
        WHERE c.id != ?
          AND (
    '''
    params = [customer_id]
    conditions = []

    if customer.get('phone'):
        conditions.append('c.phone = ?')
        params.append(customer['phone'])

    if customer.get('email'):
        conditions.append('c.email = ?')
        params.append(customer['email'])

    if customer.get('first_name') and customer.get('last_name'):
        conditions.append('(LOWER(c.first_name) = LOWER(?) AND LOWER(c.last_name) = LOWER(?))')
        params.extend([customer['first_name'], customer['last_name']])

    if not conditions:
        return []

    query += ' OR '.join(conditions) + ')'
    query += ' ORDER BY c.created_at DESC LIMIT 20'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
