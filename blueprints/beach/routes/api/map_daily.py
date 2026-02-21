"""
Map daily positions API routes.
Endpoints for daily position overrides (furniture moved for specific dates).
"""

from flask import current_app, request
from flask_login import login_required, current_user
from utils.datetime_helpers import get_today

from utils.decorators import permission_required
from utils.api_response import api_success, api_error
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
            return api_error('Datos requeridos')

        date_str = data.get('date')
        x = data.get('x')
        y = data.get('y')

        if not date_str:
            return api_error('Fecha requerida')

        if x is None or y is None:
            return api_error('Posicion X e Y requeridas')

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return api_error('Mobiliario no encontrado', 404)

        try:
            position_id = set_daily_position(
                furniture_id=furniture_id,
                target_date=date_str,
                position_x=float(x),
                position_y=float(y),
                created_by=current_user.username if current_user else 'system'
            )

            return api_success(
                message=f'Posicion diaria guardada para {furniture["number"]}',
                position_id=position_id
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

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
            return api_error('Fecha requerida')

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return api_error('Mobiliario no encontrado', 404)

        cleared = clear_daily_position(furniture_id, date_str)

        if cleared:
            return api_success(
                message=f'Posicion de {furniture["number"]} restaurada a default'
            )
        else:
            return api_error('No habia posicion diaria para esta fecha', 404)

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
        date_str = request.args.get('date', get_today().strftime('%Y-%m-%d'))

        positions = get_daily_positions_for_date(date_str)

        return api_success(
            date=date_str,
            positions=positions,
            count=len(positions)
        )
