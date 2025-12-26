"""
Package configuration routes.
Manages beach packages for reservation pricing.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from utils.decorators import permission_required
from models.package import (
    get_all_packages,
    get_package_by_id,
    create_package,
    update_package,
    toggle_package_active,
    delete_package,
    validate_package_data
)
from models.zone import get_all_zones
from models.furniture_type import get_all_furniture_types


packages_bp = Blueprint('packages', __name__, url_prefix='/beach/config/packages')


# =============================================================================
# LIST VIEW
# =============================================================================

@packages_bp.route('/', methods=['GET'])
@login_required
@permission_required('beach.config.packages.view')
def list_packages():
    """
    Display list of all packages.
    """
    # Get filter parameters
    customer_type = request.args.get('customer_type')
    active_filter = request.args.get('active')
    search = request.args.get('search', '').strip()

    # Apply filters
    active_only = active_filter == '1' if active_filter else None
    packages = get_all_packages(
        active_only=active_only if active_only is not None else False,
        customer_type=customer_type if customer_type else None
    )

    # Apply search filter (client-side for simplicity)
    if search:
        search_lower = search.lower()
        packages = [
            p for p in packages
            if search_lower in p['package_name'].lower()
            or (p.get('package_description') and search_lower in p['package_description'].lower())
        ]

    # Count active packages
    active_count = sum(1 for p in packages if p['active'] == 1)

    return render_template(
        'beach/config/packages/list.html',
        packages=packages,
        active_count=active_count,
        filters={
            'customer_type': customer_type,
            'active': active_filter,
            'search': search
        }
    )


# =============================================================================
# CREATE
# =============================================================================

@packages_bp.route('/new', methods=['GET'])
@login_required
@permission_required('beach.config.packages.create')
def new_package():
    """
    Display form to create a new package.
    """
    zones = get_all_zones()
    furniture_types = get_all_furniture_types()

    return render_template(
        'beach/config/packages/form.html',
        package=None,
        zones=zones,
        furniture_types=furniture_types,
        is_edit=False
    )


@packages_bp.route('/', methods=['POST'])
@login_required
@permission_required('beach.config.packages.create')
def create_package_route():
    """
    Handle package creation form submission.
    """
    try:
        # Extract form data
        data = {
            'package_name': request.form.get('package_name', '').strip(),
            'package_description': request.form.get('package_description', '').strip() or None,
            'base_price': float(request.form.get('base_price', 0)),
            'price_type': request.form.get('price_type', 'per_person'),
            'min_people': int(request.form.get('min_people', 1)),
            'standard_people': int(request.form.get('standard_people', 2)),
            'max_people': int(request.form.get('max_people', 4)),
            'furniture_types_included': ','.join(request.form.getlist('furniture_types_included')) or None,
            'customer_type': request.form.get('customer_type') or None,
            'zone_id': int(request.form.get('zone_id')) if request.form.get('zone_id') else None,
            'valid_from': request.form.get('valid_from') or None,
            'valid_until': request.form.get('valid_until') or None,
            'active': 1 if request.form.get('active') == 'on' else 0,
            'display_order': int(request.form.get('display_order', 0))
        }

        # Create package
        success, package_id, message = create_package(data)

        if success:
            flash(message, 'success')
            return redirect(url_for('packages.list_packages'))
        else:
            flash(message, 'error')
            # Re-render form with data
            zones = get_all_zones()
            furniture_types = get_all_furniture_types()
            return render_template(
                'beach/config/packages/form.html',
                package=data,
                zones=zones,
                furniture_types=furniture_types,
                is_edit=False
            )

    except ValueError as e:
        flash(f'Error en los datos del formulario: {str(e)}', 'error')
        return redirect(url_for('packages.new_package'))
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
        return redirect(url_for('packages.new_package'))


# =============================================================================
# EDIT
# =============================================================================

@packages_bp.route('/<int:package_id>/edit', methods=['GET'])
@login_required
@permission_required('beach.config.packages.edit')
def edit_package(package_id):
    """
    Display form to edit an existing package.
    """
    package = get_package_by_id(package_id)
    if not package:
        flash('Paquete no encontrado', 'error')
        return redirect(url_for('packages.list_packages'))

    zones = get_all_zones()
    furniture_types = get_all_furniture_types()

    return render_template(
        'beach/config/packages/form.html',
        package=package,
        zones=zones,
        furniture_types=furniture_types,
        is_edit=True
    )


@packages_bp.route('/<int:package_id>', methods=['POST'])
@login_required
@permission_required('beach.config.packages.edit')
def update_package_route(package_id):
    """
    Handle package update form submission.
    """
    try:
        # Extract form data
        data = {
            'package_name': request.form.get('package_name', '').strip(),
            'package_description': request.form.get('package_description', '').strip() or None,
            'base_price': float(request.form.get('base_price', 0)),
            'price_type': request.form.get('price_type', 'per_person'),
            'min_people': int(request.form.get('min_people', 1)),
            'standard_people': int(request.form.get('standard_people', 2)),
            'max_people': int(request.form.get('max_people', 4)),
            'furniture_types_included': ','.join(request.form.getlist('furniture_types_included')) or None,
            'customer_type': request.form.get('customer_type') or None,
            'zone_id': int(request.form.get('zone_id')) if request.form.get('zone_id') else None,
            'valid_from': request.form.get('valid_from') or None,
            'valid_until': request.form.get('valid_until') or None,
            'active': 1 if request.form.get('active') == 'on' else 0,
            'display_order': int(request.form.get('display_order', 0))
        }

        # Update package
        success, message = update_package(package_id, data)

        if success:
            flash(message, 'success')
            return redirect(url_for('packages.list_packages'))
        else:
            flash(message, 'error')
            # Re-render form with data
            zones = get_all_zones()
            furniture_types = get_all_furniture_types()
            data['id'] = package_id
            return render_template(
                'beach/config/packages/form.html',
                package=data,
                zones=zones,
                furniture_types=furniture_types,
                is_edit=True
            )

    except ValueError as e:
        flash(f'Error en los datos del formulario: {str(e)}', 'error')
        return redirect(url_for('packages.edit_package', package_id=package_id))
    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'error')
        return redirect(url_for('packages.edit_package', package_id=package_id))


# =============================================================================
# TOGGLE & DELETE
# =============================================================================

@packages_bp.route('/<int:package_id>/toggle', methods=['POST'])
@login_required
@permission_required('beach.config.packages.edit')
def toggle_package_route(package_id):
    """
    Toggle package active status.
    """
    success, message = toggle_package_active(package_id)

    if request.is_json:
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('packages.list_packages'))


@packages_bp.route('/<int:package_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.config.packages.delete')
def delete_package_route(package_id):
    """
    Delete a package (soft delete).
    """
    success, message = delete_package(package_id)

    if request.is_json:
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('packages.list_packages'))


# =============================================================================
# EXPORT
# =============================================================================

__all__ = ['packages_bp']
