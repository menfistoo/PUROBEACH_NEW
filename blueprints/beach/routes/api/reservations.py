"""
Reservation API routes including availability, multi-day, and suggestions.
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.reservation import (
    get_reservation_with_details, get_available_furniture,
    get_status_history, add_reservation_state, remove_reservation_state,
    check_furniture_availability_bulk, check_duplicate_reservation,
    get_furniture_availability_map, get_conflicting_reservations,
    create_linked_multiday_reservations, get_multiday_summary,
    cancel_multiday_reservations, update_multiday_reservations,
    suggest_furniture_for_reservation, build_furniture_occupancy_map,
    validate_cluster_contiguity
)
from datetime import date


def register_routes(bp):
    """Register reservation API routes on the blueprint."""

    # ============================================================================
    # RESERVATION API ROUTES
    # ============================================================================

    @bp.route('/reservations/<int:reservation_id>')
    @login_required
    @permission_required('beach.reservations.view')
    def reservation_detail(reservation_id):
        """Get reservation details as JSON."""
        reservation = get_reservation_with_details(reservation_id)
        if not reservation:
            return jsonify({'error': 'Reserva no encontrada'}), 404

        return jsonify({
            'id': reservation['id'],
            'ticket_number': reservation.get('ticket_number'),
            'customer_id': reservation['customer_id'],
            'customer_name': reservation['customer_name'],
            'customer_type': reservation['customer_type'],
            'reservation_date': reservation.get('reservation_date'),
            'num_people': reservation['num_people'],
            'current_state': reservation.get('current_state'),
            'current_states': reservation.get('current_states'),
            'display_color': reservation.get('display_color'),
            'furniture': reservation.get('furniture', []),
            'tags': reservation.get('tags', []),
            'notes': reservation.get('notes'),
            'preferences': reservation.get('preferences')
        })

    @bp.route('/reservations/<int:reservation_id>/toggle-state', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.change_state')
    def toggle_state(reservation_id):
        """Toggle a state on/off for a reservation."""
        data = request.get_json()
        state_name = data.get('state')
        action = data.get('action', 'toggle')

        if not state_name:
            return jsonify({'error': 'Estado requerido'}), 400

        reservation = get_reservation_with_details(reservation_id)
        if not reservation:
            return jsonify({'error': 'Reserva no encontrada'}), 404

        try:
            current_states = reservation.get('current_states', '')
            has_state = state_name in [s.strip() for s in current_states.split(',') if s.strip()]

            if action == 'add' or (action == 'toggle' and not has_state):
                add_reservation_state(
                    reservation_id, state_name,
                    changed_by=current_user.username if current_user else 'system'
                )
                return jsonify({'success': True, 'action': 'added', 'state': state_name})

            elif action == 'remove' or (action == 'toggle' and has_state):
                remove_reservation_state(
                    reservation_id, state_name,
                    changed_by=current_user.username if current_user else 'system'
                )
                return jsonify({'success': True, 'action': 'removed', 'state': state_name})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/reservations/<int:reservation_id>/history')
    @login_required
    @permission_required('beach.reservations.view')
    def reservation_history(reservation_id):
        """Get reservation state change history."""
        history = get_status_history(reservation_id)

        return jsonify({
            'history': [{
                'status_type': h.get('status_type'),
                'action': h.get('action'),
                'changed_by': h.get('changed_by'),
                'notes': h.get('notes'),
                'created_at': h.get('created_at')
            } for h in history]
        })

    @bp.route('/furniture/available')
    @login_required
    @permission_required('beach.reservations.view')
    def available_furniture():
        """Get available furniture for a date."""
        date_str = request.args.get('date')
        zone_id = request.args.get('zone_id', type=int)
        furniture_type = request.args.get('type')

        if not date_str:
            date_str = date.today().strftime('%Y-%m-%d')

        furniture = get_available_furniture(date_str, zone_id, furniture_type)

        return jsonify({
            'furniture': [{
                'id': f['id'],
                'number': f['number'],
                'furniture_type': f['furniture_type'],
                'type_name': f.get('type_name'),
                'zone_id': f['zone_id'],
                'zone_name': f.get('zone_name'),
                'capacity': f['capacity'],
                'position_x': f['position_x'],
                'position_y': f['position_y']
            } for f in furniture]
        })

    # ============================================================================
    # BULK AVAILABILITY API ENDPOINTS
    # ============================================================================

    @bp.route('/reservations/check-availability', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def check_availability_bulk():
        """Check availability for multiple furniture items across multiple dates."""
        data = request.get_json()
        furniture_ids = data.get('furniture_ids', [])
        dates = data.get('dates', [])
        exclude_reservation_id = data.get('exclude_reservation_id')

        if not furniture_ids:
            return jsonify({'error': 'furniture_ids requeridos'}), 400
        if not dates:
            return jsonify({'error': 'dates requeridos'}), 400

        result = check_furniture_availability_bulk(
            furniture_ids=furniture_ids,
            dates=dates,
            exclude_reservation_id=exclude_reservation_id
        )

        return jsonify(result)

    @bp.route('/reservations/check-duplicate', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def check_duplicate():
        """Check for duplicate reservation (same customer + dates)."""
        data = request.get_json()
        customer_id = data.get('customer_id')
        dates = data.get('dates', [])
        exclude_reservation_id = data.get('exclude_reservation_id')

        if not customer_id:
            return jsonify({'error': 'customer_id requerido'}), 400
        if not dates:
            return jsonify({'error': 'dates requeridos'}), 400

        is_duplicate, existing = check_duplicate_reservation(
            customer_id=customer_id,
            dates=dates,
            exclude_reservation_id=exclude_reservation_id
        )

        return jsonify({
            'is_duplicate': is_duplicate,
            'existing_reservation': existing
        })

    @bp.route('/reservations/availability-map')
    @login_required
    @permission_required('beach.reservations.view')
    def availability_map():
        """Get availability map for date range (calendar/grid view)."""
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        zone_id = request.args.get('zone_id', type=int)
        furniture_type = request.args.get('type')

        if not date_from or not date_to:
            return jsonify({'error': 'date_from y date_to requeridos'}), 400

        result = get_furniture_availability_map(
            date_from=date_from,
            date_to=date_to,
            zone_id=zone_id,
            furniture_type=furniture_type
        )

        return jsonify(result)

    @bp.route('/reservations/conflicts')
    @login_required
    @permission_required('beach.reservations.view')
    def get_conflicts():
        """Get conflicting reservations for furniture on a date."""
        furniture_ids_str = request.args.get('furniture_ids', '')
        date_str = request.args.get('date')
        exclude_reservation_id = request.args.get('exclude_reservation_id', type=int)

        if not furniture_ids_str or not date_str:
            return jsonify({'error': 'furniture_ids y date requeridos'}), 400

        try:
            furniture_ids = [int(x) for x in furniture_ids_str.split(',')]
        except ValueError:
            return jsonify({'error': 'furniture_ids debe ser lista de enteros'}), 400

        conflicts = get_conflicting_reservations(
            furniture_ids=furniture_ids,
            date=date_str,
            exclude_reservation_id=exclude_reservation_id
        )

        return jsonify({'conflicts': conflicts})

    # ============================================================================
    # MULTI-DAY RESERVATION API ENDPOINTS
    # ============================================================================

    @bp.route('/reservations/create-multiday', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.create')
    def create_multiday():
        """Create multi-day linked reservations."""
        data = request.get_json()

        customer_id = data.get('customer_id')
        dates = data.get('dates', [])
        num_people = data.get('num_people', 1)
        furniture_ids = data.get('furniture_ids')
        furniture_by_date = data.get('furniture_by_date')

        if not customer_id:
            return jsonify({'success': False, 'error': 'customer_id requerido'}), 400
        if not dates:
            return jsonify({'success': False, 'error': 'dates requerido'}), 400
        if not furniture_ids and not furniture_by_date:
            return jsonify({'success': False, 'error': 'furniture_ids o furniture_by_date requerido'}), 400

        try:
            result = create_linked_multiday_reservations(
                customer_id=customer_id,
                dates=dates,
                num_people=num_people,
                furniture_ids=furniture_ids,
                furniture_by_date=furniture_by_date,
                time_slot=data.get('time_slot', 'all_day'),
                payment_status=data.get('payment_status', 'NO'),
                charge_to_room=1 if data.get('charge_to_room') else 0,
                charge_reference=data.get('charge_reference', ''),
                price=data.get('price', 0.0),
                preferences=data.get('preferences', ''),
                observations=data.get('observations', ''),
                created_by=current_user.username if current_user else None,
                check_in_date=data.get('check_in_date'),
                check_out_date=data.get('check_out_date'),
                hamaca_included=data.get('hamaca_included', 1)
            )

            return jsonify(result)

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

    @bp.route('/reservations/<int:reservation_id>/multiday-summary')
    @login_required
    @permission_required('beach.reservations.view')
    def multiday_summary(reservation_id):
        """Get summary of multi-day reservation group."""
        summary = get_multiday_summary(reservation_id)

        if not summary:
            return jsonify({'error': 'Reserva no encontrada'}), 404

        return jsonify(summary)

    @bp.route('/reservations/<int:reservation_id>/cancel-multiday', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.change_state')
    def cancel_multiday(reservation_id):
        """Cancel all reservations in a multi-day group."""
        data = request.get_json() or {}

        try:
            result = cancel_multiday_reservations(
                parent_id=reservation_id,
                cancelled_by=current_user.username if current_user else 'system',
                notes=data.get('notes', ''),
                cancel_children=data.get('cancel_children', True)
            )

            return jsonify(result)

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/reservations/<int:reservation_id>/update-multiday', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def update_multiday(reservation_id):
        """Update common fields across all linked reservations."""
        data = request.get_json() or {}
        update_children = data.pop('update_children', True)
        data.pop('reservation_id', None)

        try:
            result = update_multiday_reservations(
                parent_id=reservation_id,
                update_children=update_children,
                **data
            )

            return jsonify(result)

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ============================================================================
    # SMART SUGGESTIONS API ENDPOINTS
    # ============================================================================

    @bp.route('/reservations/suggest-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def suggest_furniture():
        """Get smart furniture suggestions for a reservation."""
        data = request.get_json()

        dates = data.get('dates', [])
        num_people = data.get('num_people', 1)
        preferences = data.get('preferences', '')
        customer_id = data.get('customer_id')
        zone_id = data.get('zone_id')
        limit = data.get('limit', 5)

        if not dates:
            return jsonify({'success': False, 'error': 'dates requerido'}), 400

        try:
            result = suggest_furniture_for_reservation(
                dates=dates,
                num_people=num_people,
                preferences_csv=preferences,
                customer_id=customer_id,
                zone_id=zone_id,
                limit=limit
            )

            return jsonify(result)

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/reservations/validate-contiguity', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def validate_contiguity():
        """Validate if selected furniture forms a contiguous cluster."""
        data = request.get_json()

        furniture_ids = data.get('furniture_ids', [])
        date_str = data.get('date')

        if not furniture_ids:
            return jsonify({'error': 'furniture_ids requerido'}), 400
        if not date_str:
            return jsonify({'error': 'date requerido'}), 400

        try:
            occupancy_map = build_furniture_occupancy_map(date_str)
            result = validate_cluster_contiguity(furniture_ids, occupancy_map)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
