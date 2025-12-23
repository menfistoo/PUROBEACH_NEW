"""
Map reservation API routes.
Endpoints for quick reservations and customer search from map.
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

from utils.decorators import permission_required
from models.furniture import get_all_furniture
from models.reservation import (
    create_beach_reservation, check_furniture_availability_bulk
)
from models.customer import get_customer_by_id, search_customers_unified
from database import get_db


def register_routes(bp):
    """Register map reservation routes on the blueprint."""

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

    @bp.route('/map/quick-reservation', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.create')
    def quick_reservation():
        """
        Create a quick reservation from the map.

        Request body:
            customer_id: Customer ID
            furniture_ids: List of furniture IDs
            date: Reservation date YYYY-MM-DD
            num_people: Number of people (optional, default: capacity)
            notes: Notes (optional)

        Returns:
            JSON with reservation_id and ticket_number
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        customer_id = data.get('customer_id')
        furniture_ids = data.get('furniture_ids', [])
        date_str = data.get('date')
        num_people = data.get('num_people')
        notes = data.get('notes', '')

        # Validation
        if not customer_id:
            return jsonify({'success': False, 'error': 'Cliente requerido'}), 400

        if not furniture_ids or not isinstance(furniture_ids, list):
            return jsonify({'success': False, 'error': 'Mobiliario requerido'}), 400

        if not date_str:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

        # Check customer exists
        customer = get_customer_by_id(customer_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404

        # Check furniture availability
        availability = check_furniture_availability_bulk(
            furniture_ids=furniture_ids,
            dates=[date_str]
        )

        if availability.get('conflicts'):
            conflict_ids = list(availability['conflicts'].keys())
            return jsonify({
                'success': False,
                'error': 'Mobiliario no disponible',
                'conflicts': conflict_ids
            }), 409

        # Calculate num_people from furniture capacity if not provided
        if not num_people:
            furniture_list = get_all_furniture(active_only=True)
            furniture_map = {f['id']: f for f in furniture_list}
            num_people = sum(
                furniture_map.get(fid, {}).get('capacity', 2)
                for fid in furniture_ids
            )

        try:
            reservation_id, ticket_number = create_beach_reservation(
                customer_id=customer_id,
                reservation_date=date_str,
                num_people=num_people,
                furniture_ids=furniture_ids,
                observations=notes,
                created_by=current_user.username if current_user else 'system'
            )

            return jsonify({
                'success': True,
                'reservation_id': reservation_id,
                'ticket_number': ticket_number,
                'message': f'Reserva {ticket_number} creada exitosamente'
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error al crear reserva'}), 500
