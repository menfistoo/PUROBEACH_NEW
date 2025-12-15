"""
Beach blueprint initialization.
Registers all beach-related routes (map, customers, reservations, config).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture
from models.furniture_type import get_all_furniture_types
from models.customer import (
    get_customers_filtered, get_customer_with_details, get_customer_by_id,
    create_customer, update_customer, delete_customer, get_customer_stats,
    set_customer_preferences, set_customer_tags, find_duplicates,
    merge_customers, find_potential_duplicates_for_customer, search_customers,
    search_customers_unified, create_customer_from_hotel_guest
)
from models.reservation import (
    get_reservations_filtered, get_reservation_with_details, get_reservation_by_id,
    get_reservation_stats, get_reservation_states, get_available_furniture,
    create_reservation_with_furniture, update_reservation_with_furniture,
    change_reservation_state, delete_reservation, sync_preferences_to_customer,
    get_customer_preference_codes
)
from models.preference import get_all_preferences
from models.tag import get_all_tags
from models.hotel_guest import get_guests_by_room, search_guests
from datetime import date, datetime

# Create main beach blueprint
beach_bp = Blueprint('beach', __name__, template_folder='../../templates/beach')

# Register config sub-blueprint
from blueprints.beach.routes.config import config_bp
beach_bp.register_blueprint(config_bp)


@beach_bp.route('/map')
@login_required
@permission_required('beach.map.view')
def map():
    """Display beach map."""
    zones = get_all_zones()
    furniture = get_all_furniture()
    return render_template('beach/map.html', zones=zones, furniture=furniture)


# ============================================================================
# CUSTOMER ROUTES
# ============================================================================

@beach_bp.route('/customers')
@login_required
@permission_required('beach.customers.view')
def customers():
    """Display customer list with filters."""
    search = request.args.get('search', '')
    customer_type = request.args.get('type', '')
    vip_only = request.args.get('vip', '') == '1'

    result = get_customers_filtered(
        search=search if search else None,
        customer_type=customer_type if customer_type else None,
        vip_only=vip_only
    )

    stats = get_customer_stats()

    return render_template(
        'beach/customers.html',
        customers=result['customers'],
        total=result['total'],
        stats=stats,
        search=search,
        type_filter=customer_type,
        vip_filter='1' if vip_only else ''
    )


@beach_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.create')
def customers_create():
    """Create new customer."""
    preferences = get_all_preferences()
    tags = get_all_tags()

    if request.method == 'POST':
        customer_type = request.form.get('customer_type')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        room_number = request.form.get('room_number', '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        vip_status = 1 if request.form.get('vip_status') else 0

        # Validation
        if not first_name:
            flash('El nombre es requerido', 'error')
            return render_template('beach/customer_form.html',
                                   mode='create', preferences=preferences, tags=tags)

        if customer_type == 'interno' and not room_number:
            flash('El número de habitación es requerido para clientes internos', 'error')
            return render_template('beach/customer_form.html',
                                   mode='create', preferences=preferences, tags=tags)

        if customer_type == 'externo' and not (email or phone):
            flash('Se requiere email o teléfono para clientes externos', 'error')
            return render_template('beach/customer_form.html',
                                   mode='create', preferences=preferences, tags=tags)

        # Check for duplicates
        if phone or (customer_type == 'interno' and room_number):
            duplicates = find_duplicates(phone or '', customer_type, room_number)
            if duplicates:
                flash(f'Se encontraron {len(duplicates)} posibles duplicados. '
                      'Por favor revise antes de crear.', 'warning')
                return render_template('beach/customer_form.html',
                                       mode='create', preferences=preferences, tags=tags,
                                       duplicates=duplicates,
                                       form_data=request.form)

        try:
            customer_id = create_customer(
                customer_type=customer_type,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                room_number=room_number,
                notes=notes,
                vip_status=vip_status
            )

            # Set preferences
            pref_ids = request.form.getlist('preferences')
            if pref_ids:
                set_customer_preferences(customer_id, [int(p) for p in pref_ids])

            # Set tags
            tag_ids = request.form.getlist('tags')
            if tag_ids:
                set_customer_tags(customer_id, [int(t) for t in tag_ids])

            flash('Cliente creado exitosamente', 'success')
            return redirect(url_for('beach.customers_detail', customer_id=customer_id))

        except ValueError as e:
            flash(str(e), 'error')

    return render_template('beach/customer_form.html',
                           mode='create', preferences=preferences, tags=tags)


@beach_bp.route('/customers/<int:customer_id>')
@login_required
@permission_required('beach.customers.view')
def customers_detail(customer_id):
    """Display customer detail view."""
    customer = get_customer_with_details(customer_id)
    if not customer:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('beach.customers'))

    # Find potential duplicates
    duplicates = find_potential_duplicates_for_customer(customer_id)

    return render_template('beach/customer_detail.html',
                           customer=customer, duplicates=duplicates)


@beach_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.edit')
def customers_edit(customer_id):
    """Edit existing customer."""
    customer = get_customer_with_details(customer_id)
    if not customer:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('beach.customers'))

    preferences = get_all_preferences()
    tags = get_all_tags()

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        room_number = request.form.get('room_number', '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        vip_status = 1 if request.form.get('vip_status') else 0

        # Validation
        if not first_name:
            flash('El nombre es requerido', 'error')
            return render_template('beach/customer_form.html',
                                   mode='edit', customer=customer,
                                   preferences=preferences, tags=tags)

        if customer['customer_type'] == 'interno' and not room_number:
            flash('El número de habitación es requerido para clientes internos', 'error')
            return render_template('beach/customer_form.html',
                                   mode='edit', customer=customer,
                                   preferences=preferences, tags=tags)

        try:
            update_customer(
                customer_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                room_number=room_number,
                notes=notes,
                vip_status=vip_status
            )

            # Update preferences
            pref_ids = request.form.getlist('preferences')
            set_customer_preferences(customer_id, [int(p) for p in pref_ids] if pref_ids else [])

            # Update tags
            tag_ids = request.form.getlist('tags')
            set_customer_tags(customer_id, [int(t) for t in tag_ids] if tag_ids else [])

            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('beach.customers_detail', customer_id=customer_id))

        except ValueError as e:
            flash(str(e), 'error')

    return render_template('beach/customer_form.html',
                           mode='edit', customer=customer,
                           preferences=preferences, tags=tags)


@beach_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.customers.edit')
def customers_delete(customer_id):
    """Delete customer."""
    try:
        delete_customer(customer_id)
        flash('Cliente eliminado exitosamente', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('beach.customers'))


@beach_bp.route('/customers/<int:customer_id>/merge', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.merge')
def customers_merge(customer_id):
    """Merge customer into another."""
    customer = get_customer_with_details(customer_id)
    if not customer:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('beach.customers'))

    # Find potential duplicates to merge with
    duplicates = find_potential_duplicates_for_customer(customer_id)

    if request.method == 'POST':
        target_id = request.form.get('target_id', type=int)
        if not target_id:
            flash('Debe seleccionar un cliente destino', 'error')
            return render_template('beach/customer_merge.html',
                                   customer=customer, duplicates=duplicates)

        try:
            merge_customers(customer_id, target_id)
            flash('Clientes fusionados exitosamente', 'success')
            return redirect(url_for('beach.customers_detail', customer_id=target_id))

        except ValueError as e:
            flash(str(e), 'error')

    return render_template('beach/customer_merge.html',
                           customer=customer, duplicates=duplicates)


# ============================================================================
# CUSTOMER API ROUTES
# ============================================================================

@beach_bp.route('/api/customers/search')
@login_required
@permission_required('beach.customers.view')
def api_customers_search():
    """Search customers and hotel guests for autocomplete (unified search)."""
    query = request.args.get('q', '')
    customer_type = request.args.get('type', None)

    if len(query) < 2:
        return jsonify({'customers': []})

    # Use unified search that includes both beach_customers and hotel_guests
    results = search_customers_unified(query, customer_type)

    formatted_results = []
    for c in results:
        if c.get('source') == 'hotel_guest':
            # Hotel guest result
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
                'departure_date': c.get('departure_date')
            })
        else:
            # Beach customer result
            formatted_results.append({
                'id': c['id'],
                'source': 'customer',
                'first_name': c['first_name'],
                'last_name': c.get('last_name', ''),
                'display_name': f"{c['first_name']} {c.get('last_name', '')}".strip() +
                               (f" (Hab. {c['room_number']})" if c.get('room_number') else ''),
                'customer_type': c['customer_type'],
                'room_number': c.get('room_number'),
                'phone': c.get('phone'),
                'email': c.get('email'),
                'vip_status': c.get('vip_status', 0)
            })

    return jsonify({'customers': formatted_results})


@beach_bp.route('/api/customers/check-duplicates')
@login_required
@permission_required('beach.customers.view')
def api_customers_check_duplicates():
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


@beach_bp.route('/api/customers/from-hotel-guest', methods=['POST'])
@login_required
@permission_required('beach.customers.create')
def api_customers_from_hotel_guest():
    """Convert a hotel guest to a beach customer."""
    data = request.get_json()
    hotel_guest_id = data.get('hotel_guest_id')

    if not hotel_guest_id:
        return jsonify({'success': False, 'error': 'ID de huésped requerido'}), 400

    try:
        result = create_customer_from_hotel_guest(hotel_guest_id)
        customer = result['customer']

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
                'vip_status': customer.get('vip_status', 0)
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Error al crear cliente'}), 500


@beach_bp.route('/api/customers/create', methods=['POST'])
@login_required
@permission_required('beach.customers.create')
def api_customers_create():
    """Create a new customer via API (for modal form)."""
    data = request.get_json()

    # Validate required fields
    customer_type = data.get('customer_type')
    first_name = data.get('first_name', '').strip()

    if not customer_type or customer_type not in ['interno', 'externo']:
        return jsonify({'success': False, 'error': 'Tipo de cliente inválido'}), 400

    if not first_name:
        return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400

    room_number = data.get('room_number', '').strip() or None
    if customer_type == 'interno' and not room_number:
        return jsonify({'success': False, 'error': 'El número de habitación es requerido para clientes internos'}), 400

    try:
        customer_id = create_customer(
            customer_type=customer_type,
            first_name=first_name,
            last_name=data.get('last_name', '').strip() or None,
            email=data.get('email', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            room_number=room_number,
            notes=data.get('notes', '').strip() or None
        )

        customer = get_customer_by_id(customer_id)

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
                'vip_status': customer.get('vip_status', 0)
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Error al crear cliente'}), 500


@beach_bp.route('/api/hotel-guests/lookup')
@login_required
@permission_required('beach.customers.view')
def api_hotel_guest_lookup():
    """Lookup hotel guest by room number for auto-fill."""
    room_number = request.args.get('room', '')
    if not room_number:
        return jsonify({'guests': []})

    guests = get_guests_by_room(room_number, date.today())

    return jsonify({
        'guests': [{
            'id': g['id'],
            'guest_name': g['guest_name'],
            'room_number': g['room_number'],
            'arrival_date': g['arrival_date'],
            'departure_date': g['departure_date'],
            'vip_code': g['vip_code'],
            'nationality': g['nationality'],
            'email': g['email'],
            'phone': g['phone']
        } for g in guests]
    })


@beach_bp.route('/api/hotel-guests/search')
@login_required
@permission_required('beach.customers.view')
def api_hotel_guest_search():
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
# RESERVATIONS ROUTES (Phase 6A)
# ============================================================================

@beach_bp.route('/reservations')
@login_required
@permission_required('beach.reservations.view')
def reservations():
    """Display reservation list with filters."""
    # Get filters
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    customer_type = request.args.get('type', '')
    state = request.args.get('state', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    # Default to today if no date specified
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
    states = get_reservation_states()

    return render_template(
        'beach/reservations.html',
        reservations=result['items'],
        total=result['total'],
        page=result['page'],
        pages=result['pages'],
        stats=stats,
        states=states,
        date_from=date_from,
        date_to=date_to,
        type_filter=customer_type,
        state_filter=state,
        search=search
    )


@beach_bp.route('/reservations/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.create')
def reservations_create():
    """Create new reservation."""
    from models.reservation import (
        create_beach_reservation, get_available_furniture, check_furniture_availability
    )

    zones = get_all_zones()
    furniture_types = get_all_furniture_types()
    preferences = get_all_preferences()
    tags = get_all_tags()
    states = get_reservation_states()

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        reservation_date = request.form.get('reservation_date')
        num_people = request.form.get('num_people', 1, type=int)
        time_slot = request.form.get('time_slot', 'all_day')
        furniture_ids = request.form.getlist('furniture_ids', type=int)
        selected_prefs = request.form.getlist('preferences')
        notes = request.form.get('notes', '').strip()
        payment_status = request.form.get('payment_status', 'NO')
        charge_to_room = 1 if request.form.get('charge_to_room') else 0
        charge_reference = request.form.get('charge_reference', '').strip()

        # Validation
        if not customer_id:
            flash('Debe seleccionar un cliente', 'error')
            return render_template('beach/reservation_form.html',
                                   mode='create', zones=zones, furniture_types=furniture_types,
                                   preferences=preferences, tags=tags, states=states)

        if not reservation_date:
            flash('La fecha es requerida', 'error')
            return render_template('beach/reservation_form.html',
                                   mode='create', zones=zones, furniture_types=furniture_types,
                                   preferences=preferences, tags=tags, states=states)

        if not furniture_ids:
            flash('Debe seleccionar al menos un mobiliario', 'error')
            return render_template('beach/reservation_form.html',
                                   mode='create', zones=zones, furniture_types=furniture_types,
                                   preferences=preferences, tags=tags, states=states)

        # Check availability for each furniture
        for furn_id in furniture_ids:
            if not check_furniture_availability(furn_id, reservation_date, reservation_date):
                flash(f'El mobiliario {furn_id} no está disponible para esta fecha', 'error')
                return render_template('beach/reservation_form.html',
                                       mode='create', zones=zones, furniture_types=furniture_types,
                                       preferences=preferences, tags=tags, states=states,
                                       form_data=request.form)

        try:
            preferences_csv = ','.join(selected_prefs) if selected_prefs else ''

            reservation_id, ticket_number = create_beach_reservation(
                customer_id=customer_id,
                reservation_date=reservation_date,
                num_people=num_people,
                furniture_ids=furniture_ids,
                time_slot=time_slot,
                payment_status=payment_status,
                charge_to_room=charge_to_room,
                charge_reference=charge_reference,
                preferences=preferences_csv,
                observations=notes,
                created_by=current_user.username if current_user else None
            )

            flash(f'Reserva {ticket_number} creada exitosamente', 'success')
            return redirect(url_for('beach.reservations_detail', reservation_id=reservation_id))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al crear reserva: {str(e)}', 'error')

    # For GET request, pre-select date if provided
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))

    return render_template('beach/reservation_form.html',
                           mode='create', zones=zones, furniture_types=furniture_types,
                           preferences=preferences, tags=tags, states=states,
                           selected_date=selected_date)


@beach_bp.route('/reservations/<int:reservation_id>')
@login_required
@permission_required('beach.reservations.view')
def reservations_detail(reservation_id):
    """Display reservation detail view."""
    from models.reservation import get_status_history

    reservation = get_reservation_with_details(reservation_id)
    if not reservation:
        flash('Reserva no encontrada', 'error')
        return redirect(url_for('beach.reservations'))

    history = get_status_history(reservation_id)
    states = get_reservation_states()

    return render_template('beach/reservation_detail.html',
                           reservation=reservation, history=history, states=states)


@beach_bp.route('/reservations/<int:reservation_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.edit')
def reservations_edit(reservation_id):
    """Edit existing reservation."""
    from models.reservation import (
        update_beach_reservation, update_reservation_with_furniture,
        get_available_furniture, check_furniture_availability
    )

    reservation = get_reservation_with_details(reservation_id)
    if not reservation:
        flash('Reserva no encontrada', 'error')
        return redirect(url_for('beach.reservations'))

    zones = get_all_zones()
    furniture_types = get_all_furniture_types()
    preferences = get_all_preferences()
    tags = get_all_tags()
    states = get_reservation_states()

    if request.method == 'POST':
        num_people = request.form.get('num_people', 1, type=int)
        time_slot = request.form.get('time_slot', 'all_day')
        furniture_ids = request.form.getlist('furniture_ids', type=int)
        selected_prefs = request.form.getlist('preferences')
        notes = request.form.get('notes', '').strip()
        payment_status = request.form.get('payment_status', 'NO')
        charge_to_room = 1 if request.form.get('charge_to_room') else 0
        charge_reference = request.form.get('charge_reference', '').strip()

        if not furniture_ids:
            flash('Debe seleccionar al menos un mobiliario', 'error')
            return render_template('beach/reservation_form.html',
                                   mode='edit', reservation=reservation,
                                   zones=zones, furniture_types=furniture_types,
                                   preferences=preferences, tags=tags, states=states)

        # Check availability (excluding current reservation)
        for furn_id in furniture_ids:
            if not check_furniture_availability(furn_id, reservation['reservation_date'],
                                                 reservation['reservation_date'],
                                                 exclude_reservation_id=reservation_id):
                flash(f'El mobiliario {furn_id} no está disponible para esta fecha', 'error')
                return render_template('beach/reservation_form.html',
                                       mode='edit', reservation=reservation,
                                       zones=zones, furniture_types=furniture_types,
                                       preferences=preferences, tags=tags, states=states)

        try:
            preferences_csv = ','.join(selected_prefs) if selected_prefs else ''

            update_reservation_with_furniture(
                reservation_id,
                furniture_ids=furniture_ids,
                num_people=num_people,
                time_slot=time_slot,
                payment_status=payment_status,
                charge_to_room=charge_to_room,
                charge_reference=charge_reference,
                preferences=preferences_csv,
                notes=notes
            )

            flash('Reserva actualizada exitosamente', 'success')
            return redirect(url_for('beach.reservations_detail', reservation_id=reservation_id))

        except ValueError as e:
            flash(str(e), 'error')

    return render_template('beach/reservation_form.html',
                           mode='edit', reservation=reservation,
                           zones=zones, furniture_types=furniture_types,
                           preferences=preferences, tags=tags, states=states)


@beach_bp.route('/reservations/<int:reservation_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.reservations.delete')
def reservations_delete(reservation_id):
    """Delete reservation."""
    try:
        delete_reservation(reservation_id)
        flash('Reserva eliminada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.reservations'))


@beach_bp.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
@permission_required('beach.reservations.change_state')
def reservations_cancel(reservation_id):
    """Cancel reservation."""
    from models.reservation import cancel_beach_reservation

    reason = request.form.get('reason', '')

    try:
        cancel_beach_reservation(
            reservation_id,
            cancelled_by=current_user.username if current_user else 'system',
            notes=reason
        )
        flash('Reserva cancelada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cancelar: {str(e)}', 'error')

    return redirect(url_for('beach.reservations_detail', reservation_id=reservation_id))


# ============================================================================
# RESERVATION API ROUTES
# ============================================================================

@beach_bp.route('/api/reservations/<int:reservation_id>')
@login_required
@permission_required('beach.reservations.view')
def api_reservation_detail(reservation_id):
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


@beach_bp.route('/api/reservations/<int:reservation_id>/toggle-state', methods=['POST'])
@login_required
@permission_required('beach.reservations.change_state')
def api_toggle_state(reservation_id):
    """Toggle a state on/off for a reservation."""
    from models.reservation import add_reservation_state, remove_reservation_state

    data = request.get_json()
    state_name = data.get('state')
    action = data.get('action', 'toggle')  # 'add', 'remove', or 'toggle'

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


@beach_bp.route('/api/reservations/<int:reservation_id>/history')
@login_required
@permission_required('beach.reservations.view')
def api_reservation_history(reservation_id):
    """Get reservation state change history."""
    from models.reservation import get_status_history

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


@beach_bp.route('/api/furniture/available')
@login_required
@permission_required('beach.reservations.view')
def api_available_furniture():
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
