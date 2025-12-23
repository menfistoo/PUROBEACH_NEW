"""
Map temporary furniture API routes.
Endpoints for creating/managing temporary furniture (valid for specific dates only).
"""

from flask import request, jsonify
from flask_login import login_required
from datetime import date

from utils.decorators import permission_required
from models.furniture_daily import (
    create_temporary_furniture, get_temporary_furniture_for_date,
    delete_temporary_furniture
)


def register_routes(bp):
    """Register map temporary furniture routes on the blueprint."""

    @bp.route('/map/temporary-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.temporary')
    def create_temp_furniture():
        """
        Create temporary furniture for a specific date.

        Request body:
            zone_id: Zone to add to
            furniture_type: Type code
            number: Furniture number
            capacity: Capacity
            position_x: X position
            position_y: Y position
            date: Date this furniture is valid for
            width: Width (optional)
            height: Height (optional)

        Returns:
            JSON with furniture_id
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        required = ['zone_id', 'furniture_type', 'number', 'capacity', 'date']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} requerido'}), 400

        try:
            furniture_id = create_temporary_furniture(
                zone_id=int(data['zone_id']),
                furniture_type=data['furniture_type'],
                number=data['number'],
                capacity=int(data['capacity']),
                position_x=float(data.get('position_x', 100)),
                position_y=float(data.get('position_y', 100)),
                target_date=data['date'],
                width=float(data.get('width', 60)),
                height=float(data.get('height', 40)),
                rotation=int(data.get('rotation', 0))
            )

            return jsonify({
                'success': True,
                'furniture_id': furniture_id,
                'message': f'Mobiliario temporal {data["number"]} creado'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/temporary-furniture/<int:furniture_id>', methods=['DELETE'])
    @login_required
    @permission_required('beach.furniture.temporary')
    def delete_temp_furniture(furniture_id):
        """
        Delete temporary furniture.

        Returns:
            JSON with success status
        """
        try:
            deleted = delete_temporary_furniture(furniture_id)

            if deleted:
                return jsonify({
                    'success': True,
                    'message': 'Mobiliario temporal eliminado'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No se pudo eliminar'
                }), 404

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/temporary-furniture')
    @login_required
    @permission_required('beach.map.view')
    def list_temp_furniture():
        """
        List temporary furniture for a date.

        Query params:
            date: Date to check YYYY-MM-DD (default: today)
            zone_id: Filter by zone (optional)

        Returns:
            JSON with temporary furniture list
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        zone_id = request.args.get('zone_id', type=int)

        furniture = get_temporary_furniture_for_date(date_str, zone_id)

        return jsonify({
            'success': True,
            'date': date_str,
            'furniture': furniture,
            'count': len(furniture)
        })
