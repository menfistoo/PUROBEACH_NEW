"""
Map reservation search API routes.
Customer search with furniture lookup for the map.
All-reservations endpoint for enhanced search with filters.
"""

from flask import request
from flask_login import login_required
from datetime import date

from utils.decorators import permission_required
from utils.api_response import api_success, api_error
from models.customer import search_customers_unified
from database import get_db


def register_routes(bp):
    """Register map search routes on the blueprint."""

    @bp.route('/map/all-reservations')
    @login_required
    @permission_required('beach.map.view')
    def get_all_reservations_for_search():
        """
        Get ALL reservations for a date including cancelled/no-show/liberadas.
        Used for enhanced search functionality with filters.

        Query params:
            date: Date string YYYY-MM-DD (default: today)
            zone_id: Optional zone filter

        Returns:
            JSON with all reservations grouped with furniture codes
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        zone_id = request.args.get('zone_id', type=int)

        with get_db() as conn:
            # Build query - NO filtering by is_availability_releasing
            # Note: beach_reservation_daily_states has columns: date, state_id (not state_date, state_name)
            query = '''
                SELECT
                    r.id as reservation_id,
                    r.ticket_number,
                    COALESCE(rs_daily.name, r.current_state) as state,
                    r.paid,
                    r.num_people,
                    c.id as customer_id,
                    c.first_name || ' ' || c.last_name as customer_name,
                    c.customer_type,
                    c.room_number,
                    COALESCE(rs_daily.is_availability_releasing, rs_current.is_availability_releasing) as is_availability_releasing,
                    COALESCE(rs_daily.color, rs_current.color) as state_color,
                    GROUP_CONCAT(DISTINCT f.number) as furniture_codes,
                    GROUP_CONCAT(DISTINCT f.id) as furniture_ids
                FROM beach_reservations r
                JOIN beach_customers c ON r.customer_id = c.id
                JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
                JOIN beach_furniture f ON f.id = rf.furniture_id
                LEFT JOIN beach_reservation_daily_states rds
                    ON rds.reservation_id = r.id AND rds.date = rf.assignment_date
                LEFT JOIN beach_reservation_states rs_daily
                    ON rs_daily.id = rds.state_id
                LEFT JOIN beach_reservation_states rs_current
                    ON rs_current.name = r.current_state
                WHERE rf.assignment_date = ?
            '''
            params = [date_str]

            # Add zone filter if provided
            if zone_id:
                query += ' AND f.zone_id = ?'
                params.append(zone_id)

            query += '''
                GROUP BY r.id
                ORDER BY c.first_name, c.last_name
            '''

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Also get states for filter dropdown
            states_cursor = conn.execute('''
                SELECT name, color, is_availability_releasing
                FROM beach_reservation_states
                WHERE active = 1
                ORDER BY display_order
            ''')
            states = [dict(row) for row in states_cursor.fetchall()]

        # Format response
        reservations = []
        for row in rows:
            furniture_codes = row['furniture_codes'].split(',') if row['furniture_codes'] else []
            furniture_ids = [int(x) for x in row['furniture_ids'].split(',')] if row['furniture_ids'] else []

            reservations.append({
                'reservation_id': row['reservation_id'],
                'ticket_number': row['ticket_number'],
                'customer_id': row['customer_id'],
                'customer_name': row['customer_name'] or 'Sin cliente',
                'customer_type': row['customer_type'],
                'room_number': row['room_number'],
                'state': row['state'],
                'state_color': row['state_color'] or '#F3F4F6',
                'is_released': bool(row['is_availability_releasing']),
                'paid': bool(row['paid']),
                'num_people': row['num_people'],
                'furniture_codes': furniture_codes,
                'furniture_ids': furniture_ids
            })

        return api_success(
            date=date_str,
            reservations=reservations,
            states=states,
            total=len(reservations)
        )

    @bp.route('/map/search-customer')
    @login_required
    @permission_required('beach.map.view')
    def search_customer():
        """
        Search customers and return their reserved furniture for the date.

        Query params:
            q: Search query (name, room, phone)
            date: Date string YYYY-MM-DD (default: today)

        Returns:
            JSON with matching customers and their furniture_ids
        """
        query = request.args.get('q', '').strip()
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))

        if len(query) < 2:
            return api_success(customers=[], furniture_ids=[])

        # Search customers
        customers = search_customers_unified(query, limit=10)

        # Get customer IDs
        customer_ids = [c['id'] for c in customers if c.get('source') == 'customer']

        if not customer_ids:
            # Return customers without furniture matches
            return api_success(
                customers=[{
                    'id': c.get('id'),
                    'name': c.get('guest_name') or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                    'room_number': c.get('room_number'),
                    'customer_type': c.get('customer_type', 'interno'),
                    'source': c.get('source', 'customer')
                } for c in customers],
                furniture_ids=[]
            )

        # Find furniture reserved by these customers for the date
        # Note: beach_reservation_daily_states has columns: date, state_id (not state_date, state_name)
        with get_db() as conn:
            placeholders = ','.join('?' * len(customer_ids))
            cursor = conn.execute(f'''
                SELECT DISTINCT rf.furniture_id, r.customer_id
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                LEFT JOIN beach_reservation_daily_states rds
                    ON rds.reservation_id = r.id AND rds.date = rf.assignment_date
                LEFT JOIN beach_reservation_states rs ON rs.id = rds.state_id
                WHERE r.customer_id IN ({placeholders})
                AND rf.assignment_date = ?
                AND (
                    rs.is_availability_releasing IS NULL
                    OR rs.is_availability_releasing = 0
                )
            ''', customer_ids + [date_str])

            furniture_rows = cursor.fetchall()

        furniture_ids = list(set(row['furniture_id'] for row in furniture_rows))
        customer_furniture_map = {}
        for row in furniture_rows:
            if row['customer_id'] not in customer_furniture_map:
                customer_furniture_map[row['customer_id']] = []
            customer_furniture_map[row['customer_id']].append(row['furniture_id'])

        # Format response
        formatted_customers = []
        for c in customers:
            customer_data = {
                'id': c.get('id'),
                'name': c.get('guest_name') or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                'room_number': c.get('room_number'),
                'customer_type': c.get('customer_type', 'interno'),
                'source': c.get('source', 'customer'),
                'furniture_ids': customer_furniture_map.get(c.get('id'), [])
            }
            formatted_customers.append(customer_data)

        return api_success(
            date=date_str,
            customers=formatted_customers,
            furniture_ids=furniture_ids
        )
