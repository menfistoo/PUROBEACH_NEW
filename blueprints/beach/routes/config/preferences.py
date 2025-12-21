"""
Preferences configuration routes.
"""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register preference routes on the blueprint."""

    @bp.route('/preferences')
    @login_required
    @permission_required('beach.furniture.view')
    def preferences():
        """List all customer preferences."""
        from models.preference import get_all_preferences
        all_preferences = get_all_preferences(active_only=False)
        return render_template('beach/config/preferences.html', preferences=all_preferences)

    @bp.route('/preferences/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.furniture.manage')
    def preferences_create():
        """Create new preference."""
        from models.preference import create_preference

        if request.method == 'POST':
            code = request.form.get('code', '').strip().lower()
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            maps_to_feature = request.form.get('maps_to_feature', '').strip()

            if not code or not name:
                flash('Codigo y nombre son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.preferences_create'))

            try:
                create_preference(
                    code=code,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    maps_to_feature=maps_to_feature if maps_to_feature else None
                )
                flash('Preferencia creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.preferences'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al crear: {str(e)}', 'error')

        return render_template('beach/config/preference_form.html',
                               preference=None, mode='create')

    @bp.route('/preferences/<int:preference_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.furniture.manage')
    def preferences_edit(preference_id):
        """Edit existing preference."""
        from models.preference import get_preference_by_id, update_preference

        pref = get_preference_by_id(preference_id)
        if not pref:
            flash('Preferencia no encontrada', 'error')
            return redirect(url_for('beach.beach_config.preferences'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            maps_to_feature = request.form.get('maps_to_feature', '').strip()
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.preferences_edit', preference_id=preference_id))

            try:
                updated = update_preference(
                    preference_id,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    maps_to_feature=maps_to_feature if maps_to_feature else None,
                    active=active
                )

                if updated:
                    flash('Preferencia actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.preferences'))

            except Exception as e:
                flash(f'Error al actualizar: {str(e)}', 'error')

        return render_template('beach/config/preference_form.html',
                               preference=pref, mode='edit')

    @bp.route('/preferences/<int:preference_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.manage')
    def preferences_delete(preference_id):
        """Delete preference."""
        from models.preference import delete_preference

        try:
            deleted = delete_preference(preference_id)
            if deleted:
                flash('Preferencia eliminada correctamente', 'success')
            else:
                flash('Error al eliminar preferencia', 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.preferences'))
