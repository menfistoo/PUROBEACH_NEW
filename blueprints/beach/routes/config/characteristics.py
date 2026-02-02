"""
Characteristics configuration routes.
Admin CRUD for the unified caracteristicas system.
"""

from flask import current_app, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register characteristic routes on the blueprint."""

    @bp.route('/characteristics')
    @login_required
    @permission_required('beach.config.characteristics.view')
    def characteristics():
        """Redirect to unified page (characteristics tab)."""
        show_inactive = request.args.get('show_inactive')
        params = {'tab': 'characteristics'}
        if show_inactive:
            params['show_inactive'] = show_inactive
        return redirect(url_for('beach.beach_config.tags_characteristics', **params), code=301)

    @bp.route('/characteristics/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.characteristics.manage')
    def characteristics_create():
        """Create new characteristic."""
        from models.characteristic import create_characteristic

        if request.method == 'POST':
            code = request.form.get('code', '').strip().lower().replace(' ', '_')
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            color = request.form.get('color', '#D4AF37').strip()

            if not code or not name:
                flash('Codigo y nombre son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.characteristics_create'))

            try:
                create_characteristic(
                    code=code,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    color=color
                )
                flash('Caracteristica creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.tags_characteristics', tab='characteristics'))

            except ValueError as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Se produjo un error. Contacte al administrador.', 'error')
            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al crear. Contacte al administrador.', 'error')

        return render_template(
            'beach/config/characteristic_form.html',
            characteristic=None,
            mode='create'
        )

    @bp.route('/characteristics/<int:characteristic_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.characteristics.manage')
    def characteristics_edit(characteristic_id):
        """Edit existing characteristic."""
        from models.characteristic import get_characteristic_by_id, update_characteristic

        char = get_characteristic_by_id(characteristic_id)
        if not char:
            flash('Caracteristica no encontrada', 'error')
            return redirect(url_for('beach.beach_config.tags_characteristics', tab='characteristics'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            color = request.form.get('color', '#D4AF37').strip()
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for(
                    'beach.beach_config.characteristics_edit',
                    characteristic_id=characteristic_id
                ))

            try:
                updated = update_characteristic(
                    characteristic_id,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    color=color,
                    active=active
                )

                if updated:
                    flash('Caracteristica actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.tags_characteristics', tab='characteristics'))

            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al actualizar. Contacte al administrador.', 'error')

        return render_template(
            'beach/config/characteristic_form.html',
            characteristic=char,
            mode='edit'
        )

    @bp.route('/characteristics/<int:characteristic_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.characteristics.manage')
    def characteristics_delete(characteristic_id):
        """Delete characteristic (soft delete)."""
        from models.characteristic import delete_characteristic

        try:
            deleted = delete_characteristic(characteristic_id)
            if deleted:
                flash('Caracteristica eliminada correctamente', 'success')
            else:
                flash('Error al eliminar caracteristica', 'error')
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            flash('Error al eliminar. Contacte al administrador.', 'error')

        return redirect(url_for('beach.beach_config.tags_characteristics', tab='characteristics'))

    @bp.route('/characteristics/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.config.characteristics.manage')
    def characteristics_reorder():
        """Reorder characteristics via AJAX."""
        from models.characteristic import reorder_characteristics

        data = request.get_json()
        ordered_ids = data.get('order', [])

        if not ordered_ids:
            return jsonify({'success': False, 'error': 'No order provided'}), 400

        try:
            reorder_characteristics(ordered_ids)
            return jsonify({'success': True})
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
