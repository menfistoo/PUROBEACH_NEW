"""
Map daily positions API routes.
Endpoints for daily position overrides (furniture moved for specific dates).
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

from utils.decorators import permission_required
from models.furniture import get_furniture_by_id
from models.furniture_daily import (
    set_daily_position, get_daily_position, clear_daily_position,
    get_daily_positions_for_date
)


def register_routes(bp):
    """Register map daily position routes on the blueprint."""

    @bp.route('/map/furniture/<int:furniture_id>/daily-position', methods=['PUT'])
    @login_required
    @permission_required('beach.map.edit')
    def set_furniture_daily_position(furniture_id):
        """
        Set a daily position override for furniture (for specific date only).

        Request body:
            date: Date for position YYYY-MM-DD
            x: X position
            y: Y position

        Returns:
            JSON with success status
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        date_str = data.get('date')
        x = data.get('x')
        y = data.get('y')

        if not date_str:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

        if x is None or y is None:
            return jsonify({'success': False, 'error': 'Posicion X e Y requeridas'}), 400

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        try:
            position_id = set_daily_position(
                furniture_id=furniture_id,
                target_date=date_str,
                position_x=float(x),
                position_y=float(y),
                created_by=current_user.username if current_user else 'system'
            )

            return jsonify({
                'success': True,
                'position_id': position_id,
                'message': f'Posicion diaria guardada para {furniture["number"]}'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map/furniture/<int:furniture_id>/daily-position', methods=['DELETE'])
    @login_required
    @permission_required('beach.map.edit')
    def clear_furniture_daily_position(furniture_id):
        """
        Clear daily position override (revert to default position).

        Query params:
            date: Date to clear YYYY-MM-DD

        Returns:
            JSON with success status
        """
        date_str = request.args.get('date')

        if not date_str:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        cleared = clear_daily_position(furniture_id, date_str)

        if cleared:
            return jsonify({
                'success': True,
                'message': f'Posicion de {furniture["number"]} restaurada a default'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No habia posicion diaria para esta fecha'
            }), 404

    @bp.route('/map/daily-positions')
    @login_required
    @permission_required('beach.map.view')
    def list_daily_positions():
        """
        List all daily position overrides for a date.

        Query params:
            date: Date to check YYYY-MM-DD (default: today)

        Returns:
            JSON with positions list
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))

        positions = get_daily_positions_for_date(date_str)

        return jsonify({
            'success': True,
            'date': date_str,
            'positions': positions,
            'count': len(positions)
        })
