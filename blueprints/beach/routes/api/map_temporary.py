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
    delete_temporary_furniture, get_next_temp_furniture_number,
    partial_delete_temp_furniture, get_temp_furniture_date_info
)
from models.furniture_type import get_furniture_type_by_code


def register_routes(bp):
    """Register map temporary furniture routes on the blueprint."""

    @bp.route('/map/temporary-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.temporary')
    def create_temp_furniture():
        """
        Create temporary furniture for a date range.

        Request body:
            zone_id: Zone to add to
            furniture_type: Type code
            number: Furniture number (optional, auto-generated if not provided)
            capacity: Capacity
            position_x: X position
            position_y: Y position
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD, optional, defaults to start_date)
            width: Width (optional)
            height: Height (optional)

        Returns:
            JSON with furniture_id
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        # Required fields
        required = ['zone_id', 'furniture_type', 'capacity', 'start_date']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} requerido'}), 400

        # Get dates
        start_date = data['start_date']
        end_date = data.get('end_date') or start_date

        # Validate date range
        if start_date > end_date:
            return jsonify({
                'success': False,
                'error': 'La fecha de inicio no puede ser posterior a la fecha de fin'
            }), 400

        # Auto-generate number if not provided
        number = data.get('number')
        if not number:
            number = get_next_temp_furniture_number(
                data['furniture_type'],
                int(data['zone_id'])
            )

        # Get dimensions from furniture type
        furniture_type_code = data['furniture_type']
        ftype = get_furniture_type_by_code(furniture_type_code)
        if ftype:
            default_width = ftype.get('default_width', 60)
            default_height = ftype.get('default_height', 40)
        else:
            default_width = 60
            default_height = 40

        # Get rotation (0 = horizontal, 90 = vertical)
        rotation = int(data.get('rotation', 0))

        try:
            furniture_id = create_temporary_furniture(
                zone_id=int(data['zone_id']),
                furniture_type=furniture_type_code,
                number=number,
                capacity=int(data['capacity']),
                position_x=float(data.get('position_x', 100)),
                position_y=float(data.get('position_y', 100)),
                start_date=start_date,
                end_date=end_date,
                width=default_width,
                height=default_height,
                rotation=rotation
            )

            return jsonify({
                'success': True,
                'furniture_id': furniture_id,
                'number': number,
                'message': f'Mobiliario temporal {number} creado'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/temporary-furniture/<int:furniture_id>', methods=['DELETE'])
    @login_required
    @permission_required('beach.furniture.temporary')
    def delete_temp_furniture(furniture_id):
        """
        Delete temporary furniture (full or partial).

        Query params:
            delete_type: 'all' (delete entire range) or 'day' (delete single day)
            date: Required if delete_type='day', the date to remove (YYYY-MM-DD)

        Returns:
            JSON with success status and action taken
        """
        delete_type = request.args.get('delete_type', 'all')
        delete_date = request.args.get('date')

        try:
            if delete_type == 'day' and delete_date:
                # Partial deletion - remove only this date
                result = partial_delete_temp_furniture(furniture_id, delete_date)
                return jsonify({
                    'success': True,
                    'action': result['action'],
                    'furniture_ids': result['furniture_ids'],
                    'message': f'Mobiliario temporal eliminado para {delete_date}'
                })
            else:
                # Full deletion - remove entire furniture
                deleted = delete_temporary_furniture(furniture_id)

                if deleted:
                    return jsonify({
                        'success': True,
                        'action': 'deleted',
                        'message': 'Mobiliario temporal eliminado completamente'
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

    @bp.route('/map/temporary-furniture/<int:furniture_id>/info')
    @login_required
    @permission_required('beach.map.view')
    def temp_furniture_info(furniture_id):
        """
        Get date range info for temporary furniture.

        Returns:
            JSON with date info including is_multi_day flag
        """
        info = get_temp_furniture_date_info(furniture_id)

        if not info:
            return jsonify({'success': False, 'error': 'No encontrado'}), 404

        return jsonify({
            'success': True,
            **info
        })

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

    @bp.route('/map/temporary-furniture/next-number')
    @login_required
    @permission_required('beach.furniture.temporary')
    def get_next_number():
        """
        Get the next available number for temporary furniture.

        Query params:
            furniture_type: Type code (optional)
            zone_id: Zone ID (optional)

        Returns:
            JSON with next available number
        """
        furniture_type = request.args.get('furniture_type', 'hamaca')
        zone_id = request.args.get('zone_id', type=int)

        next_number = get_next_temp_furniture_number(furniture_type, zone_id)

        return jsonify({
            'success': True,
            'number': next_number
        })
