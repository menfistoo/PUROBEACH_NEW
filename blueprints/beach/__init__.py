"""
Beach blueprint initialization.
Registers all beach-related routes (map, customers, reservations, config).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture
from models.customer import (
    get_customers_filtered, get_customer_with_details, get_customer_by_id,
    create_customer, update_customer, delete_customer, get_customer_stats,
    set_customer_preferences, set_customer_tags, find_duplicates,
    merge_customers, find_potential_duplicates_for_customer, search_customers
)
from models.preference import get_all_preferences
from models.tag import get_all_tags
from models.hotel_guest import get_guests_by_room, search_guests
from datetime import date

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
    """Search customers for autocomplete."""
    query = request.args.get('q', '')
    customer_type = request.args.get('type', None)

    if len(query) < 2:
        return jsonify({'customers': []})

    customers = search_customers(query, customer_type)

    return jsonify({
        'customers': [{
            'id': c['id'],
            'first_name': c['first_name'],
            'last_name': c['last_name'],
            'customer_type': c['customer_type'],
            'room_number': c['room_number'],
            'phone': c['phone'],
            'email': c['email'],
            'vip_status': c['vip_status'],
            'display_name': f"{c['first_name']} {c['last_name'] or ''}" +
                           (f" (Hab. {c['room_number']})" if c['room_number'] else '')
        } for c in customers[:20]]
    })


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
# RESERVATIONS ROUTES (Placeholder for Phase 6)
# ============================================================================

@beach_bp.route('/reservations')
@login_required
@permission_required('beach.reservations.view')
def reservations():
    """Display reservation list."""
    return render_template('beach/reservations.html')
