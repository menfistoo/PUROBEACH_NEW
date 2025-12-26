"""
Bulk availability checking and duplicate detection.
Handles efficient multi-furniture/multi-date availability queries.

Phase 6B - Module 1
"""

from database import get_db
from .reservation_state import get_active_releasing_states


# =============================================================================
# BULK AVAILABILITY
# =============================================================================

def check_furniture_availability_bulk(
    furniture_ids: list,
    dates: list,
    exclude_reservation_id: int = None
) -> dict:
    """
    Check availability of multiple furniture items for multiple dates.
    More efficient than calling check_furniture_availability() in a loop.

    Args:
        furniture_ids: List of furniture IDs to check
        dates: List of dates (YYYY-MM-DD strings)
        exclude_reservation_id: Reservation ID to exclude (for updates)

    Returns:
        dict: {
            'all_available': bool,
            'unavailable': [
                {'furniture_id': int, 'date': str, 'reservation_id': int,
                 'ticket_number': str, 'customer_name': str}
            ],
            'availability_matrix': {
                'YYYY-MM-DD': {furniture_id: bool, ...}
            }
        }
    """
    if not furniture_ids or not dates:
        return {
            'all_available': True,
            'unavailable': [],
            'availability_matrix': {}
        }

    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()

    # Build query to find all conflicts
    placeholders_furniture = ','.join('?' * len(furniture_ids))
    placeholders_dates = ','.join('?' * len(dates))

    query = f'''
        SELECT rf.furniture_id, rf.assignment_date, r.id as reservation_id,
               r.ticket_number, r.current_state,
               f.number as furniture_number,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.room_number
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        JOIN beach_furniture f ON rf.furniture_id = f.id
        WHERE rf.furniture_id IN ({placeholders_furniture})
          AND rf.assignment_date IN ({placeholders_dates})
    '''
    params = list(furniture_ids) + list(dates)

    # Exclude releasing states (Cancelada, No-Show, Liberada)
    if releasing_states:
        placeholders_states = ','.join('?' * len(releasing_states))
        query += f' AND r.current_state NOT IN ({placeholders_states})'
        params.extend(releasing_states)

    # Exclude specific reservation (for updates)
    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    cursor.execute(query, params)
    conflicts = cursor.fetchall()

    # Build unavailable list
    # Note: assignment_date may be returned as datetime.date object, convert to string
    unavailable = []
    conflict_set = set()  # (furniture_id, date) tuples

    for row in conflicts:
        assignment_date = row['assignment_date']
        if hasattr(assignment_date, 'strftime'):
            assignment_date = assignment_date.strftime('%Y-%m-%d')
        unavailable.append({
            'furniture_id': row['furniture_id'],
            'furniture_number': row['furniture_number'],
            'date': assignment_date,
            'reservation_id': row['reservation_id'],
            'ticket_number': row['ticket_number'],
            'customer_name': row['customer_name'],
            'room_number': row['room_number']
        })
        conflict_set.add((row['furniture_id'], assignment_date))

    # Build availability matrix
    availability_matrix = {}
    for date in dates:
        availability_matrix[date] = {}
        for furn_id in furniture_ids:
            availability_matrix[date][furn_id] = (furn_id, date) not in conflict_set

    return {
        'all_available': len(unavailable) == 0,
        'unavailable': unavailable,
        'availability_matrix': availability_matrix
    }


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def check_duplicate_reservation(
    customer_id: int,
    dates: list,
    exclude_reservation_id: int = None
) -> tuple:
    """
    Detect duplicate reservations for same customer on same dates.
    Excludes reservations with releasing states (Cancelada, No-Show, Liberada).

    Args:
        customer_id: Customer ID to check
        dates: List of dates to check (YYYY-MM-DD strings)
        exclude_reservation_id: Reservation ID to exclude (for updates)

    Returns:
        tuple: (is_duplicate: bool, existing_reservation: dict or None)
            existing_reservation contains: id, ticket_number, date, current_state
    """
    if not customer_id or not dates:
        return False, None

    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()

    # Check for existing reservations on any of the dates
    placeholders_dates = ','.join('?' * len(dates))

    query = f'''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state,
               r.current_states, r.num_people
        FROM beach_reservations r
        WHERE r.customer_id = ?
          AND r.reservation_date IN ({placeholders_dates})
    '''
    params = [customer_id] + list(dates)

    # Exclude releasing states
    if releasing_states:
        placeholders_states = ','.join('?' * len(releasing_states))
        query += f' AND r.current_state NOT IN ({placeholders_states})'
        params.extend(releasing_states)

    # Exclude specific reservation
    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    query += ' ORDER BY r.reservation_date LIMIT 1'

    cursor.execute(query, params)
    row = cursor.fetchone()

    if row:
        reservation_id = row['id']

        # Fetch furniture for this reservation
        furniture_query = '''
            SELECT bf.id, bf.number, bft.display_name as type_name
            FROM beach_reservation_furniture brf
            JOIN beach_furniture bf ON brf.furniture_id = bf.id
            JOIN beach_furniture_types bft ON bf.furniture_type = bft.type_code
            WHERE brf.reservation_id = ?
        '''
        cursor.execute(furniture_query, (reservation_id,))
        furniture_rows = cursor.fetchall()
        furniture = [
            {'id': f['id'], 'number': f['number'], 'type_name': f['type_name']}
            for f in furniture_rows
        ]

        return True, {
            'id': reservation_id,
            'ticket_number': row['ticket_number'],
            'date': row['reservation_date'],
            'current_state': row['current_state'],
            'num_people': row['num_people'],
            'furniture': furniture
        }

    return False, None


