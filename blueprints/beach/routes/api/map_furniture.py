"""
Map furniture API routes.
Endpoints for furniture positioning and details.
"""

from flask import request, jsonify
from flask_login import login_required
from datetime import date

from utils.decorators import permission_required
from models.furniture import (
    get_furniture_by_id, update_furniture_position,
    batch_update_furniture_positions, setup_initial_furniture_positions,
    get_all_furniture
)
from models.furniture_type import get_all_furniture_types
from models.reservation import get_reservations_by_furniture, get_reservation_with_details
from models.customer import get_customer_by_id


def register_routes(bp):
    """Register map furniture routes on the blueprint."""

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
            return jsonify({'success': False, 'error': 'Posicion X e Y requeridas'}), 400

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
