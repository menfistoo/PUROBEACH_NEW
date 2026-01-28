"""
Minimum consumption policy configuration routes.
CRUD operations for managing consumption policies.
"""

from flask import Blueprint, Response, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp: Blueprint) -> None:
    """Register minimum consumption routes on the blueprint."""

    @bp.route('/minimum-consumption')
    @login_required
    @permission_required('beach.config.minimum_consumption.view')
    def minimum_consumption():
        """Redirect to unified pricing page (minimum consumption tab)."""
        # Preserve show_inactive parameter
        show_inactive = request.args.get('show_inactive', '0')
        return redirect(url_for('beach.beach_config.pricing', tab='minimum-consumption', show_inactive_policies=show_inactive))

    @bp.route('/minimum-consumption/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.minimum_consumption.manage')
    def minimum_consumption_create():
        """Create new minimum consumption policy."""
        from models.pricing import create_minimum_consumption_policy
        from models.zone import get_all_zones
        from models.furniture_type import get_all_furniture_types

        if request.method == 'POST':
            # Get form fields
            policy_name = request.form.get('policy_name', '').strip()
            policy_description = request.form.get('policy_description', '').strip()
            minimum_amount = float(request.form.get('minimum_amount', 0) or 0)
            calculation_type = request.form.get('calculation_type', 'per_reservation')
            furniture_type = request.form.get('furniture_type', '').strip()
            customer_type = request.form.get('customer_type', '').strip()
            zone_id = request.form.get('zone_id')
            priority_order = int(request.form.get('priority_order', 0) or 0)

            # Validate required fields (0€ allowed = "included")
            if not policy_name or minimum_amount < 0:
                flash('Nombre es obligatorio y monto no puede ser negativo', 'error')
                return redirect(url_for('beach.beach_config.minimum_consumption_create'))

            try:
                # Convert empty strings to None
                zone_id = int(zone_id) if zone_id else None
                customer_type = customer_type if customer_type else None
                furniture_type = furniture_type if furniture_type else None

                create_minimum_consumption_policy(
                    policy_name=policy_name,
                    minimum_amount=minimum_amount,
                    policy_description=policy_description,
                    calculation_type=calculation_type,
                    furniture_type=furniture_type,
                    customer_type=customer_type,
                    zone_id=zone_id,
                    priority_order=priority_order
                )
                flash('Política de consumo mínimo creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.pricing', tab='minimum-consumption'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al crear: {str(e)}', 'error')

        # Load zones and furniture types for dropdowns
        zones = get_all_zones()
        furniture_types = get_all_furniture_types()

        # Get prefill customer type from URL parameter
        prefill_customer_type = request.args.get('customer_type', '')
        if prefill_customer_type not in ('interno', 'externo'):
            prefill_customer_type = None

        return render_template('beach/config/minimum_consumption_form.html',
                             policy=None,
                             mode='create',
                             zones=zones,
                             furniture_types=furniture_types,
                             prefill_customer_type=prefill_customer_type)

    @bp.route('/minimum-consumption/<int:policy_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.minimum_consumption.manage')
    def minimum_consumption_edit(policy_id):
        """Edit existing minimum consumption policy."""
        from models.pricing import get_minimum_consumption_policy_by_id, update_minimum_consumption_policy
        from models.zone import get_all_zones
        from models.furniture_type import get_all_furniture_types

        policy = get_minimum_consumption_policy_by_id(policy_id)
        if not policy:
            flash('Política no encontrada', 'error')
            return redirect(url_for('beach.beach_config.pricing', tab='minimum-consumption'))

        if request.method == 'POST':
            # Get form fields
            policy_name = request.form.get('policy_name', '').strip()
            policy_description = request.form.get('policy_description', '').strip()
            minimum_amount = float(request.form.get('minimum_amount', 0) or 0)
            calculation_type = request.form.get('calculation_type', 'per_reservation')
            furniture_type = request.form.get('furniture_type', '').strip()
            customer_type = request.form.get('customer_type', '').strip()
            zone_id = request.form.get('zone_id')
            priority_order = int(request.form.get('priority_order', 0) or 0)
            is_active = 1 if request.form.get('is_active') == '1' else 0

            # Validate required fields (0€ allowed = "included")
            if not policy_name or minimum_amount < 0:
                flash('Nombre es obligatorio y monto no puede ser negativo', 'error')
                return redirect(url_for('beach.beach_config.minimum_consumption_edit', policy_id=policy_id))

            try:
                # Convert empty strings to None
                zone_id = int(zone_id) if zone_id else None
                customer_type = customer_type if customer_type else None
                furniture_type = furniture_type if furniture_type else None

                updated = update_minimum_consumption_policy(
                    policy_id,
                    policy_name=policy_name,
                    policy_description=policy_description,
                    minimum_amount=minimum_amount,
                    calculation_type=calculation_type,
                    furniture_type=furniture_type,
                    customer_type=customer_type,
                    zone_id=zone_id,
                    priority_order=priority_order,
                    is_active=is_active
                )

                if updated:
                    flash('Política actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.pricing', tab='minimum-consumption'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al actualizar: {str(e)}', 'error')

        # Load zones and furniture types for dropdowns
        zones = get_all_zones()
        furniture_types = get_all_furniture_types()
        return render_template('beach/config/minimum_consumption_form.html',
                             policy=policy,
                             mode='edit',
                             zones=zones,
                             furniture_types=furniture_types)

    @bp.route('/minimum-consumption/<int:policy_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.minimum_consumption.manage')
    def minimum_consumption_delete(policy_id):
        """Delete minimum consumption policy (soft delete)."""
        from models.pricing import delete_minimum_consumption_policy

        try:
            deleted = delete_minimum_consumption_policy(policy_id)
            if deleted:
                flash('Política eliminada correctamente', 'success')
            else:
                flash('Error al eliminar política', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.pricing', tab='minimum-consumption'))

    @bp.route('/minimum-consumption/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.config.minimum_consumption.manage')
    def minimum_consumption_reorder():
        """Reorder minimum consumption policies via AJAX."""
        from models.pricing import reorder_minimum_consumption_policies

        try:
            data = request.get_json()
            policy_ids = data.get('order', [])

            if not policy_ids:
                return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400

            # Convert to integers
            policy_ids = [int(pid) for pid in policy_ids]

            if reorder_minimum_consumption_policies(policy_ids):
                return jsonify({'success': True, 'message': 'Orden actualizado'})
            else:
                return jsonify({'success': False, 'error': 'Error al reordenar'}), 400

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