def check_duplicate_by_room(
    room_number: str,
    dates: list,
    exclude_reservation_id: int = None
) -> tuple:
    """
    Check if a reservation exists for a customer with the given room number.

    This is used when checking for duplicates before converting a hotel guest
    to a beach customer - we check if any customer from the same room already
    has a reservation on the given dates.

    Args:
        room_number: Hotel room number
        dates: List of dates to check (YYYY-MM-DD)
        exclude_reservation_id: Reservation ID to exclude from check

    Returns:
        tuple: (is_duplicate: bool, existing_reservation: dict or None)
    """
    if not room_number or not dates:
        return False, None

    db = get_db()
    cursor = db.cursor()

    # Build date placeholders
    date_placeholders = ','.join(['?' for _ in dates])

    query = f'''
        SELECT r.id, r.ticket_number, r.start_date as reservation_date,
               r.current_state, r.num_people, c.first_name, c.last_name,
               c.room_number
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_states s
            ON r.current_state = s.name
        WHERE c.room_number = ?
          AND r.start_date IN ({date_placeholders})
          AND (s.is_availability_releasing = 0 OR s.is_availability_releasing IS NULL)
    '''

    params = [room_number] + dates

    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    query += ' LIMIT 1'

    cursor.execute(query, params)
    row = cursor.fetchone()

    if row:
        reservation_id = row['id']

        # Fetch furniture for this reservation
        furniture_query = '''
            SELECT bf.id, bf.number, bft.display_name as type_name
            FROM beach_reservation_furniture brf
            JOIN beach_furniture bf ON brf.furniture_id = bf.id
            JOIN beach_furniture_types bft ON bf.furniture_type = bft.type_code
            WHERE brf.reservation_id = ?
        '''
        cursor.execute(furniture_query, (reservation_id,))
        furniture_rows = cursor.fetchall()
        furniture = [
            {'id': f['id'], 'number': f['number'], 'type_name': f['type_name']}
            for f in furniture_rows
        ]

        return True, {
            'id': reservation_id,
            'ticket_number': row['ticket_number'],
            'date': row['reservation_date'],
            'current_state': row['current_state'],
            'num_people': row['num_people'],
            'customer_name': f"{row['first_name'] or ''} {row['last_name'] or ''}".strip(),
            'room_number': row['room_number'],
            'furniture': furniture
        }

    return False, None


# =============================================================================
# AVAILABILITY MAP (for calendar/grid views)
# =============================================================================

