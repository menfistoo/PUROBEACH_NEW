"""
Furniture types configuration routes.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required
from models.zone import get_all_zones


def register_routes(bp):
    """Register furniture type routes on the blueprint."""

    @bp.route('/furniture-types')
    @login_required
    @permission_required('beach.config.furniture.view')
    def furniture_types():
        """Furniture types - redirect to unified furniture manager."""
        return redirect(url_for('beach.beach_config.furniture_manager', tab='furniture-types'))

    @bp.route('/furniture-types/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def furniture_types_create():
        """Create new furniture type - redirect to unified page."""
        # Redirect GET to unified page with create mode
        if request.method == 'GET':
            return redirect(url_for('beach.beach_config.furniture_manager',
                                    tab='furniture-types', create=1))

        # Handle POST for form submission
        from models.furniture_type import get_all_furniture_types, create_furniture_type

        data = {
            'type_code': request.form.get('type_code', '').strip().lower(),
            'display_name': request.form.get('display_name', '').strip(),
            'icon': request.form.get('icon', 'fa-umbrella-beach').strip(),
            'default_color': request.form.get('default_color', '#A0522D'),
            'min_capacity': request.form.get('min_capacity', 0, type=int),
            'max_capacity': request.form.get('max_capacity', 4, type=int),
            'default_capacity': request.form.get('default_capacity', 2, type=int),
            'is_suite_only': 1 if request.form.get('is_suite_only') else 0,
            'notes': request.form.get('notes', '').strip() or None,
            'map_shape': request.form.get('map_shape', 'rounded_rect'),
            'custom_svg': request.form.get('custom_svg', '').strip() or None,
            'default_width': request.form.get('default_width', 60, type=float),
            'default_height': request.form.get('default_height', 40, type=float),
            'border_radius': request.form.get('border_radius', 5, type=int),
            'fill_color': request.form.get('fill_color', '#A0522D'),
            'stroke_color': request.form.get('stroke_color', '#654321'),
            'stroke_width': request.form.get('stroke_width', 2, type=int),
            'default_rotation': 1 if request.form.get('default_rotation') else 0,
            'is_decorative': 1 if request.form.get('is_decorative') else 0,
            'number_prefix': request.form.get('number_prefix', '').strip() or None,
            'number_start': request.form.get('number_start', 1, type=int),
            'default_features': request.form.get('default_features', '').strip() or None,
            'allowed_zones': ','.join(request.form.getlist('allowed_zones')) or None,
        }

        if not data['type_code'] or not data['display_name']:
            flash('Codigo y nombre son obligatorios', 'error')
            return redirect(url_for('beach.beach_config.furniture_manager',
                                    tab='furniture-types', create=1))

        try:
            create_furniture_type(**data)
            flash('Tipo de mobiliario creado correctamente', 'success')
            return redirect(url_for('beach.beach_config.furniture_manager', tab='furniture-types'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al crear tipo: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.furniture_manager',
                                tab='furniture-types', create=1))

    @bp.route('/furniture-types/<int:type_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def furniture_types_edit(type_id):
        """Edit existing furniture type - redirect to unified page."""
        from models.furniture_type import get_furniture_type_by_id, update_furniture_type

        ftype = get_furniture_type_by_id(type_id)
        if not ftype:
            flash('Tipo de mobiliario no encontrado', 'error')
            return redirect(url_for('beach.beach_config.furniture_manager', tab='furniture-types'))

        # Redirect GET to unified page with edit mode
        if request.method == 'GET':
            return redirect(url_for('beach.beach_config.furniture_manager',
                                    tab='furniture-types', type_id=type_id))

        # Handle POST for form submission
        data = {
            'display_name': request.form.get('display_name', '').strip(),
            'icon': request.form.get('icon', 'fa-umbrella-beach').strip(),
            'default_color': request.form.get('default_color', '#A0522D'),
            'min_capacity': request.form.get('min_capacity', 0, type=int),
            'max_capacity': request.form.get('max_capacity', 4, type=int),
            'default_capacity': request.form.get('default_capacity', 2, type=int),
            'is_suite_only': 1 if request.form.get('is_suite_only') else 0,
            'notes': request.form.get('notes', '').strip() or None,
            'active': 1 if request.form.get('active') == '1' else 0,
            'map_shape': request.form.get('map_shape', 'rounded_rect'),
            'custom_svg': request.form.get('custom_svg', '').strip() or None,
            'default_width': request.form.get('default_width', 60, type=float),
            'default_height': request.form.get('default_height', 40, type=float),
            'border_radius': request.form.get('border_radius', 5, type=int),
            'fill_color': request.form.get('fill_color', '#A0522D'),
            'stroke_color': request.form.get('stroke_color', '#654321'),
            'stroke_width': request.form.get('stroke_width', 2, type=int),
            'default_rotation': 1 if request.form.get('default_rotation') else 0,
            'is_decorative': 1 if request.form.get('is_decorative') else 0,
            'number_prefix': request.form.get('number_prefix', '').strip() or None,
            'number_start': request.form.get('number_start', 1, type=int),
            'default_features': request.form.get('default_features', '').strip() or None,
            'allowed_zones': ','.join(request.form.getlist('allowed_zones')) or None,
        }

        if not data['display_name']:
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('beach.beach_config.furniture_manager',
                                    tab='furniture-types', type_id=type_id))

        try:
            updated = update_furniture_type(type_id, **data)
            if updated:
                flash('Tipo actualizado correctamente', 'success')
            else:
                flash('No se realizaron cambios', 'warning')
            return redirect(url_for('beach.beach_config.furniture_manager', tab='furniture-types'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.furniture_manager',
                                tab='furniture-types', type_id=type_id))

    @bp.route('/furniture-types/<int:type_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def furniture_types_delete(type_id):
        """Delete furniture type."""
        from models.furniture_type import delete_furniture_type

        try:
            deleted = delete_furniture_type(type_id)
            if deleted:
                flash('Tipo de mobiliario eliminado correctamente', 'success')
            else:
                flash('Error al eliminar tipo', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.furniture_manager', tab='furniture-types'))

    @bp.route('/furniture-types/preview', methods=['POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def furniture_types_preview():
        """Generate SVG preview for furniture type configuration (AJAX)."""
        from models.furniture_type import get_furniture_type_svg

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        svg_content = get_furniture_type_svg(data, state=None)
        width = float(data.get('default_width', 60) or 60)
        height = float(data.get('default_height', 40) or 40)
        preview = f'''<svg viewBox="0 0 {width} {height}"
                           width="{width}" height="{height}"
                           xmlns="http://www.w3.org/2000/svg">
                        {svg_content}
                      </svg>'''

        return jsonify({
            'success': True,
            'preview': preview
        })

    @bp.route('/furniture-types/<int:type_id>/next-number')
    @login_required
    @permission_required('beach.config.furniture.view')
    def furniture_types_next_number(type_id):
        """Get next available number for furniture type (AJAX)."""
        from models.furniture_type import get_next_number_for_type

        zone_id = request.args.get('zone_id', type=int)

        try:
            next_number = get_next_number_for_type(type_id, zone_id)
            return jsonify({
                'success': True,
                'next_number': next_number
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/furniture-types/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.config.furniture.manage')
    def furniture_types_reorder():
        """Update furniture types display order (AJAX)."""
        from models.furniture_type import update_furniture_types_order

        data = request.get_json()
        if not data or 'type_ids' not in data:
            return jsonify({'error': 'No type_ids provided'}), 400

        type_ids = data['type_ids']
        if not isinstance(type_ids, list):
            return jsonify({'error': 'type_ids must be a list'}), 400

        try:
            update_furniture_types_order(type_ids)
            return jsonify({'success': True, 'message': 'Orden actualizado'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
