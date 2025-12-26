"""
Beach reservation routes.
Handles reservation CRUD operations and views.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture_type import get_all_furniture_types
from models.preference import get_all_preferences
from models.tag import get_all_tags
from models.customer import create_customer_from_hotel_guest
from models.reservation import (
    get_reservations_filtered, get_reservation_with_details,
    get_reservation_stats, get_reservation_states, get_available_furniture,
    create_beach_reservation, check_furniture_availability,
    update_reservation_with_furniture, change_reservation_state,
    delete_reservation, cancel_beach_reservation, get_status_history
)
from datetime import date

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.route('/')
@login_required
@permission_required('beach.reservations.view')
def list():
    """Display reservation list with filters."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    customer_type = request.args.get('type', '')
    state = request.args.get('state', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

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


@reservations_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.create')
def create():
    """Create new reservation."""
    zones = get_all_zones()
    furniture_types = get_all_furniture_types()
    preferences = get_all_preferences()
    tags = get_all_tags()
    states = get_reservation_states()

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        hotel_guest_id = request.form.get('hotel_guest_id', type=int)
        reservation_date = request.form.get('reservation_date')
        num_people = request.form.get('num_people', 1, type=int)
        time_slot = request.form.get('time_slot', 'all_day')
        furniture_ids = request.form.getlist('furniture_ids', type=int)
        selected_prefs = request.form.getlist('preferences')
        notes = request.form.get('notes', '').strip()
        payment_status = request.form.get('payment_status', 'NO')
        charge_to_room = 1 if request.form.get('charge_to_room') else 0
        charge_reference = request.form.get('charge_reference', '').strip()

        # Pricing fields
        package_id = request.form.get('package_id', type=int) or None
        payment_ticket_number = request.form.get('payment_ticket_number', '').strip() or None
        price = request.form.get('price', 0.0, type=float)
        final_price = request.form.get('final_price', 0.0, type=float)
        paid = 1 if request.form.get('paid') else 0
        minimum_consumption_amount = request.form.get('minimum_consumption_amount', 0.0, type=float)
        minimum_consumption_policy_id = request.form.get('minimum_consumption_policy_id', type=int) or None

        # If hotel_guest_id is provided but no customer_id, create customer now
        if hotel_guest_id and not customer_id:
            try:
                additional_data = {}
                customer_phone = request.form.get('customer_phone', '').strip()
                customer_email = request.form.get('customer_email', '').strip()
                customer_country_code = request.form.get('customer_country_code', '+34').strip()
                if customer_phone:
                    additional_data['phone'] = customer_phone
                if customer_email:
                    additional_data['email'] = customer_email
                if customer_country_code:
                    additional_data['country_code'] = customer_country_code

                result = create_customer_from_hotel_guest(hotel_guest_id, additional_data)
                customer_id = result['customer_id']
            except ValueError as e:
                flash(f'Error al crear cliente: {str(e)}', 'error')
                return render_template('beach/reservation_form.html',
                                       mode='create', zones=zones, furniture_types=furniture_types,
                                       preferences=preferences, tags=tags, states=states)

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

        # Validate payment ticket requirement
        if paid and not payment_ticket_number:
            flash('Número de ticket requerido para reservas pagadas', 'error')
            return render_template('beach/reservation_form.html',
                                   mode='create', zones=zones, furniture_types=furniture_types,
                                   preferences=preferences, tags=tags, states=states,
                                   form_data=request.form)

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
                price=price,
                final_price=final_price,
                paid=paid,
                minimum_consumption_amount=minimum_consumption_amount,
                minimum_consumption_policy_id=minimum_consumption_policy_id,
                package_id=package_id,
                payment_ticket_number=payment_ticket_number,
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

    # For GET request, pre-select date and other parameters if provided (deep link from map)
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))

    # Pre-select customer if provided (deep link with state)
    preselected_customer = None
    preselected_hotel_guest = None

    customer_id_param = request.args.get('customer_id', type=int)
    hotel_guest_id_param = request.args.get('hotel_guest_id', type=int)

    if customer_id_param:
        from models.customer import get_customer_by_id, get_customer_preferences
        preselected_customer = get_customer_by_id(customer_id_param)
        if preselected_customer:
            # Get customer preferences for auto-fill
            prefs = get_customer_preferences(customer_id_param)
            preselected_customer['preference_codes'] = [p['code'] for p in prefs]

    elif hotel_guest_id_param:
        from models.hotel_guest import get_hotel_guest_by_id
        preselected_hotel_guest = get_hotel_guest_by_id(hotel_guest_id_param)

    # Pre-select multiple dates if provided (comma-separated)
    selected_dates = request.args.get('dates', '').split(',') if request.args.get('dates') else []
    selected_dates = [d.strip() for d in selected_dates if d.strip()]

    return render_template('beach/reservation_form.html',
                           mode='create', zones=zones, furniture_types=furniture_types,
                           preferences=preferences, tags=tags, states=states,
                           selected_date=selected_date,
                           selected_dates=selected_dates,
                           preselected_customer=preselected_customer,
                           preselected_hotel_guest=preselected_hotel_guest)


@reservations_bp.route('/<int:reservation_id>')
@login_required
@permission_required('beach.reservations.view')
def detail(reservation_id):
    """Display reservation detail view."""
    reservation = get_reservation_with_details(reservation_id)
    if not reservation:
        flash('Reserva no encontrada', 'error')
        return redirect(url_for('beach.reservations'))

    history = get_status_history(reservation_id)
    states = get_reservation_states()

    return render_template('beach/reservation_detail.html',
                           reservation=reservation, history=history, states=states)


@reservations_bp.route('/<int:reservation_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.edit')
def edit(reservation_id):
    """Edit existing reservation."""
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


@reservations_bp.route('/<int:reservation_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.reservations.delete')
def delete(reservation_id):
    """Delete reservation."""
    try:
        delete_reservation(reservation_id)
        flash('Reserva eliminada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.reservations'))


@reservations_bp.route('/<int:reservation_id>/cancel', methods=['POST'])
@login_required
@permission_required('beach.reservations.change_state')
def cancel(reservation_id):
    """Cancel reservation."""
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
