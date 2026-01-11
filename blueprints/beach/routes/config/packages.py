"""
Package configuration routes.
CRUD operations for managing beach packages.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register package routes on the blueprint."""

    @bp.route('/packages')
    @login_required
    @permission_required('beach.config.packages.view')
    def packages():
        """Redirect to unified pricing page (packages tab)."""
        # Preserve show_inactive parameter
        show_inactive = request.args.get('show_inactive', '0')
        return redirect(url_for('beach.beach_config.pricing', tab='packages', show_inactive_packages=show_inactive))

    @bp.route('/packages/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.packages.manage')
    def packages_create():
        """Create new package."""
        from models.package import create_package
        from models.zone import get_all_zones
        from models.furniture_type import get_all_furniture_types

        if request.method == 'POST':
            # Get form fields
            package_name = request.form.get('package_name', '').strip()
            package_description = request.form.get('package_description', '').strip()
            base_price = float(request.form.get('base_price', 0) or 0)
            price_type = request.form.get('price_type', 'per_package')
            min_people = int(request.form.get('min_people', 1) or 1)
            standard_people = int(request.form.get('standard_people', 2) or 2)
            max_people = int(request.form.get('max_people', 4) or 4)
            furniture_types_included = request.form.get('furniture_types_included', '').strip()
            customer_type = request.form.get('customer_type', '').strip()
            zone_id = request.form.get('zone_id')
            valid_from = request.form.get('valid_from', '').strip()
            valid_until = request.form.get('valid_until', '').strip()
            display_order = int(request.form.get('display_order', 0) or 0)

            # Validate required fields
            if not package_name or base_price <= 0:
                flash('Nombre y precio base son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.packages_create'))

            try:
                # Convert empty strings to None
                zone_id = int(zone_id) if zone_id else None
                customer_type = customer_type if customer_type else None
                furniture_types_included = furniture_types_included if furniture_types_included else None
                valid_from = valid_from if valid_from else None
                valid_until = valid_until if valid_until else None

                create_package(
                    package_name=package_name,
                    base_price=base_price,
                    price_type=price_type,
                    package_description=package_description,
                    min_people=min_people,
                    standard_people=standard_people,
                    max_people=max_people,
                    furniture_types_included=furniture_types_included,
                    customer_type=customer_type,
                    zone_id=zone_id,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    display_order=display_order
                )
                flash('Paquete creado correctamente', 'success')
                return redirect(url_for('beach.beach_config.pricing', tab='packages'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al crear: {str(e)}', 'error')

        # Load zones and furniture types for dropdowns
        zones = get_all_zones()
        furniture_types = get_all_furniture_types()
        return render_template('beach/config/package_form.html',
                             package=None,
                             mode='create',
                             zones=zones,
                             furniture_types=furniture_types)

    @bp.route('/packages/<int:package_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.packages.manage')
    def packages_edit(package_id):
        """Edit existing package."""
        from models.package import get_package_by_id, update_package
        from models.zone import get_all_zones
        from models.furniture_type import get_all_furniture_types

        package = get_package_by_id(package_id)
        if not package:
            flash('Paquete no encontrado', 'error')
            return redirect(url_for('beach.beach_config.pricing', tab='packages'))

        if request.method == 'POST':
            # Get form fields
            package_name = request.form.get('package_name', '').strip()
            package_description = request.form.get('package_description', '').strip()
            base_price = float(request.form.get('base_price', 0) or 0)
            price_type = request.form.get('price_type', 'per_package')
            min_people = int(request.form.get('min_people', 1) or 1)
            standard_people = int(request.form.get('standard_people', 2) or 2)
            max_people = int(request.form.get('max_people', 4) or 4)
            furniture_types_included = request.form.get('furniture_types_included', '').strip()
            customer_type = request.form.get('customer_type', '').strip()
            zone_id = request.form.get('zone_id')
            valid_from = request.form.get('valid_from', '').strip()
            valid_until = request.form.get('valid_until', '').strip()
            display_order = int(request.form.get('display_order', 0) or 0)
            active = 1 if request.form.get('active') == '1' else 0

            # Validate required fields
            if not package_name or base_price <= 0:
                flash('Nombre y precio base son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.packages_edit', package_id=package_id))

            try:
                # Convert empty strings to None
                zone_id = int(zone_id) if zone_id else None
                customer_type = customer_type if customer_type else None
                furniture_types_included = furniture_types_included if furniture_types_included else None
                valid_from = valid_from if valid_from else None
                valid_until = valid_until if valid_until else None

                updated = update_package(
                    package_id,
                    package_name=package_name,
                    package_description=package_description,
                    base_price=base_price,
                    price_type=price_type,
                    min_people=min_people,
                    standard_people=standard_people,
                    max_people=max_people,
                    furniture_types_included=furniture_types_included,
                    customer_type=customer_type,
                    zone_id=zone_id,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    display_order=display_order,
                    active=active
                )

                if updated:
                    flash('Paquete actualizado correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.pricing', tab='packages'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al actualizar: {str(e)}', 'error')

        # Load zones and furniture types for dropdowns
        zones = get_all_zones()
        furniture_types = get_all_furniture_types()
        return render_template('beach/config/package_form.html',
                             package=package,
                             mode='edit',
                             zones=zones,
                             furniture_types=furniture_types)

    @bp.route('/packages/<int:package_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.packages.manage')
    def packages_delete(package_id):
        """Delete package (soft delete)."""
        from models.package import delete_package

        try:
            deleted = delete_package(package_id)
            if deleted:
                flash('Paquete eliminado correctamente', 'success')
            else:
                flash('Error al eliminar paquete', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.pricing', tab='packages'))

    @bp.route('/packages/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.config.packages.manage')
    def packages_reorder():
        """Reorder packages via AJAX."""
        from models.package import reorder_packages

        try:
            data = request.get_json()
            package_ids = data.get('order', [])

            if not package_ids:
                return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400

            # Convert to integers
            package_ids = [int(pid) for pid in package_ids]

            if reorder_packages(package_ids):
                return jsonify({'success': True, 'message': 'Orden actualizado'})
            else:
                return jsonify({'success': False, 'error': 'Error al reordenar'}), 400

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
