"""
Map reservation search API routes.
Customer search with furniture lookup for the map.
"""

from flask import request, jsonify
from flask_login import login_required
from datetime import date

from utils.decorators import permission_required
from models.customer import search_customers_unified
from database import get_db


def register_routes(bp):
    """Register map search routes on the blueprint."""

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
            return jsonify({'customers': [], 'furniture_ids': []})

        # Search customers
        customers = search_customers_unified(query, limit=10)

        # Get customer IDs
        customer_ids = [c['id'] for c in customers if c.get('source') == 'customer']

        if not customer_ids:
            # Return customers without furniture matches
            return jsonify({
                'customers': [{
                    'id': c.get('id'),
                    'name': c.get('guest_name') or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                    'room_number': c.get('room_number'),
                    'customer_type': c.get('customer_type', 'interno'),
                    'source': c.get('source', 'customer')
                } for c in customers],
                'furniture_ids': []
            })

        # Find furniture reserved by these customers for the date
        with get_db() as conn:
            placeholders = ','.join('?' * len(customer_ids))
            cursor = conn.execute(f'''
                SELECT DISTINCT rf.furniture_id, r.customer_id
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                LEFT JOIN beach_reservation_daily_states rds
                    ON rds.reservation_id = r.id AND rds.state_date = rf.assignment_date
                LEFT JOIN beach_reservation_states rs ON rs.name = rds.state_name
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

        return jsonify({
            'success': True,
            'date': date_str,
            'customers': formatted_customers,
            'furniture_ids': furniture_ids
        })
