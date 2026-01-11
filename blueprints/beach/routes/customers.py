"""
Beach customer routes.
Handles customer CRUD operations, preferences, and deduplication.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils.decorators import permission_required
from models.customer import (
    get_customers_filtered, get_customer_with_details,
    create_customer, update_customer, delete_customer, get_customer_stats,
    set_customer_preferences, set_customer_tags, find_duplicates,
    merge_customers, find_potential_duplicates_for_customer
)
from models.characteristic import get_all_characteristics, get_characteristic_by_id
from models.reservation import sync_preferences_to_customer
from models.tag import get_all_tags

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/')
@login_required
@permission_required('beach.customers.view')
def list():
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


@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.create')
def create():
    """Create new customer."""
    preferences = get_all_characteristics()
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


@customers_bp.route('/<int:customer_id>')
@login_required
@permission_required('beach.customers.view')
def detail(customer_id):
    """Display customer detail view."""
    customer = get_customer_with_details(customer_id)
    if not customer:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('beach.customers'))

    # Find potential duplicates
    duplicates = find_potential_duplicates_for_customer(customer_id)

    return render_template('beach/customer_detail.html',
                           customer=customer, duplicates=duplicates)


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.edit')
def edit(customer_id):
    """Edit existing customer."""
    customer = get_customer_with_details(customer_id)
    if not customer:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('beach.customers'))

    preferences = get_all_characteristics()
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

            # Update preferences with bidirectional sync to reservations
            pref_ids = request.form.getlist('preferences')
            if pref_ids:
                # Convert preference IDs to codes for sync
                pref_codes = []
                for pid in pref_ids:
                    pref = get_characteristic_by_id(int(pid))
                    if pref:
                        pref_codes.append(pref['code'])
                preferences_csv = ','.join(pref_codes)
            else:
                preferences_csv = ''
            sync_preferences_to_customer(customer_id, preferences_csv, replace=True)

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


@customers_bp.route('/<int:customer_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.customers.edit')
def delete(customer_id):
    """Delete customer."""
    try:
        delete_customer(customer_id)
        flash('Cliente eliminado exitosamente', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('beach.customers'))


@customers_bp.route('/<int:customer_id>/merge', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.merge')
def merge(customer_id):
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
