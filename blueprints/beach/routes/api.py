"""
Beach API routes.
All REST API endpoints for customers, reservations, and Phase 6B features.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.customer import (
    find_duplicates, get_customer_by_id, get_customer_preferences,
    create_customer, set_customer_preferences, search_customers_unified,
    create_customer_from_hotel_guest
)
from models.reservation import (
    get_reservation_with_details, get_available_furniture,
    get_customer_reservation_history, get_status_history,
    add_reservation_state, remove_reservation_state,
    check_furniture_availability_bulk, check_duplicate_reservation,
    get_furniture_availability_map, get_conflicting_reservations,
    create_linked_multiday_reservations, get_multiday_summary,
    cancel_multiday_reservations, update_multiday_reservations,
    suggest_furniture_for_reservation, build_furniture_occupancy_map,
    validate_cluster_contiguity, get_customer_preferred_furniture
)
from models.hotel_guest import get_guests_by_room, search_guests
from datetime import date

api_bp = Blueprint('api', __name__)


# ============================================================================
# CUSTOMER API ROUTES
# ============================================================================

@api_bp.route('/customers/search')
@login_required
@permission_required('beach.customers.view')
def customers_search():
    """Search customers and hotel guests for autocomplete (unified search)."""
    query = request.args.get('q', '')
    customer_type = request.args.get('type', None)

    if len(query) < 2:
        return jsonify({'customers': []})

    results = search_customers_unified(query, customer_type)

    formatted_results = []
    for c in results:
        if c.get('source') == 'hotel_guest':
            formatted_results.append({
                'id': c['id'],
                'source': 'hotel_guest',
                'guest_name': c.get('guest_name', ''),
                'display_name': f"{c.get('guest_name', '')} (Hab. {c['room_number']})",
                'customer_type': 'interno',
                'room_number': c['room_number'],
                'phone': c.get('phone'),
                'email': c.get('email'),
                'vip_code': c.get('vip_code'),
                'departure_date': c.get('departure_date'),
                'arrival_date': c.get('arrival_date'),
                'nationality': c.get('nationality'),
                'num_adults': c.get('num_adults', 1),
                'num_children': c.get('num_children', 0),
                'notes': c.get('notes'),
                'is_main_guest': c.get('is_main_guest', 0),
                'room_guest_count': c.get('room_guest_count', 1),
                'booking_reference': c.get('booking_reference'),
                'is_checkin_today': c.get('is_checkin_today', False),
                'is_checkout_today': c.get('is_checkout_today', False)
            })
        else:
            preferences = get_customer_preferences(c['id'])
            pref_codes = [p['code'] for p in preferences]

            customer_data = {
                'id': c['id'],
                'source': 'customer',
                'first_name': c['first_name'],
                'last_name': c.get('last_name', ''),
                'display_name': f"{c['first_name']} {c.get('last_name', '')}".strip() +
                               (f" (Hab. {c['room_number']})" if c.get('room_number') and c['room_number'] != 'None' else ''),
                'customer_type': c['customer_type'],
                'room_number': c.get('room_number') if c.get('room_number') != 'None' else None,
                'phone': c.get('phone'),
                'email': c.get('email'),
                'vip_status': c.get('vip_status', 0),
                'notes': c.get('notes'),
                'total_visits': c.get('total_visits', 0),
                'total_spent': c.get('total_spent', 0),
                'last_visit': c.get('last_visit'),
                'preferences': pref_codes,
                'is_checkin_today': c.get('is_checkin_today', False),
                'is_checkout_today': c.get('is_checkout_today', False)
            }

            if c['customer_type'] == 'interno' and c.get('room_number'):
                hotel_guests = get_guests_by_room(c['room_number'], date.today())
                if hotel_guests:
                    full_name = f"{c['first_name']} {c.get('last_name', '')}".strip().upper()
                    matching_guest = None
                    for hg in hotel_guests:
                        if hg['guest_name'].upper() == full_name:
                            matching_guest = hg
                            break
                    if not matching_guest:
                        matching_guest = next((hg for hg in hotel_guests if hg.get('is_main_guest')), hotel_guests[0])

                    customer_data['arrival_date'] = matching_guest.get('arrival_date')
                    customer_data['departure_date'] = matching_guest.get('departure_date')
                    customer_data['nationality'] = matching_guest.get('nationality')
                    customer_data['booking_reference'] = matching_guest.get('booking_reference')
                    customer_data['room_guest_count'] = len(hotel_guests)
                    customer_data['vip_code'] = matching_guest.get('vip_code')

            formatted_results.append(customer_data)

    return jsonify({'customers': formatted_results})


@api_bp.route('/customers/check-duplicates')
@login_required
@permission_required('beach.customers.view')
def customers_check_duplicates():
    """Check for duplicate customers."""
    phone = request.args.get('phone', '')
    customer_type = request.args.get('type', 'externo')
    room_number = request.args.get('room', '')

    duplicates = find_duplicates(phone, customer_type, room_number)

    return jsonify({
        'duplicates': [{
            'id': d['id'],
            'first_name': d['first_name'],
            'last_name': d['last_name'],
            'customer_type': d['customer_type'],
            'room_number': d['room_number'],
            'phone': d['phone'],
            'email': d['email']
        } for d in duplicates]
    })


@api_bp.route('/customers/from-hotel-guest', methods=['POST'])
@login_required
@permission_required('beach.customers.create')
def customers_from_hotel_guest():
    """Convert a hotel guest to a beach customer with optional additional data."""
    data = request.get_json()
    hotel_guest_id = data.get('hotel_guest_id')

    if not hotel_guest_id:
        return jsonify({'success': False, 'error': 'ID de huésped requerido'}), 400

    additional_data = {}
    if data.get('phone'):
        additional_data['phone'] = data['phone'].strip()
    if data.get('email'):
        additional_data['email'] = data['email'].strip()
    if data.get('language'):
        additional_data['language'] = data['language'].strip()
    if data.get('country_code'):
        additional_data['country_code'] = data['country_code'].strip()
    if data.get('notes'):
        additional_data['notes'] = data['notes'].strip()
    if data.get('preferences'):
        additional_data['preferences'] = [int(p) for p in data['preferences'] if p]

    try:
        result = create_customer_from_hotel_guest(hotel_guest_id, additional_data)
        customer = result['customer']

        preferences = get_customer_preferences(customer['id'])
        pref_codes = [p['code'] for p in preferences]

        return jsonify({
            'success': True,
            'action': result['action'],
            'customer': {
                'id': customer['id'],
                'source': 'customer',
                'first_name': customer['first_name'],
                'last_name': customer.get('last_name', ''),
                'display_name': f"{customer['first_name']} {customer.get('last_name', '')}".strip(),
                'customer_type': customer['customer_type'],
                'room_number': customer.get('room_number'),
                'phone': customer.get('phone'),
                'email': customer.get('email'),
                'vip_status': customer.get('vip_status', 0),
                'language': customer.get('language'),
                'country_code': customer.get('country_code'),
                'notes': customer.get('notes'),
                'preferences': pref_codes
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Error al crear cliente'}), 500


@api_bp.route('/customers/create', methods=['POST'])
@login_required
@permission_required('beach.customers.create')
def customers_create():
    """Create a new customer via API (for inline form)."""
    data = request.get_json()

    customer_type = data.get('customer_type')
    first_name = data.get('first_name', '').strip()

    if not customer_type or customer_type not in ['interno', 'externo']:
        return jsonify({'success': False, 'error': 'Tipo de cliente inválido'}), 400

    if not first_name:
        return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400

    room_number = data.get('room_number', '').strip() or None
    if customer_type == 'interno' and not room_number:
        return jsonify({'success': False, 'error': 'El número de habitación es requerido para clientes internos'}), 400

    phone = data.get('phone', '').strip() or None
    email = data.get('email', '').strip() or None
    if customer_type == 'externo' and not (phone or email):
        return jsonify({'success': False, 'error': 'Se requiere teléfono o email para clientes externos'}), 400

    try:
        customer_id = create_customer(
            customer_type=customer_type,
            first_name=first_name,
            last_name=data.get('last_name', '').strip() or None,
            email=email,
            phone=phone,
            room_number=room_number,
            notes=data.get('notes', '').strip() or None,
            language=data.get('language', '').strip() or None,
            country_code=data.get('country_code', '+34').strip()
        )

        preference_ids = data.get('preferences', [])
        if preference_ids:
            set_customer_preferences(customer_id, [int(p) for p in preference_ids if p])

        customer = get_customer_by_id(customer_id)

        preferences = get_customer_preferences(customer_id)
        pref_codes = [p['code'] for p in preferences]

        return jsonify({
            'success': True,
            'customer': {
                'id': customer['id'],
                'source': 'customer',
                'first_name': customer['first_name'],
                'last_name': customer.get('last_name', ''),
                'display_name': f"{customer['first_name']} {customer.get('last_name', '')}".strip(),
                'customer_type': customer['customer_type'],
                'room_number': customer.get('room_number'),
                'phone': customer.get('phone'),
                'email': customer.get('email'),
                'vip_status': customer.get('vip_status', 0),
                'language': customer.get('language'),
                'country_code': customer.get('country_code'),
                'notes': customer.get('notes'),
                'preferences': pref_codes
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Error al crear cliente'}), 500


@api_bp.route('/customers/<int:customer_id>/history')
@login_required
@permission_required('beach.customers.view')
def customer_history(customer_id):
    """Get reservation history for a customer."""
    limit = request.args.get('limit', 5, type=int)
    history = get_customer_reservation_history(customer_id, limit=min(limit, 20))

    return jsonify({
        'customer_id': customer_id,
        'history': history,
        'count': len(history)
    })


@api_bp.route('/customers/<int:customer_id>/preferred-furniture')
@login_required
@permission_required('beach.customers.view')
def customer_preferred_furniture(customer_id):
    """Get customer's preferred furniture based on history."""
    limit = request.args.get('limit', 5, type=int)

    try:
        preferred = get_customer_preferred_furniture(customer_id, limit=limit)
        return jsonify({'preferred_furniture': preferred})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/customers/create-from-guest', methods=['POST'])
