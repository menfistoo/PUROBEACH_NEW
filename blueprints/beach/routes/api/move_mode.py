"""
Move mode API endpoints.

Handles furniture reassignment operations during move mode:
- Unassign furniture from reservations
- Assign furniture to reservations
- Get reservation pool data
- Get preference-based furniture matches
"""

from flask import current_app, jsonify, request
from flask_login import login_required
from utils.decorators import permission_required
from models.move_mode import (
    unassign_furniture_for_date,
    assign_furniture_for_date,
    get_reservation_pool_data,
    get_furniture_preference_matches,
    get_unassigned_reservations
)


def _validate_furniture_request(data):
    """
    Validate common fields for furniture assign/unassign requests.

    Args:
        data: JSON request data

    Returns:
        Tuple of (reservation_id, furniture_ids, target_date, error_response)
        error_response is None if validation passes, otherwise a tuple of (response, status_code)
    """
    if not data:
        return None, None, None, (jsonify({'success': False, 'error': 'No se recibieron datos'}), 400)

    reservation_id = data.get('reservation_id')
    furniture_ids = data.get('furniture_ids', [])
    target_date = data.get('date')

    if not reservation_id:
        return None, None, None, (jsonify({'success': False, 'error': 'reservation_id es requerido'}), 400)
    if not target_date:
        return None, None, None, (jsonify({'success': False, 'error': 'date es requerido'}), 400)

    return reservation_id, furniture_ids, target_date, None


def register_routes(bp):
    """Register move mode API routes on the blueprint."""

    @bp.route('/move-mode/unassign', methods=['POST'])
    @login_required
    @permission_required('beach.map.edit')
    def move_mode_unassign():
        """
        Unassign furniture from a reservation for a specific date.

        Request JSON:
        {
            "reservation_id": int,
            "furniture_ids": [int, ...],
            "date": "YYYY-MM-DD"
        }

        Response JSON:
        {
            "success": true,
            "unassigned_count": int,
            "furniture_ids": [int, ...],
            "reservation_id": int,
            "date": "YYYY-MM-DD"
        }
        """
        try:
            reservation_id, furniture_ids, target_date, error = _validate_furniture_request(request.get_json())
            if error:
                return error

            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=furniture_ids,
                assignment_date=target_date
            )
            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

    @bp.route('/move-mode/assign', methods=['POST'])
    @login_required
    @permission_required('beach.map.edit')
    def move_mode_assign():
        """
        Assign furniture to a reservation for a specific date.

        Request JSON:
        {
            "reservation_id": int,
            "furniture_ids": [int, ...],
            "date": "YYYY-MM-DD"
        }

        Response JSON (success):
        {
            "success": true,
            "assigned_count": int,
            "furniture_ids": [int, ...],
            "reservation_id": int,
            "date": "YYYY-MM-DD"
        }

        Response JSON (conflict):
        {
            "success": false,
            "error": "Mobiliario ocupado por John Doe",
            "conflicts": [...]
        }
        """
        try:
            reservation_id, furniture_ids, target_date, error = _validate_furniture_request(request.get_json())
            if error:
                return error

            result = assign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=furniture_ids,
                assignment_date=target_date
            )

            if not result.get('success'):
                return jsonify(result), 409

            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

    @bp.route('/move-mode/pool-data', methods=['GET'])
    @login_required
    @permission_required('beach.map.view')
    def move_mode_pool_data():
        """
        Get comprehensive reservation data for the pool panel.

        Auto-syncs customer preferences to reservation if reservation has none.

        Query params:
        - reservation_id: int (required)
        - date: YYYY-MM-DD (required)

        Response JSON:
        {
            "reservation_id": int,
            "customer_name": str,
            "room_number": str,
            "num_people": int,
            "preferences": [...],
            "original_furniture": [...],
            "is_multiday": bool,
            "total_days": int,
            ...
        }
        """
        try:
            reservation_id = request.args.get('reservation_id', type=int)
            target_date = request.args.get('date')

            if not reservation_id:
                return jsonify({'error': 'reservation_id es requerido'}), 400
            if not target_date:
                return jsonify({'error': 'date es requerido'}), 400

            result = get_reservation_pool_data(reservation_id, target_date)

            if 'error' in result:
                return jsonify(result), 404

            # Auto-sync customer preferences if reservation has none
            if not result.get('preferences') and result.get('customer_id'):
                from models.characteristic_assignments import (
                    get_customer_characteristics,
                    set_reservation_characteristics
                )
                customer_chars = get_customer_characteristics(result['customer_id'])
                if customer_chars:
                    # Sync customer preferences to reservation
                    char_ids = [c['id'] for c in customer_chars]
                    set_reservation_characteristics(reservation_id, char_ids)
                    # Reload pool data with synced preferences
                    result = get_reservation_pool_data(reservation_id, target_date)

            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500

    @bp.route('/move-mode/preferences-match', methods=['GET'])
    @login_required
    @permission_required('beach.map.view')
    def move_mode_preferences_match():
        """
        Get furniture with preference match scores.

        Query params:
        - date: YYYY-MM-DD (required)
        - preferences: comma-separated preference codes (optional)
        - zone_id: int (optional)

        Response JSON:
        {
            "furniture": [
                {
                    "id": int,
                    "number": str,
                    "available": bool,
                    "match_score": float (0-1),
                    "matched_preferences": [str, ...]
                },
                ...
            ],
            "date": "YYYY-MM-DD",
            "preferences_requested": [str, ...]
        }
        """
        try:
            target_date = request.args.get('date')
            preferences_str = request.args.get('preferences', '')
            zone_id = request.args.get('zone_id', type=int)

            if not target_date:
                return jsonify({'error': 'date es requerido'}), 400

            preference_codes = [p.strip() for p in preferences_str.split(',') if p.strip()]

            result = get_furniture_preference_matches(
                preference_codes=preference_codes,
                target_date=target_date,
                zone_id=zone_id
            )

            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500

    @bp.route('/move-mode/unassigned', methods=['GET'])
    @login_required
    @permission_required('beach.map.view')
    def move_mode_unassigned():
        """
        Get all reservations with insufficient furniture for a date.

        Query params:
        - date: YYYY-MM-DD (required)

        Response JSON:
        {
            "reservation_ids": [int, ...],
            "date": "YYYY-MM-DD"
        }
        """
        try:
            target_date = request.args.get('date')

            if not target_date:
                return jsonify({'error': 'date es requerido'}), 400

            reservation_ids = get_unassigned_reservations(target_date)

            return jsonify({
                'reservation_ids': reservation_ids,
                'date': target_date
            })

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500

    @bp.route('/move-mode/unassigned-global', methods=['GET'])
    @login_required
    @permission_required('beach.map.view')
    def move_mode_unassigned_global():
        """
        Get all reservations with insufficient furniture for the next 7 days.

        Response JSON:
        {
            "count": int,
            "dates": ["YYYY-MM-DD", ...],
            "first_date": "YYYY-MM-DD" or null,
            "by_date": {"YYYY-MM-DD": [reservation_ids], ...}
        }
        """
        try:
            from models.move_mode import get_unassigned_reservations_global
            result = get_unassigned_reservations_global(days_ahead=7)
            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'error': 'Error interno del servidor'}), 500
