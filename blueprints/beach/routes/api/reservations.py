"""
Reservation API routes including availability, multi-day, and suggestions.
"""

from flask import current_app, request, jsonify
from flask_login import login_required, current_user
from utils.decorators import permission_required
from utils.audit import log_create, log_update, log_delete
from utils.api_response import api_success, api_error
from models.characteristic_assignments import get_reservation_characteristics, set_reservation_characteristics_by_codes
from models.reservation import (
    get_reservation_with_details, get_available_furniture,
    get_status_history, add_reservation_state, remove_reservation_state,
    check_furniture_availability_bulk, check_duplicate_reservation,
    check_duplicate_by_room, get_furniture_availability_map,
    get_conflicting_reservations, create_linked_multiday_reservations,
    get_multiday_summary, cancel_multiday_reservations,
    update_multiday_reservations, suggest_furniture_for_reservation,
    build_furniture_occupancy_map, validate_cluster_contiguity,
    InvalidStateTransitionError, get_allowed_transitions,
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
            return api_error('Reserva no encontrada', 404)

        return api_success(data={
            'id': reservation['id'],
            'ticket_number': reservation.get('ticket_number'),
            'customer_id': reservation['customer_id'],
            'customer_name': reservation['customer_name'],
            'customer_type': reservation['customer_type'],
            'customer_room': reservation.get('customer_room'),
            'customer_phone': reservation.get('customer_phone'),
            'customer_email': reservation.get('customer_email'),
            'reservation_date': reservation.get('reservation_date'),
            'start_date': reservation.get('start_date'),
            'end_date': reservation.get('end_date'),
            'num_people': reservation['num_people'],
            'current_state': reservation.get('current_state'),
            'current_states': reservation.get('current_states'),
            'display_color': reservation.get('display_color'),
            'furniture': reservation.get('furniture', []),
            'tags': reservation.get('tags', []),
            'notes': reservation.get('notes'),
            'observations': reservation.get('observations'),
            'preferences': reservation.get('preferences'),
            'paid': reservation.get('paid', 0),
            'final_price': reservation.get('final_price', 0),
            'price': reservation.get('price', 0),
            'package_name': reservation.get('package_name'),
            'payment_ticket_number': reservation.get('payment_ticket_number'),
            'payment_method': reservation.get('payment_method'),
            'room_changed': reservation.get('room_changed', 0),
            'reservation_characteristics': get_reservation_characteristics(reservation_id),
        })

    @bp.route('/reservations/<int:reservation_id>', methods=['PATCH'])
    @login_required
    @permission_required('beach.reservations.edit')
    def reservation_update(reservation_id):
        """Quick update reservation fields."""
        from models.reservation import update_beach_reservation

        reservation = get_reservation_with_details(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        data = request.get_json()
        allowed_fields = ['num_people', 'paid', 'notes', 'final_price',
                          'payment_ticket_number', 'payment_method']

        # Map frontend field names to database column names
        field_mapping = {'observations': 'notes'}
        mapped_data = {}
        for k, v in data.items():
            mapped_key = field_mapping.get(k, k)
            if mapped_key in allowed_fields:
                mapped_data[mapped_key] = v
        updates = mapped_data

        try:
            # Capture before state for audit log
            before_state = {
                'id': reservation['id'],
                'customer_id': reservation.get('customer_id'),
                'num_people': reservation.get('num_people'),
                'current_states': reservation.get('current_states'),
                'notes': reservation.get('notes'),
                'paid': reservation.get('paid'),
                'final_price': reservation.get('final_price'),
                'payment_method': reservation.get('payment_method'),
                'payment_ticket_number': reservation.get('payment_ticket_number')
            }

            # Handle state change separately
            if 'state_id' in data:
                state_id = data['state_id']
                # Get state name from ID
                from database import get_db
                with get_db() as conn:
                    state = conn.execute(
                        'SELECT name FROM beach_reservation_states WHERE id = ?',
                        (state_id,)
                    ).fetchone()
                    if state:
                        # Remove current states and add new one
                        # Validation is bypassed by default - users can pick any state
                        current_states = reservation.get('current_states', '')
                        current_state_list = [s.strip() for s in current_states.split(',') if s.strip()]
                        for existing_state in current_state_list:
                            remove_reservation_state(
                                reservation_id, existing_state,
                                changed_by=current_user.username if current_user else 'system'
                            )
                        add_reservation_state(
                            reservation_id, state['name'],
                            changed_by=current_user.username if current_user else 'system'
                        )

            # Handle preferences/characteristics
            if 'preferences' in data:
                pref_value = data['preferences']
                pref_codes = [c.strip() for c in pref_value.split(',') if c.strip()] if pref_value else []
                set_reservation_characteristics_by_codes(reservation_id, pref_codes)

            # Handle tags
            if 'tag_ids' in data:
                from models.tag import set_reservation_tags
                tag_ids = data['tag_ids']
                if isinstance(tag_ids, list):
                    set_reservation_tags(reservation_id, tag_ids)

            # Update other fields
            if updates:
                update_beach_reservation(reservation_id, **updates)

            # Log audit entry for the update
            updated_reservation = get_reservation_with_details(reservation_id)
            after_state = {
                'id': updated_reservation['id'],
                'customer_id': updated_reservation.get('customer_id'),
                'num_people': updated_reservation.get('num_people'),
                'current_states': updated_reservation.get('current_states'),
                'notes': updated_reservation.get('notes'),
                'paid': updated_reservation.get('paid'),
                'final_price': updated_reservation.get('final_price'),
                'payment_method': updated_reservation.get('payment_method'),
                'payment_ticket_number': updated_reservation.get('payment_ticket_number')
            }
            log_update('reservation', reservation_id, before=before_state, after=after_state)

            return jsonify({'success': True})

        except InvalidStateTransitionError as e:
            current_app.logger.warning(f'Invalid state transition: {e}')
            return api_error('Transición de estado no permitida', 400)
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/reservations/<int:reservation_id>/toggle-state', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.change_state')
    def toggle_state(reservation_id):
        """Toggle a state on/off for a reservation."""
        data = request.get_json()
        state_name = data.get('state')
        action = data.get('action', 'toggle')

        if not state_name:
            return api_error('Estado requerido', 400)

        reservation = get_reservation_with_details(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # Capture before state for audit logging
        before_state = {
            'id': reservation['id'],
            'current_states': reservation.get('current_states')
        }

        try:
            current_states = reservation.get('current_states', '')
            current_state_list = [s.strip() for s in current_states.split(',') if s.strip()]
            has_state = state_name in current_state_list
            result_action = None

            # Set action: remove all existing states and set the new one
            # Validation is bypassed by default - users can pick any state
            if action == 'set':
                # Remove all existing states first
                for existing_state in current_state_list:
                    if existing_state != state_name:
                        remove_reservation_state(
                            reservation_id, existing_state,
                            changed_by=current_user.username if current_user else 'system'
                        )
                # Add the new state if not already present
                if not has_state:
                    add_reservation_state(
                        reservation_id, state_name,
                        changed_by=current_user.username if current_user else 'system'
                    )
                result_action = 'set'

            elif action == 'add' or (action == 'toggle' and not has_state):
                add_reservation_state(
                    reservation_id, state_name,
                    changed_by=current_user.username if current_user else 'system'
                )
                result_action = 'added'

            elif action == 'remove' or (action == 'toggle' and has_state):
                remove_reservation_state(
                    reservation_id, state_name,
                    changed_by=current_user.username if current_user else 'system'
                )
                result_action = 'removed'

            # Log audit entry for state change
            if result_action:
                updated_reservation = get_reservation_with_details(reservation_id)
                after_state = {
                    'id': updated_reservation['id'],
                    'current_states': updated_reservation.get('current_states')
                }
                log_update('reservation', reservation_id, before=before_state, after=after_state)

            return jsonify({'success': True, 'action': result_action, 'state': state_name})

        except InvalidStateTransitionError as e:
            current_app.logger.warning(f'Invalid state transition: {e}')
            current_state = reservation.get('current_state', '')
            allowed = get_allowed_transitions(current_state)
            return api_error(
                'Transición de estado no permitida', 400,
                current_state=current_state,
                allowed_transitions=sorted(allowed)
            )
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/reservations/<int:reservation_id>/history')
    @login_required
    @permission_required('beach.reservations.view')
    def reservation_history(reservation_id):
        """Get reservation state change history."""
        history = get_status_history(reservation_id)

        return api_success(data={
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

        return api_success(data={
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
            return api_error('furniture_ids requeridos', 400)
        if not dates:
            return api_error('dates requeridos', 400)

        result = check_furniture_availability_bulk(
            furniture_ids=furniture_ids,
            dates=dates,
            exclude_reservation_id=exclude_reservation_id
        )

        return jsonify({'success': True, **result})

    @bp.route('/reservations/check-duplicate', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def check_duplicate():
        """Check for duplicate reservation (same customer + dates).

        Supports both GET (query params) and POST (JSON body).
        GET: ?customer_id=123&date=2024-12-24 or ?hotel_guest_id=456&date=...
        POST: { customer_id: 123, dates: [...] }

        For hotel guests, checks by room number to find any customer
        with the same room who already has a reservation.
        """
        if request.method == 'GET':
            customer_id = request.args.get('customer_id', type=int)
            hotel_guest_id = request.args.get('hotel_guest_id', type=int)
            date = request.args.get('date')
            exclude_reservation_id = request.args.get('exclude_reservation_id', type=int)

            # If hotel_guest_id provided, look up by room number
            if hotel_guest_id and not customer_id:
                from models.hotel_guest import get_hotel_guest_by_id
                hotel_guest = get_hotel_guest_by_id(hotel_guest_id)
                if hotel_guest and hotel_guest.get('room_number'):
                    # Check for any reservation with a customer from this room
                    room_number = hotel_guest['room_number']
                    is_duplicate, existing = check_duplicate_by_room(
                        room_number=room_number,
                        dates=[date] if date else [],
                        exclude_reservation_id=exclude_reservation_id
                    )
                    return jsonify({
                        'success': True,
                        'has_duplicate': is_duplicate,
                        'is_duplicate': is_duplicate,
                        'existing_reservation': existing
                    })

            if not customer_id:
                return jsonify({'success': True, 'has_duplicate': False, 'existing_reservation': None})
            if not date:
                return api_error('date requerido', 400)

            dates = [date]
        else:
            data = request.get_json()
            customer_id = data.get('customer_id')
            dates = data.get('dates', [])
            exclude_reservation_id = data.get('exclude_reservation_id')

            if not customer_id:
                return api_error('customer_id requerido', 400)
            if not dates:
                return api_error('dates requeridos', 400)

        is_duplicate, existing = check_duplicate_reservation(
            customer_id=customer_id,
            dates=dates,
            exclude_reservation_id=exclude_reservation_id
        )

        return jsonify({
            'success': True,
            'has_duplicate': is_duplicate,
            'is_duplicate': is_duplicate,  # backward compat
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
            return api_error('date_from y date_to requeridos', 400)

        result = get_furniture_availability_map(
            date_from=date_from,
            date_to=date_to,
            zone_id=zone_id,
            furniture_type=furniture_type
        )

        return jsonify({'success': True, **result})

    @bp.route('/reservations/conflicts')
    @login_required
    @permission_required('beach.reservations.view')
    def get_conflicts():
        """Get conflicting reservations for furniture on a date."""
        furniture_ids_str = request.args.get('furniture_ids', '')
        date_str = request.args.get('date')
        exclude_reservation_id = request.args.get('exclude_reservation_id', type=int)

        if not furniture_ids_str or not date_str:
            return api_error('furniture_ids y date requeridos', 400)

        try:
            furniture_ids = [int(x) for x in furniture_ids_str.split(',')]
        except ValueError:
            return api_error('furniture_ids debe ser lista de enteros', 400)

        conflicts = get_conflicting_reservations(
            furniture_ids=furniture_ids,
            date=date_str,
            exclude_reservation_id=exclude_reservation_id
        )

        return api_success(data={'conflicts': conflicts})

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

            # Log audit entry for each created reservation
            if result.get('success') and result.get('reservation_ids'):
                for res_id in result['reservation_ids']:
                    reservation_data = {
                        'customer_id': customer_id,
                        'dates': dates,
                        'num_people': num_people,
                        'furniture_ids': furniture_ids or furniture_by_date
                    }
                    log_create('reservation', res_id, data=reservation_data)

            return jsonify(result)

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

    @bp.route('/reservations/<int:reservation_id>/multiday-summary')
    @login_required
    @permission_required('beach.reservations.view')
    def multiday_summary(reservation_id):
        """Get summary of multi-day reservation group."""
        summary = get_multiday_summary(reservation_id)

        if not summary:
            return api_error('Reserva no encontrada', 404)

        return jsonify({'success': True, **summary})

    @bp.route('/reservations/<int:reservation_id>/cancel-multiday', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.change_state')
    def cancel_multiday(reservation_id):
        """Cancel all reservations in a multi-day group."""
        data = request.get_json() or {}

        # Capture before state for audit logging
        before_summary = get_multiday_summary(reservation_id)
        before_state = None
        if before_summary:
            before_state = {
                'reservation_ids': before_summary.get('reservation_ids', []),
                'total_reservations': before_summary.get('total_reservations'),
                'customer_name': before_summary.get('customer_name')
            }

        try:
            result = cancel_multiday_reservations(
                parent_id=reservation_id,
                cancelled_by=current_user.username if current_user else 'system',
                notes=data.get('notes', ''),
                cancel_children=data.get('cancel_children', True)
            )

            # Log audit entry for cancellation (DELETE action)
            if result.get('success'):
                log_delete('reservation', reservation_id, data=before_state)

            return jsonify(result)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

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
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

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
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

    @bp.route('/reservations/validate-contiguity', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.view')
    def validate_contiguity():
        """Validate if selected furniture forms a contiguous cluster."""
        data = request.get_json()

        furniture_ids = data.get('furniture_ids', [])
        date_str = data.get('date')

        if not furniture_ids:
            return api_error('furniture_ids requerido', 400)
        if not date_str:
            return api_error('date requerido', 400)

        try:
            occupancy_map = build_furniture_occupancy_map(date_str)
            result = validate_cluster_contiguity(furniture_ids, occupancy_map)
            return jsonify({'success': True, **result})
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    # ============================================================================
    # RESERVATIONS LIST API (for auto-filtering)
    # ============================================================================

    @bp.route('/reservations/list')
    @login_required
    @permission_required('beach.reservations.view')
    def reservations_list():
        """Get filtered reservations list as JSON (for auto-filtering)."""
        from models.reservation import get_reservations_filtered, get_reservation_stats

        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        customer_type = request.args.get('type', '')
        state = request.args.get('state', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)

        # Default to today if no date_from provided
        if not date_from:
            date_from = date.today().strftime('%Y-%m-%d')

        result = get_reservations_filtered(
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            customer_type=customer_type if customer_type else None,
            state=state if state else None,
            search=search if search else None,
            page=page
        )

        stats = get_reservation_stats(date_from, date_to if date_to else date_from)

        return jsonify({
            'success': True,
            'reservations': result['items'],
            'total': result['total'],
            'page': result['page'],
            'pages': result['pages'],
            'stats': stats
        })