@login_required
@permission_required('beach.customers.create')
def create_customer_from_guest():
    """Create a beach customer from a hotel guest."""
    data = request.get_json()
    hotel_guest_id = data.get('hotel_guest_id')

    if not hotel_guest_id:
        return jsonify({'success': False, 'error': 'hotel_guest_id requerido'}), 400

    try:
        result = create_customer_from_hotel_guest(hotel_guest_id)

        if result:
            return jsonify({
                'success': True,
                'customer_id': result['id'],
                'customer': result
            })
        else:
            return jsonify({'success': False, 'error': 'Error al crear cliente'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# HOTEL GUEST API ROUTES
# ============================================================================

@api_bp.route('/hotel-guests/lookup')
@login_required
@permission_required('beach.customers.view')
def hotel_guest_lookup():
    """Lookup hotel guests by room number for auto-fill and guest selection."""
    room_number = request.args.get('room', '')
    if not room_number:
        return jsonify({'guests': [], 'guest_count': 0})

    guests = get_guests_by_room(room_number, date.today())

    return jsonify({
        'guest_count': len(guests),
        'guests': [{
            'id': g['id'],
            'guest_name': g['guest_name'],
            'room_number': g['room_number'],
            'arrival_date': g['arrival_date'],
            'departure_date': g['departure_date'],
            'vip_code': g['vip_code'],
            'nationality': g['nationality'],
            'email': g['email'],
            'phone': g['phone'],
            'notes': g.get('notes'),
            'num_adults': g.get('num_adults', 1),
            'num_children': g.get('num_children', 0),
            'is_main_guest': g.get('is_main_guest', 0),
            'booking_reference': g.get('booking_reference')
        } for g in guests]
    })


@api_bp.route('/hotel-guests/search')
@login_required
@permission_required('beach.customers.view')
def hotel_guest_search():
    """Search hotel guests for autocomplete."""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'guests': []})

    guests = search_guests(query, limit=10)

    return jsonify({
        'guests': [{
            'id': g['id'],
            'guest_name': g['guest_name'],
            'room_number': g['room_number'],
            'arrival_date': g['arrival_date'],
            'departure_date': g['departure_date']
        } for g in guests]
    })


