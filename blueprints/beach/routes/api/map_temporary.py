"""
Map temporary furniture API routes.
Endpoints for creating/managing temporary furniture (valid for specific dates only).
"""

from flask import current_app, request
from flask_login import login_required
from utils.datetime_helpers import get_today

from utils.decorators import permission_required
from utils.api_response import api_success, api_error
from models.furniture_daily import (
    create_temporary_furniture, get_temporary_furniture_for_date,
    delete_temporary_furniture, get_next_temp_furniture_number,
    partial_delete_temp_furniture, get_temp_furniture_date_info
)
from models.furniture_type import get_furniture_type_by_code
from models.zone import get_all_zones
from models.config import get_map_config


def calculate_zone_bounds(zone_id: int) -> dict:
    """
    Calculate the visual bounds of a zone on the map.
    Uses same logic as map_data.py to ensure consistency.

    Args:
        zone_id: Zone ID to calculate bounds for

    Returns:
        dict with x, y, width, height or None if zone not found
    """
    zones = get_all_zones(active_only=True)
    map_config = get_map_config()

    zone_padding = map_config['zone_padding']
    zone_height = map_config['zone_height']
    map_width = map_config['default_width']

    for idx, zone in enumerate(zones):
        if zone['id'] == zone_id:
            return {
                'x': zone_padding,
                'y': zone_padding + idx * (zone_height + zone_padding),
                'width': map_width - 2 * zone_padding,
                'height': zone_height
            }
    return None


def ensure_position_in_zone(position_x: float, position_y: float,
                            zone_id: int, furniture_width: float = 60,
                            furniture_height: float = 40) -> tuple:
    """
    Ensure position is within the zone bounds.
    If outside, calculate a default position inside the zone.

    Args:
        position_x: Requested X position
        position_y: Requested Y position
        zone_id: Target zone ID
        furniture_width: Width of furniture item
        furniture_height: Height of furniture item

    Returns:
        tuple (x, y) with valid position inside the zone
    """
    bounds = calculate_zone_bounds(zone_id)
    if not bounds:
        return position_x, position_y

    # Add margin for furniture size
    margin = 20
    min_x = bounds['x'] + margin
    max_x = bounds['x'] + bounds['width'] - furniture_width - margin
    min_y = bounds['y'] + margin
    max_y = bounds['y'] + bounds['height'] - furniture_height - margin

    # Check if position is inside zone bounds
    is_inside = (min_x <= position_x <= max_x and min_y <= position_y <= max_y)

    if is_inside:
        return position_x, position_y

    # Position is outside zone - calculate a default position
    # Place it in the center-left area of the zone
    default_x = min_x + 50
    default_y = min_y + (bounds['height'] // 2) - (furniture_height // 2)

    return default_x, default_y


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
            return api_error('Datos requeridos')

        # Required fields
        required = ['zone_id', 'furniture_type', 'capacity', 'start_date']
        for field in required:
            if not data.get(field):
                return api_error(f'{field} requerido')

        # Get dates
        start_date = data['start_date']
        end_date = data.get('end_date') or start_date

        # Validate date range
        if start_date > end_date:
            return api_error('La fecha de inicio no puede ser posterior a la fecha de fin')

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

        # Get requested position
        requested_x = float(data.get('position_x', 100))
        requested_y = float(data.get('position_y', 100))

        # Ensure position is within the zone bounds
        # This fixes the bug where changing zone in dropdown doesn't update position
        position_x, position_y = ensure_position_in_zone(
            requested_x, requested_y,
            int(data['zone_id']),
            default_width, default_height
        )

        try:
            furniture_id = create_temporary_furniture(
                zone_id=int(data['zone_id']),
                furniture_type=furniture_type_code,
                number=number,
                capacity=int(data['capacity']),
                position_x=position_x,
                position_y=position_y,
                start_date=start_date,
                end_date=end_date,
                width=default_width,
                height=default_height,
                rotation=rotation
            )

            return api_success(
                message=f'Mobiliario temporal {number} creado',
                furniture_id=furniture_id,
                number=number
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

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
                return api_success(
                    message=f'Mobiliario temporal eliminado para {delete_date}',
                    action=result['action'],
                    furniture_ids=result['furniture_ids']
                )
            else:
                # Full deletion - remove entire furniture
                deleted = delete_temporary_furniture(furniture_id)

                if deleted:
                    return api_success(
                        message='Mobiliario temporal eliminado completamente',
                        action='deleted'
                    )
                else:
                    return api_error('No se pudo eliminar', 404)

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Solicitud inválida')
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

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
            return api_error('No encontrado', 404)

        return api_success(**info)

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
        date_str = request.args.get('date', get_today().strftime('%Y-%m-%d'))
        zone_id = request.args.get('zone_id', type=int)

        furniture = get_temporary_furniture_for_date(date_str, zone_id)

        return api_success(
            date=date_str,
            furniture=furniture,
            count=len(furniture)
        )

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

        return api_success(number=next_number)
