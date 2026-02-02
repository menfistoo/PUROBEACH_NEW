"""
Zone configuration routes.
"""

from flask import current_app, render_template, redirect, url_for, flash, request
from flask_login import login_required
from utils.decorators import permission_required
from models.zone import get_all_zones, get_zone_by_id, create_zone, update_zone, delete_zone


def register_routes(bp):
    """Register zone routes on the blueprint."""

    @bp.route('/zones')
    @login_required
    @permission_required('beach.zones.view')
    def zones():
        """List all beach zones - redirects to furniture manager."""
        # Redirect to the zones tab in furniture manager
        return redirect(url_for('beach.beach_config.furniture_manager', tab='zones'))

    @bp.route('/zones/save', methods=['POST'])
    @login_required
    @permission_required('beach.zones.manage')
    def zones_save():
        """Unified save route for create/update zone from furniture manager tab."""
        zone_id = request.form.get('zone_id')
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#F5E6D3')
        parent_zone_id = request.form.get('parent_zone_id')
        active = 1 if request.form.get('active') == '1' else 0
        redirect_tab = request.form.get('redirect_tab') == '1'

        if not name:
            flash('El nombre es obligatorio', 'error')
            if redirect_tab:
                if zone_id:
                    return redirect(url_for('beach.beach_config.furniture_manager', tab='zones', zone_id=zone_id))
                else:
                    return redirect(url_for('beach.beach_config.furniture_manager', tab='zones', create_zone=1))
            return redirect(url_for('beach.beach_config.zones'))

        try:
            parent_id = int(parent_zone_id) if parent_zone_id else None

            if zone_id:
                # Update existing zone
                zone_id = int(zone_id)
                if parent_id == zone_id:
                    flash('Una zona no puede ser su propio padre', 'error')
                    if redirect_tab:
                        return redirect(url_for('beach.beach_config.furniture_manager', tab='zones', zone_id=zone_id))
                    return redirect(url_for('beach.beach_config.zones_edit', zone_id=zone_id))

                updated = update_zone(
                    zone_id,
                    name=name,
                    description=description if description else None,
                    parent_zone_id=parent_id,
                    color=color,
                    active=active
                )
                if updated:
                    flash('Zona actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
            else:
                # Create new zone
                create_zone(
                    name=name,
                    description=description if description else None,
                    parent_zone_id=parent_id,
                    color=color
                )
                flash('Zona creada correctamente', 'success')

            if redirect_tab:
                return redirect(url_for('beach.beach_config.furniture_manager', tab='zones'))
            return redirect(url_for('beach.beach_config.zones'))

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            flash('Error al guardar zona. Contacte al administrador.', 'error')
            if redirect_tab:
                if zone_id:
                    return redirect(url_for('beach.beach_config.furniture_manager', tab='zones', zone_id=zone_id))
                else:
                    return redirect(url_for('beach.beach_config.furniture_manager', tab='zones', create_zone=1))
            return redirect(url_for('beach.beach_config.zones'))

    @bp.route('/zones/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.zones.manage')
    def zones_create():
        """Create new zone."""
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            color = request.form.get('color', '#F5E6D3')
            parent_zone_id = request.form.get('parent_zone_id')

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.zones_create'))

            try:
                parent_id = int(parent_zone_id) if parent_zone_id else None
                create_zone(
                    name=name,
                    description=description if description else None,
                    parent_zone_id=parent_id,
                    color=color
                )
                flash('Zona creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.zones'))

            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al crear zona. Contacte al administrador.', 'error')
                return redirect(url_for('beach.beach_config.zones_create'))

        # GET: Show form
        parent_zones = get_all_zones()
        return render_template('beach/config/zone_form.html',
                               zone=None, parent_zones=parent_zones, mode='create')

    @bp.route('/zones/<int:zone_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.zones.manage')
    def zones_edit(zone_id):
        """Edit existing zone."""
        zone = get_zone_by_id(zone_id)
        if not zone:
            flash('Zona no encontrada', 'error')
            return redirect(url_for('beach.beach_config.zones'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            color = request.form.get('color', '#F5E6D3')
            parent_zone_id = request.form.get('parent_zone_id')
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.zones_edit', zone_id=zone_id))

            try:
                parent_id = int(parent_zone_id) if parent_zone_id else None
                if parent_id == zone_id:
                    flash('Una zona no puede ser su propio padre', 'error')
                    return redirect(url_for('beach.beach_config.zones_edit', zone_id=zone_id))

                updated = update_zone(
                    zone_id,
                    name=name,
                    description=description if description else None,
                    parent_zone_id=parent_id,
                    color=color,
                    active=active
                )

                if updated:
                    flash('Zona actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.zones'))

            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al actualizar zona. Contacte al administrador.', 'error')

        # GET: Show form
        parent_zones = [z for z in get_all_zones() if z['id'] != zone_id]
        return render_template('beach/config/zone_form.html',
                               zone=zone, parent_zones=parent_zones, mode='edit')

    @bp.route('/zones/<int:zone_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.zones.manage')
    def zones_delete(zone_id):
        """Delete zone."""
        redirect_tab = request.form.get('redirect_tab') == '1'

        try:
            deleted = delete_zone(zone_id)
            if deleted:
                flash('Zona eliminada correctamente', 'success')
            else:
                flash('Error al eliminar zona', 'error')
        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            flash('Se produjo un error. Contacte al administrador.', 'error')
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            flash('Error al eliminar. Contacte al administrador.', 'error')

        if redirect_tab:
            return redirect(url_for('beach.beach_config.furniture_manager', tab='zones'))
        return redirect(url_for('beach.beach_config.zones'))