# ============================================================================
# RESERVATION API ROUTES
# ============================================================================

@api_bp.route('/reservations/<int:reservation_id>')
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


@api_bp.route('/reservations/<int:reservation_id>/toggle-state', methods=['POST'])
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


@api_bp.route('/reservations/<int:reservation_id>/history')
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


@api_bp.route('/furniture/available')
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
# PHASE 6B: BULK AVAILABILITY API ENDPOINTS
# ============================================================================

@api_bp.route('/reservations/check-availability', methods=['POST'])
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


@api_bp.route('/reservations/check-duplicate', methods=['POST'])
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


@api_bp.route('/reservations/availability-map')
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


@api_bp.route('/reservations/conflicts')
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
# PHASE 6B: MULTI-DAY RESERVATION API ENDPOINTS
# ============================================================================

@api_bp.route('/reservations/create-multiday', methods=['POST'])
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


@api_bp.route('/reservations/<int:reservation_id>/multiday-summary')
@login_required
@permission_required('beach.reservations.view')
def multiday_summary(reservation_id):
    """Get summary of multi-day reservation group."""
    summary = get_multiday_summary(reservation_id)

    if not summary:
        return jsonify({'error': 'Reserva no encontrada'}), 404

    return jsonify(summary)


@api_bp.route('/reservations/<int:reservation_id>/cancel-multiday', methods=['POST'])
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


@api_bp.route('/reservations/<int:reservation_id>/update-multiday', methods=['POST'])
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
# PHASE 6B: SMART SUGGESTIONS API ENDPOINTS
# ============================================================================

@api_bp.route('/reservations/suggest-furniture', methods=['POST'])
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


@api_bp.route('/reservations/validate-contiguity', methods=['POST'])
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
