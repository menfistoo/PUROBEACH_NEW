"""
Minimum consumption configuration routes.
Manages minimum consumption policies for reservations.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from utils.decorators import permission_required
from models.pricing import (
    get_all_minimum_consumption_policies,
    get_minimum_consumption_policy_by_id,
    create_minimum_consumption_policy,
    update_minimum_consumption_policy,
    delete_minimum_consumption_policy
)
from models.zone import get_all_zones
from models.furniture_type import get_all_furniture_types


minimum_consumption_bp = Blueprint(
    'minimum_consumption',
    __name__,
    url_prefix='/beach/config/minimum-consumption'
)


# =============================================================================
# LIST VIEW
# =============================================================================

@minimum_consumption_bp.route('/', methods=['GET'])
@login_required
@permission_required('beach.config.minimum_consumption.view')
def list_policies():
    """
    Display list of all minimum consumption policies.
    """
    # Get filter parameters
    active_filter = request.args.get('active')
    search = request.args.get('search', '').strip()

    # Get policies
    active_only = active_filter == '1' if active_filter else None
    policies = get_all_minimum_consumption_policies(
        active_only=active_only if active_only is not None else False
    )

    # Apply search filter
    if search:
        search_lower = search.lower()
        policies = [
            p for p in policies
            if search_lower in p['policy_name'].lower()
            or (p.get('policy_description') and search_lower in p['policy_description'].lower())
        ]

    # Count active policies
    active_count = sum(1 for p in policies if p['is_active'] == 1)

    return render_template(
        'beach/config/minimum_consumption/list.html',
        policies=policies,
        active_count=active_count,
        filters={
            'active': active_filter,
            'search': search
        }
    )


# =============================================================================
# CREATE
# =============================================================================

@minimum_consumption_bp.route('/new', methods=['GET'])
@login_required
@permission_required('beach.config.minimum_consumption.manage')
def new_policy():
    """
    Display form to create a new minimum consumption policy.
    """
    zones = get_all_zones()
    furniture_types = get_all_furniture_types()

    return render_template(
        'beach/config/minimum_consumption/form.html',
        policy=None,
        zones=zones,
        furniture_types=furniture_types,
        is_edit=False
    )


@minimum_consumption_bp.route('/', methods=['POST'])
@login_required
@permission_required('beach.config.minimum_consumption.manage')
def create_policy_route():
    """
    Handle policy creation form submission.
    """
    try:
        # Extract form data
        data = {
            'policy_name': request.form.get('policy_name', '').strip(),
            'policy_description': request.form.get('policy_description', '').strip() or None,
            'minimum_amount': float(request.form.get('minimum_amount', 0)),
            'calculation_type': request.form.get('calculation_type', 'per_reservation'),
            'furniture_type': request.form.get('furniture_type') or None,
            'customer_type': request.form.get('customer_type') or None,
            'zone_id': int(request.form.get('zone_id')) if request.form.get('zone_id') else None,
            'priority_order': int(request.form.get('priority_order', 0)),
            'is_active': 1 if request.form.get('is_active') == 'on' else 0
        }

        # Create policy
        success, policy_id, message = create_minimum_consumption_policy(data)

        if success:
            flash(message, 'success')
            return redirect(url_for('minimum_consumption.list_policies'))
        else:
            flash(message, 'error')
            # Re-render form with data
            zones = get_all_zones()
            furniture_types = get_all_furniture_types()
            return render_template(
                'beach/config/minimum_consumption/form.html',
                policy=data,
                zones=zones,
                furniture_types=furniture_types,
                is_edit=False
            )

    except ValueError as e:
        flash(f'Error en los datos del formulario: {str(e)}', 'error')
        return redirect(url_for('minimum_consumption.new_policy'))
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
        return redirect(url_for('minimum_consumption.new_policy'))


# =============================================================================
# EDIT
# =============================================================================

@minimum_consumption_bp.route('/<int:policy_id>/edit', methods=['GET'])
@login_required
@permission_required('beach.config.minimum_consumption.manage')
def edit_policy(policy_id):
    """
    Display form to edit an existing policy.
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy:
        flash('Política no encontrada', 'error')
        return redirect(url_for('minimum_consumption.list_policies'))

    zones = get_all_zones()
    furniture_types = get_all_furniture_types()

    return render_template(
        'beach/config/minimum_consumption/form.html',
        policy=policy,
        zones=zones,
        furniture_types=furniture_types,
        is_edit=True
    )


@minimum_consumption_bp.route('/<int:policy_id>', methods=['POST'])
@login_required
@permission_required('beach.config.minimum_consumption.manage')
def update_policy_route(policy_id):
    """
    Handle policy update form submission.
    """
    try:
        # Extract form data
        data = {
            'policy_name': request.form.get('policy_name', '').strip(),
            'policy_description': request.form.get('policy_description', '').strip() or None,
            'minimum_amount': float(request.form.get('minimum_amount', 0)),
            'calculation_type': request.form.get('calculation_type', 'per_reservation'),
            'furniture_type': request.form.get('furniture_type') or None,
            'customer_type': request.form.get('customer_type') or None,
            'zone_id': int(request.form.get('zone_id')) if request.form.get('zone_id') else None,
            'priority_order': int(request.form.get('priority_order', 0)),
            'is_active': 1 if request.form.get('is_active') == 'on' else 0
        }

        # Update policy
        success, message = update_minimum_consumption_policy(policy_id, data)

        if success:
            flash(message, 'success')
            return redirect(url_for('minimum_consumption.list_policies'))
        else:
            flash(message, 'error')
            # Re-render form with data
            zones = get_all_zones()
            furniture_types = get_all_furniture_types()
            data['id'] = policy_id
            return render_template(
                'beach/config/minimum_consumption/form.html',
                policy=data,
                zones=zones,
                furniture_types=furniture_types,
                is_edit=True
            )

    except ValueError as e:
        flash(f'Error en los datos del formulario: {str(e)}', 'error')
        return redirect(url_for('minimum_consumption.edit_policy', policy_id=policy_id))
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
        return redirect(url_for('minimum_consumption.edit_policy', policy_id=policy_id))


# =============================================================================
# DELETE
# =============================================================================

@minimum_consumption_bp.route('/<int:policy_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.config.minimum_consumption.manage')
def delete_policy_route(policy_id):
    """
    Delete a policy.
    """
    success, message = delete_minimum_consumption_policy(policy_id)

    if request.is_json:
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('minimum_consumption.list_policies'))


# =============================================================================
# EXPORT
# =============================================================================

__all__ = ['minimum_consumption_bp']
