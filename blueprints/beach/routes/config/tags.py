"""
Tags configuration routes.
Includes the unified tags + characteristics page.
"""

from flask import current_app, render_template, redirect, url_for, flash, request
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register tag routes on the blueprint."""

    @bp.route('/tags-characteristics')
    @login_required
    @permission_required('beach.config.characteristics.view')
    def tags_characteristics():
        """Unified tags and characteristics configuration page."""
        from models.tag import get_all_tags
        from models.characteristic import get_all_characteristics

        active_tab = request.args.get('tab', 'tags')
        show_inactive = request.args.get('show_inactive') == '1'

        tags = get_all_tags(active_only=not show_inactive)
        characteristics = get_all_characteristics(active_only=not show_inactive)

        return render_template(
            'beach/config/tags_characteristics.html',
            active_tab=active_tab,
            tags=tags,
            characteristics=characteristics,
            show_inactive=show_inactive
        )

    @bp.route('/tags')
    @login_required
    @permission_required('beach.config.furniture.view')
    def tags():
        """Redirect to unified page (tags tab)."""
        return redirect(url_for('beach.beach_config.tags_characteristics', tab='tags'), code=301)

    @bp.route('/tags/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def tags_create():
        """Create new tag."""
        from models.tag import create_tag

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            color = request.form.get('color', '#6C757D')
            description = request.form.get('description', '').strip()

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.tags_create'))

            try:
                create_tag(
                    name=name,
                    color=color,
                    description=description if description else None
                )
                flash('Etiqueta creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.tags_characteristics', tab='tags'))

            except ValueError as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Se produjo un error. Contacte al administrador.', 'error')
            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al crear. Contacte al administrador.', 'error')

        return render_template('beach/config/tag_form.html', tag=None, mode='create')

    @bp.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def tags_edit(tag_id):
        """Edit existing tag."""
        from models.tag import get_tag_by_id, update_tag

        tag = get_tag_by_id(tag_id)
        if not tag:
            flash('Etiqueta no encontrada', 'error')
            return redirect(url_for('beach.beach_config.tags_characteristics', tab='tags'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            color = request.form.get('color', '#6C757D')
            description = request.form.get('description', '').strip()
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for('beach.beach_config.tags_edit', tag_id=tag_id))

            try:
                updated = update_tag(
                    tag_id,
                    name=name,
                    color=color,
                    description=description if description else None,
                    active=active
                )

                if updated:
                    flash('Etiqueta actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.tags_characteristics', tab='tags'))

            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                flash('Error al actualizar. Contacte al administrador.', 'error')

        return render_template('beach/config/tag_form.html', tag=tag, mode='edit')

    @bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def tags_delete(tag_id):
        """Delete tag."""
        from models.tag import delete_tag

        try:
            deleted = delete_tag(tag_id)
            if deleted:
                flash('Etiqueta eliminada correctamente', 'success')
            else:
                flash('Error al eliminar etiqueta', 'error')
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            flash('Error al eliminar. Contacte al administrador.', 'error')

        return redirect(url_for('beach.beach_config.tags_characteristics', tab='tags'))