def get_furniture_availability_map(
    date_from: str,
    date_to: str,
    zone_id: int = None,
    furniture_type: str = None
) -> dict:
    """
    Get availability map for date range (useful for calendar views).

    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        zone_id: Filter by zone (optional)
        furniture_type: Filter by type (optional)

    Returns:
        dict: {
            'furniture': [
                {'id': int, 'number': str, 'zone_name': str, 'type': str}
            ],
            'dates': [str],
            'availability': {
                furniture_id: {
                    'YYYY-MM-DD': {
                        'available': bool,
                        'reservation_id': int or None,
                        'ticket_number': str or None,
                        'customer_name': str or None,
                        'first_name': str or None,
                        'room_number': str or None,
                        'customer_type': str or None ('interno'/'externo'),
                        'vip_status': int or None,
                        'num_people': int or None,
                        'state': str or None
                    }
                }
            },
            'summary': {
                'YYYY-MM-DD': {
                    'total': int,
                    'available': int,
                    'occupied': int,
                    'occupancy_rate': float
                }
            }
        }
    """
    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()

    # Get furniture list
    furniture_query = '''
        SELECT f.id, f.number, f.furniture_type, f.capacity,
               z.name as zone_name, ft.display_name as type_name
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type = ft.type_code
        WHERE f.active = 1
    '''
    furniture_params = []

    if zone_id:
        furniture_query += ' AND f.zone_id = ?'
        furniture_params.append(zone_id)

    if furniture_type:
        furniture_query += ' AND f.furniture_type = ?'
        furniture_params.append(furniture_type)

    furniture_query += ' ORDER BY f.zone_id, f.number'

    cursor.execute(furniture_query, furniture_params)
    furniture_list = [dict(row) for row in cursor.fetchall()]
    furniture_ids = [f['id'] for f in furniture_list]

    if not furniture_ids:
        return {
            'furniture': [],
            'dates': [],
            'availability': {},
            'summary': {}
        }

    # Generate date list
    from datetime import datetime, timedelta
    start = datetime.strptime(date_from, '%Y-%m-%d')
    end = datetime.strptime(date_to, '%Y-%m-%d')
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    # Get all reservations in date range
    placeholders_furniture = ','.join('?' * len(furniture_ids))

    reservations_query = f'''
        SELECT rf.furniture_id, rf.assignment_date, r.id as reservation_id,
               r.ticket_number, r.current_state, r.num_people,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.first_name, c.room_number, c.customer_type, c.vip_status
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE rf.furniture_id IN ({placeholders_furniture})
          AND rf.assignment_date >= ?
          AND rf.assignment_date <= ?
    '''
    res_params = list(furniture_ids) + [date_from, date_to]

    # Exclude releasing states
    if releasing_states:
        placeholders_states = ','.join('?' * len(releasing_states))
        reservations_query += f' AND r.current_state NOT IN ({placeholders_states})'
        res_params.extend(releasing_states)

    cursor.execute(reservations_query, res_params)
    reservations = cursor.fetchall()

    # Build reservation lookup: {(furniture_id, date): reservation_info}
    # Note: assignment_date may be returned as datetime.date object, convert to string
    reservation_map = {}
    for row in reservations:
        assignment_date = row['assignment_date']
        if hasattr(assignment_date, 'strftime'):
            assignment_date = assignment_date.strftime('%Y-%m-%d')
        key = (row['furniture_id'], assignment_date)
        reservation_map[key] = {
            'reservation_id': row['reservation_id'],
            'ticket_number': row['ticket_number'],
            'customer_name': row['customer_name'],
            'first_name': row['first_name'],
            'room_number': row['room_number'],
            'customer_type': row['customer_type'],
            'vip_status': row['vip_status'],
            'num_people': row['num_people'],
            'state': row['current_state']
        }

    # Build availability matrix
    availability = {}
    summary = {d: {'total': len(furniture_ids), 'available': 0, 'occupied': 0} for d in dates}

    for furn in furniture_list:
        furn_id = furn['id']
        availability[furn_id] = {}

        for date in dates:
            key = (furn_id, date)
            if key in reservation_map:
                res_info = reservation_map[key]
                availability[furn_id][date] = {
                    'available': False,
                    'reservation_id': res_info['reservation_id'],
                    'ticket_number': res_info['ticket_number'],
                    'customer_name': res_info['customer_name'],
                    'first_name': res_info['first_name'],
                    'room_number': res_info['room_number'],
                    'customer_type': res_info['customer_type'],
                    'vip_status': res_info['vip_status'],
                    'num_people': res_info['num_people'],
                    'state': res_info['state']
                }
                summary[date]['occupied'] += 1
            else:
                availability[furn_id][date] = {
                    'available': True,
                    'reservation_id': None,
                    'ticket_number': None,
                    'customer_name': None,
                    'first_name': None,
                    'room_number': None,
                    'customer_type': None,
                    'vip_status': None,
                    'num_people': None,
                    'state': None
                }
                summary[date]['available'] += 1

    # Calculate occupancy rates
    for date in dates:
        total = summary[date]['total']
        occupied = summary[date]['occupied']
        summary[date]['occupancy_rate'] = round(occupied / total * 100, 1) if total > 0 else 0

    return {
        'furniture': furniture_list,
        'dates': dates,
        'availability': availability,
        'summary': summary
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_conflicting_reservations(
    furniture_ids: list,
    date: str,
    exclude_reservation_id: int = None
) -> list:
    """
    Get all reservations that conflict with given furniture on a date.
    Useful for showing what's blocking availability.

    Args:
        furniture_ids: List of furniture IDs
        date: Date to check (YYYY-MM-DD)
        exclude_reservation_id: Reservation to exclude

    Returns:
        list: Conflicting reservations with details
    """
    if not furniture_ids:
        return []

    db = get_db()
    cursor = db.cursor()

    releasing_states = get_active_releasing_states()
    placeholders = ','.join('?' * len(furniture_ids))

    query = f'''
        SELECT DISTINCT r.id, r.ticket_number, r.reservation_date,
               r.current_state, r.num_people,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.room_number,
               GROUP_CONCAT(f.number, ', ') as furniture_numbers
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        JOIN beach_furniture f ON rf.furniture_id = f.id
        WHERE rf.furniture_id IN ({placeholders})
          AND rf.assignment_date = ?
    '''
    params = list(furniture_ids) + [date]

    if releasing_states:
        placeholders_states = ','.join('?' * len(releasing_states))
        query += f' AND r.current_state NOT IN ({placeholders_states})'
        params.extend(releasing_states)

    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    query += ' GROUP BY r.id ORDER BY r.ticket_number'

    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
