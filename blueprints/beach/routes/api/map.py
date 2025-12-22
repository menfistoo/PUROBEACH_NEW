"""
Map API routes for interactive beach map.
Provides data endpoints for SVG rendering and furniture positioning.
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime

from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import (
    get_all_furniture, get_furniture_by_id, update_furniture_position,
    batch_update_furniture_positions, setup_initial_furniture_positions
)
from models.furniture_type import get_all_furniture_types
from models.state import get_all_states
from models.reservation import (
    get_furniture_availability_map, get_reservations_by_furniture,
    get_reservation_with_details, create_beach_reservation,
    check_furniture_availability_bulk
)
from models.customer import get_customer_by_id, search_customers_unified
from models.furniture_block import (
    create_furniture_block, get_blocks_for_date, get_block_by_id,
    delete_block, is_furniture_blocked, BLOCK_TYPES
)
from database import get_db


def register_routes(bp):
    """Register map API routes on the blueprint."""

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

    @bp.route('/map/data')
    @login_required
    @permission_required('beach.map.view')
    def map_data():
        """
        Get all data needed to render the interactive map.

        Query params:
            date: Date string YYYY-MM-DD (default: today)

        Returns:
            JSON with zones, furniture, furniture_types, states, availability
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))

        # Get all static data
        zones = get_all_zones(active_only=True)
        furniture = get_all_furniture(active_only=True)
        furniture_types = get_all_furniture_types(active_only=True)
        states = get_all_states(active_only=True)

        # Build lookup dicts
        furniture_types_map = {ft['type_code']: ft for ft in furniture_types}
        state_colors = {s['name']: s['color'] for s in states}

        # Get availability for the date
        availability = get_furniture_availability_map(date_str, date_str)

        # Build furniture availability lookup for the specific date
        furniture_availability = {}
        if availability and 'availability' in availability:
            for fid, dates_data in availability['availability'].items():
                if date_str in dates_data:
                    furniture_availability[int(fid)] = dates_data[date_str]

        # Calculate zone bounds for rendering (vertical stacking)
        zone_bounds = {}
        zone_padding = 20
        zone_height = 200
        map_width = 1200

        for idx, zone in enumerate(zones):
            zone_bounds[zone['id']] = {
                'x': zone_padding,
                'y': zone_padding + idx * (zone_height + zone_padding),
                'width': map_width - 2 * zone_padding,
                'height': zone_height
            }

        # Calculate total map height based on zones
        total_height = zone_padding + len(zones) * (zone_height + zone_padding)

        return jsonify({
            'success': True,
            'date': date_str,
            'zones': zones,
            'zone_bounds': zone_bounds,
            'furniture': furniture,
            'furniture_types': furniture_types_map,
            'states': states,
            'state_colors': state_colors,
            'availability': furniture_availability,
            'summary': availability.get('summary', {}).get(date_str, {}),
            'map_dimensions': {
                'width': map_width,
                'height': max(800, total_height)
            }
        })

    @bp.route('/map/furniture/<int:furniture_id>/position', methods=['PUT'])
    @login_required
    @permission_required('beach.map.edit')
    def update_position(furniture_id):
        """
        Update furniture position (drag-drop from map).

        Request body:
            x: New X position
            y: New Y position
            rotation: New rotation angle (optional)

        Returns:
            JSON with success status
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        x = data.get('x')
        y = data.get('y')
        rotation = data.get('rotation')

        if x is None or y is None:
            return jsonify({'success': False, 'error': 'Posición X e Y requeridas'}), 400

        try:
            result = update_furniture_position(furniture_id, x, y, rotation)
            if result:
                return jsonify({'success': True, 'furniture_id': furniture_id})
            else:
                return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/furniture/batch-position', methods=['PUT'])
    @login_required
    @permission_required('beach.map.edit')
    def batch_update_positions():
        """
        Batch update furniture positions.

        Request body:
            updates: List of {id, x, y, rotation?}

        Returns:
            JSON with success status and count
        """
        data = request.get_json()

        if not data or 'updates' not in data:
            return jsonify({'success': False, 'error': 'Lista de actualizaciones requerida'}), 400

        updates = data['updates']

        if not isinstance(updates, list):
            return jsonify({'success': False, 'error': 'updates debe ser una lista'}), 400

        try:
            count = batch_update_furniture_positions(updates)
            return jsonify({
                'success': True,
                'updated': count,
                'total': len(updates)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/auto-position', methods=['POST'])
    @login_required
    @permission_required('beach.map.edit')
    def auto_position():
        """
        Auto-position all furniture in grid layout.
        Used for initial setup when positions are all at 0,0.

        Returns:
            JSON with counts per zone and total
        """
        try:
            result = setup_initial_furniture_positions()
            return jsonify({
                'success': True,
                'zones': result['zones'],
                'total': result['total']
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/availability')
    @login_required
    @permission_required('beach.map.view')
    def map_availability():
        """
        Get availability for date range (for calendar/timeline view).

        Query params:
            date_from: Start date YYYY-MM-DD
            date_to: End date YYYY-MM-DD (default: same as date_from)
            zone_id: Filter by zone (optional)

        Returns:
            JSON availability matrix
        """
        date_from = request.args.get('date_from', date.today().strftime('%Y-%m-%d'))
        date_to = request.args.get('date_to', date_from)
        zone_id = request.args.get('zone_id', type=int)

        try:
            availability = get_furniture_availability_map(
                date_from, date_to,
                zone_id=zone_id
            )

            return jsonify({
                'success': True,
                'date_from': date_from,
                'date_to': date_to,
                **availability
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/furniture/<int:furniture_id>/details')
    @login_required
    @permission_required('beach.map.view')
    def furniture_details(furniture_id):
        """
        Get detailed furniture info including current reservation.

        Query params:
            date: Date string YYYY-MM-DD (default: today)

        Returns:
            JSON with furniture details, reservation, customer info
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))

        # Get furniture info
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        # Get furniture type config
        furniture_types = get_all_furniture_types(active_only=True)
        type_config = next(
            (ft for ft in furniture_types if ft['type_code'] == furniture['furniture_type']),
            {}
        )

        # Check for reservations on this furniture for this date
        reservations = get_reservations_by_furniture(furniture_id, date_str)

        reservation_data = None
        customer_data = None

        if reservations:
            # Get the active reservation (first non-releasing state)
            for res in reservations:
                res_details = get_reservation_with_details(res['id'])
                if res_details:
                    reservation_data = {
                        'id': res_details['id'],
                        'ticket_number': res_details.get('ticket_number'),
                        'current_state': res_details.get('current_state'),
                        'current_states': res_details.get('current_states'),
                        'display_color': res_details.get('display_color'),
                        'num_people': res_details.get('num_people'),
                        'time_slot': res_details.get('time_slot'),
                        'notes': res_details.get('notes'),
                        'reservation_date': res_details.get('reservation_date'),
                        'start_date': res_details.get('start_date'),
                        'end_date': res_details.get('end_date'),
                        'created_at': res_details.get('created_at'),
                        'furniture': res_details.get('furniture', []),
                        'tags': res_details.get('tags', [])
                    }

                    # Get customer info
                    customer_id = res_details.get('customer_id')
                    if customer_id:
                        customer = get_customer_by_id(customer_id)
                        if customer:
                            customer_data = {
                                'id': customer['id'],
                                'first_name': customer.get('first_name'),
                                'last_name': customer.get('last_name'),
                                'full_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                                'customer_type': customer.get('customer_type'),
                                'room_number': customer.get('room_number'),
                                'phone': customer.get('phone'),
                                'email': customer.get('email'),
                                'vip_status': customer.get('vip_status', 0),
                                'total_visits': customer.get('total_visits', 0),
                                'notes': customer.get('notes')
                            }
                    break

        # Build response
        return jsonify({
            'success': True,
            'date': date_str,
            'furniture': {
                'id': furniture['id'],
                'number': furniture['number'],
                'zone_id': furniture['zone_id'],
                'zone_name': furniture.get('zone_name'),
                'furniture_type': furniture['furniture_type'],
                'type_name': type_config.get('display_name', furniture['furniture_type']),
                'capacity': furniture['capacity'],
                'features': furniture.get('features', '').split(',') if furniture.get('features') else [],
                'position_x': furniture['position_x'],
                'position_y': furniture['position_y'],
                'is_temporary': furniture.get('is_temporary', 0),
                'active': furniture.get('active', 1)
            },
            'reservation': reservation_data,
            'customer': customer_data,
            'is_available': reservation_data is None
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

    # =========================================================================
    # FURNITURE BLOCKING ENDPOINTS
    # =========================================================================

    @bp.route('/map/furniture/<int:furniture_id>/block', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.block')
    def block_furniture(furniture_id):
        """
        Block furniture for a date range.

        Request body:
            start_date: Block start date YYYY-MM-DD
            end_date: Block end date YYYY-MM-DD
            block_type: Type (maintenance, vip_hold, event, other)
            reason: Reason for blocking
            notes: Additional notes

        Returns:
            JSON with block ID
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        start_date = data.get('start_date')
        end_date = data.get('end_date', start_date)
        block_type = data.get('block_type', 'other')
        reason = data.get('reason', '')
        notes = data.get('notes', '')

        if not start_date:
            return jsonify({'success': False, 'error': 'Fecha de inicio requerida'}), 400

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        try:
            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date=start_date,
                end_date=end_date,
                block_type=block_type,
                reason=reason,
                notes=notes,
                created_by=current_user.username if current_user else 'system'
            )

            return jsonify({
                'success': True,
                'block_id': block_id,
                'message': f'Mobiliario {furniture["number"]} bloqueado'
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error al bloquear mobiliario'}), 500

    @bp.route('/map/furniture/<int:furniture_id>/block', methods=['DELETE'])
    @login_required
    @permission_required('beach.furniture.block')
    def unblock_furniture(furniture_id):
        """
        Remove a block from furniture.

        Query params:
            date: Date to unblock (finds block covering this date)
            block_id: Specific block ID to remove

        Returns:
            JSON with success status
        """
        date_str = request.args.get('date')
        block_id = request.args.get('block_id', type=int)

        if block_id:
            # Delete specific block
            block = get_block_by_id(block_id)
            if not block:
                return jsonify({'success': False, 'error': 'Bloqueo no encontrado'}), 404

            if block['furniture_id'] != furniture_id:
                return jsonify({'success': False, 'error': 'Bloqueo no corresponde al mobiliario'}), 400

            delete_block(block_id)
            return jsonify({'success': True, 'message': 'Bloqueo eliminado'})

        elif date_str:
            # Find and delete block for this date
            block = is_furniture_blocked(furniture_id, date_str)
            if not block:
                return jsonify({'success': False, 'error': 'No hay bloqueo para esta fecha'}), 404

            delete_block(block['id'])
            return jsonify({'success': True, 'message': 'Bloqueo eliminado'})

        else:
            return jsonify({'success': False, 'error': 'Se requiere date o block_id'}), 400

    @bp.route('/map/blocks')
    @login_required
    @permission_required('beach.map.view')
    def list_blocks():
        """
        List all blocks for a date.

        Query params:
            date: Date to check YYYY-MM-DD (default: today)
            zone_id: Filter by zone (optional)

        Returns:
            JSON with blocks list
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        zone_id = request.args.get('zone_id', type=int)

        blocks = get_blocks_for_date(date_str, zone_id)

        return jsonify({
            'success': True,
            'date': date_str,
            'blocks': blocks,
            'block_types': BLOCK_TYPES
        })
