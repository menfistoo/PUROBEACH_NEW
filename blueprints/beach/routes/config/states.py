"""
Reservation states configuration routes.
CRUD operations for managing configurable reservation states.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register state configuration routes on the blueprint."""

    @bp.route('/states')
    @login_required
    @permission_required('beach.config.states.view')
    def states():
        """List all reservation states."""
        from models.state import get_all_states
        show_inactive = request.args.get('show_inactive', '0') == '1'
        all_states = get_all_states(active_only=not show_inactive)
        return render_template('beach/config/states.html', states=all_states, show_inactive=show_inactive)

    @bp.route('/states/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.states.manage')
    def states_create():
        """Create new state."""
        from models.state import create_state

        if request.method == 'POST':
            code = request.form.get('code', '').strip().lower().replace(' ', '_')
            name = request.form.get('name', '').strip()
            color = request.form.get('color', '#6C757D')
            icon = request.form.get('icon', '').strip()
            is_releasing = 1 if request.form.get('is_availability_releasing') == '1' else 0
            priority = int(request.form.get('display_priority', 0) or 0)
            creates_incident = 1 if request.form.get('creates_incident') == '1' else 0

            if not code or not name:
                flash('Codigo y nombre son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.states_create'))

            try:
                create_state(
                    code=code,
                    name=name,
                    color=color,
                    icon=icon if icon else None,
                    is_availability_releasing=is_releasing,
                    display_priority=priority,
                    creates_incident=creates_incident
                )
                flash('Estado creado correctamente', 'success')
                return redirect(url_for('beach.beach_config.states'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al crear: {str(e)}', 'error')

        return render_template('beach/config/state_form.html', state=None, mode='create')

    @bp.route('/states/<int:state_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.states.manage')
    def states_edit(state_id):
        """Edit existing state."""
        from models.state import get_state_by_id, update_state

        state = get_state_by_id(state_id)
        if not state:
            flash('Estado no encontrado', 'error')
            return redirect(url_for('beach.beach_config.states'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            color = request.form.get('color', '#6C757D')
            icon = request.form.get('icon', '').strip()
            is_releasing = 1 if request.form.get('is_availability_releasing') == '1' else 0
            priority = int(request.form.get('display_priority', 0) or 0)
            creates_incident = 1 if request.form.get('creates_incident') == '1' else 0
            is_default = 1 if request.form.get('is_default') == '1' else 0
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.states_edit', state_id=state_id))

            try:
                updated = update_state(
                    state_id,
                    name=name,
                    color=color,
                    icon=icon if icon else None,
                    is_availability_releasing=is_releasing,
                    display_priority=priority,
                    creates_incident=creates_incident,
                    is_default=is_default,
                    active=active
                )

                if updated:
                    flash('Estado actualizado correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.states'))

            except Exception as e:
                flash(f'Error al actualizar: {str(e)}', 'error')

        return render_template('beach/config/state_form.html', state=state, mode='edit')

    @bp.route('/states/<int:state_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.states.manage')
    def states_delete(state_id):
        """Delete state (soft delete)."""
        from models.state import delete_state

        try:
            deleted = delete_state(state_id)
            if deleted:
                flash('Estado eliminado correctamente', 'success')
            else:
                flash('Error al eliminar estado', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.states'))

    @bp.route('/states/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.config.states.manage')
    def states_reorder():
        """Reorder states via AJAX."""
        from models.state import reorder_states

        try:
            data = request.get_json()
            state_ids = data.get('order', [])

            if not state_ids:
                return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400

            # Convert to integers
            state_ids = [int(sid) for sid in state_ids]

            if reorder_states(state_ids):
                return jsonify({'success': True, 'message': 'Orden actualizado'})
            else:
                return jsonify({'success': False, 'error': 'Error al reordenar'}), 400

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
