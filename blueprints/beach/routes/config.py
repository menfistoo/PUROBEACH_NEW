"""
Beach infrastructure configuration routes.
Handles zones, furniture types, furniture, preferences, and tags management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

from utils.decorators import permission_required
from models.zone import (get_all_zones, get_zone_by_id, create_zone,
                          update_zone, delete_zone)
from models.furniture import (get_all_furniture, get_furniture_by_id,
                                get_furniture_types, create_furniture,
                                update_furniture, delete_furniture)

config_bp = Blueprint('beach_config', __name__, url_prefix='/config')


# ==================== Zones Routes ====================

@config_bp.route('/zones')
@login_required
@permission_required('beach.zones.view')
def zones():
    """List all beach zones."""
    all_zones = get_all_zones(active_only=False)
    return render_template('beach/config/zones.html', zones=all_zones)


@config_bp.route('/zones/create', methods=['GET', 'POST'])
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
            zone_id = create_zone(
                name=name,
                description=description if description else None,
                parent_zone_id=parent_id,
                color=color
            )
            flash('Zona creada correctamente', 'success')
            return redirect(url_for('beach.beach_config.zones'))

        except Exception as e:
            flash(f'Error al crear zona: {str(e)}', 'error')
            return redirect(url_for('beach.beach_config.zones_create'))

    # GET: Show form
    parent_zones = get_all_zones()
    return render_template('beach/config/zone_form.html',
                           zone=None, parent_zones=parent_zones, mode='create')


@config_bp.route('/zones/<int:zone_id>/edit', methods=['GET', 'POST'])
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
            # Prevent setting self as parent
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
            flash(f'Error al actualizar zona: {str(e)}', 'error')

    # GET: Show form
    parent_zones = [z for z in get_all_zones() if z['id'] != zone_id]
    return render_template('beach/config/zone_form.html',
                           zone=zone, parent_zones=parent_zones, mode='edit')


@config_bp.route('/zones/<int:zone_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.zones.manage')
def zones_delete(zone_id):
    """Delete zone."""
    try:
        deleted = delete_zone(zone_id)
        if deleted:
            flash('Zona eliminada correctamente', 'success')
        else:
            flash('Error al eliminar zona', 'error')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.beach_config.zones'))


# ==================== Furniture Types Routes ====================

@config_bp.route('/furniture-types')
@login_required
@permission_required('beach.furniture.view')
def furniture_types():
    """List all furniture types with two-panel layout."""
    from models.furniture_type import get_all_furniture_types
    types = get_all_furniture_types(active_only=False)
    zones = get_all_zones()
    return render_template('beach/config/furniture_types.html',
                           furniture_types=types,
                           zones=zones,
                           selected_type=None,
                           mode=None)


@config_bp.route('/furniture-types/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_types_create():
    """Create new furniture type with enhanced fields."""
    from models.furniture_type import get_all_furniture_types, create_furniture_type

    if request.method == 'POST':
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
            # Enhanced fields
            'map_shape': request.form.get('map_shape', 'rounded_rect'),
            'custom_svg': request.form.get('custom_svg', '').strip() or None,
            'default_width': request.form.get('default_width', 60, type=float),
            'default_height': request.form.get('default_height', 40, type=float),
            'border_radius': request.form.get('border_radius', 5, type=int),
            'fill_color': request.form.get('fill_color', '#A0522D'),
            'stroke_color': request.form.get('stroke_color', '#654321'),
            'stroke_width': request.form.get('stroke_width', 2, type=int),
            # Note: status_colors are NOT set here - they come from reservation states config
            'default_rotation': 1 if request.form.get('default_rotation') else 0,
            'is_decorative': 1 if request.form.get('is_decorative') else 0,
            'number_prefix': request.form.get('number_prefix', '').strip() or None,
            'number_start': request.form.get('number_start', 1, type=int),
            'default_features': request.form.get('default_features', '').strip() or None,
            'allowed_zones': ','.join(request.form.getlist('allowed_zones')) or None,
        }

        if not data['type_code'] or not data['display_name']:
            flash('Código y nombre son obligatorios', 'error')
            types = get_all_furniture_types(active_only=False)
            zones = get_all_zones()
            return render_template('beach/config/furniture_types.html',
                                   furniture_types=types, zones=zones,
                                   form_data=data, mode='create')

        try:
            create_furniture_type(**data)
            flash('Tipo de mobiliario creado correctamente', 'success')
            return redirect(url_for('beach.beach_config.furniture_types'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al crear tipo: {str(e)}', 'error')

        types = get_all_furniture_types(active_only=False)
        zones = get_all_zones()
        return render_template('beach/config/furniture_types.html',
                               furniture_types=types, zones=zones,
                               form_data=data, mode='create')

    # GET: Show form in right panel
    types = get_all_furniture_types(active_only=False)
    zones = get_all_zones()
    return render_template('beach/config/furniture_types.html',
                           furniture_types=types, zones=zones,
                           selected_type=None, mode='create')


@config_bp.route('/furniture-types/<int:type_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_types_edit(type_id):
    """Edit existing furniture type with enhanced fields."""
    from models.furniture_type import get_all_furniture_types, get_furniture_type_by_id, update_furniture_type

    ftype = get_furniture_type_by_id(type_id)
    if not ftype:
        flash('Tipo de mobiliario no encontrado', 'error')
        return redirect(url_for('beach.beach_config.furniture_types'))

    if request.method == 'POST':
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
            # Enhanced fields
            'map_shape': request.form.get('map_shape', 'rounded_rect'),
            'custom_svg': request.form.get('custom_svg', '').strip() or None,
            'default_width': request.form.get('default_width', 60, type=float),
            'default_height': request.form.get('default_height', 40, type=float),
            'border_radius': request.form.get('border_radius', 5, type=int),
            'fill_color': request.form.get('fill_color', '#A0522D'),
            'stroke_color': request.form.get('stroke_color', '#654321'),
            'stroke_width': request.form.get('stroke_width', 2, type=int),
            # Note: status_colors are NOT set here - they come from reservation states config
            'default_rotation': 1 if request.form.get('default_rotation') else 0,
            'is_decorative': 1 if request.form.get('is_decorative') else 0,
            'number_prefix': request.form.get('number_prefix', '').strip() or None,
            'number_start': request.form.get('number_start', 1, type=int),
            'default_features': request.form.get('default_features', '').strip() or None,
            'allowed_zones': ','.join(request.form.getlist('allowed_zones')) or None,
        }

        if not data['display_name']:
            flash('El nombre es obligatorio', 'error')
            types = get_all_furniture_types(active_only=False)
            zones = get_all_zones()
            return render_template('beach/config/furniture_types.html',
                                   furniture_types=types, zones=zones,
                                   selected_type=ftype, mode='edit')

        try:
            updated = update_furniture_type(type_id, **data)
            if updated:
                flash('Tipo actualizado correctamente', 'success')
            else:
                flash('No se realizaron cambios', 'warning')
            return redirect(url_for('beach.beach_config.furniture_types'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'error')

    # GET: Show form with existing data
    types = get_all_furniture_types(active_only=False)
    zones = get_all_zones()
    return render_template('beach/config/furniture_types.html',
                           furniture_types=types, zones=zones,
                           selected_type=ftype, mode='edit')


@config_bp.route('/furniture-types/<int:type_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
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

    return redirect(url_for('beach.beach_config.furniture_types'))


@config_bp.route('/furniture-types/preview', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_types_preview():
    """Generate SVG preview for furniture type configuration (AJAX)."""
    from models.furniture_type import get_furniture_type_svg

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Generate single preview using fill_color (status colors come from reservation states config)
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


@config_bp.route('/furniture-types/<int:type_id>/next-number')
@login_required
@permission_required('beach.furniture.view')
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


@config_bp.route('/furniture-types/reorder', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
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


# ==================== Furniture Routes ====================

@config_bp.route('/furniture')
@login_required
@permission_required('beach.furniture.view')
def furniture():
    """List all furniture items."""
    zone_filter = request.args.get('zone', '')
    type_filter = request.args.get('type', '')
    active_filter = request.args.get('active', '1')

    # Get all furniture
    zone_id = int(zone_filter) if zone_filter else None
    active_only = active_filter == '1'
    all_furniture = get_all_furniture(zone_id=zone_id, active_only=active_only)

    # Apply type filter
    if type_filter:
        all_furniture = [f for f in all_furniture if f['furniture_type'] == type_filter]

    # Get zones and types for filters
    zones = get_all_zones()
    types = get_furniture_types()

    return render_template('beach/config/furniture.html',
                           furniture=all_furniture, zones=zones, types=types,
                           zone_filter=zone_filter, type_filter=type_filter,
                           active_filter=active_filter)


@config_bp.route('/furniture/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_create():
    """Create new furniture item(s) with optional duplication."""
    if request.method == 'POST':
        from models.furniture_type import get_furniture_type_by_code

        number = request.form.get('number', '').strip()
        zone_id = request.form.get('zone_id', type=int)
        furniture_type = request.form.get('furniture_type', '').strip()
        capacity = request.form.get('capacity', 2, type=int)
        position_x = request.form.get('position_x', 0, type=float)
        position_y = request.form.get('position_y', 0, type=float)
        rotation = request.form.get('rotation', 0, type=int)
        width = request.form.get('width', 60, type=float)
        height = request.form.get('height', 40, type=float)
        features = request.form.get('features', '').strip()

        # Duplication parameters
        copy_count = request.form.get('copy_count', 1, type=int)
        copy_layout = request.form.get('copy_layout', 'horizontal')
        copy_spacing = request.form.get('copy_spacing', 10, type=float)

        if not number or not zone_id or not furniture_type:
            flash('Número, zona y tipo son obligatorios', 'error')
            return redirect(url_for('beach.beach_config.furniture_create'))

        # Limit copy count
        copy_count = max(1, min(copy_count, 50))

        try:
            # Get furniture type info for prefix
            ftype = get_furniture_type_by_code(furniture_type)
            prefix = ftype.get('number_prefix', '') if ftype else ''

            created_count = 0
            for i in range(copy_count):
                # Calculate position for this copy
                if copy_layout == 'horizontal':
                    current_x = position_x + i * (width + copy_spacing)
                    current_y = position_y
                else:  # vertical
                    current_x = position_x
                    current_y = position_y + i * (height + copy_spacing)

                # Generate number for copies after the first
                if i == 0:
                    current_number = number
                else:
                    # Extract base number and increment
                    if prefix and number.startswith(prefix):
                        try:
                            base_num = int(number[len(prefix):])
                            current_number = f"{prefix}{base_num + i}"
                        except ValueError:
                            current_number = f"{number}_{i + 1}"
                    else:
                        current_number = f"{number}_{i + 1}"

                create_furniture(
                    number=current_number,
                    zone_id=zone_id,
                    furniture_type=furniture_type,
                    capacity=capacity,
                    position_x=current_x,
                    position_y=current_y,
                    rotation=rotation,
                    width=width,
                    height=height,
                    features=features if features else ''
                )
                created_count += 1

            if created_count == 1:
                flash('Mobiliario creado correctamente', 'success')
            else:
                flash(f'{created_count} elementos de mobiliario creados correctamente', 'success')
            return redirect(url_for('beach.beach_config.furniture'))

        except Exception as e:
            flash(f'Error al crear mobiliario: {str(e)}', 'error')

    # GET: Show form
    zones = get_all_zones()
    types = get_furniture_types()
    return render_template('beach/config/furniture_form.html',
                           furniture=None, zones=zones, types=types, mode='create')


@config_bp.route('/furniture/<int:furniture_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_edit(furniture_id):
    """Edit existing furniture item or duplicate it."""
    from models.furniture_type import get_furniture_type_by_code

    item = get_furniture_by_id(furniture_id)
    if not item:
        flash('Mobiliario no encontrado', 'error')
        return redirect(url_for('beach.beach_config.furniture'))

    if request.method == 'POST':
        number = request.form.get('number', '').strip()
        zone_id = request.form.get('zone_id', type=int)
        capacity = request.form.get('capacity', 2, type=int)
        position_x = request.form.get('position_x', 0, type=float)
        position_y = request.form.get('position_y', 0, type=float)
        rotation = request.form.get('rotation', 0, type=int)
        width = request.form.get('width', 60, type=float)
        height = request.form.get('height', 40, type=float)
        features = request.form.get('features', '').strip()
        active = 1 if request.form.get('active') == '1' else 0

        # Check if this is a duplicate action
        is_duplicate = request.form.get('duplicate') == '1'

        if not number or not zone_id:
            flash('Número y zona son obligatorios', 'error')
            return redirect(url_for('beach.beach_config.furniture_edit', furniture_id=furniture_id))

        try:
            if is_duplicate:
                # Duplication mode - create new copies
                from models.furniture import get_next_number_by_prefix

                copy_count = request.form.get('copy_count', 1, type=int)
                copy_layout = request.form.get('copy_layout', 'horizontal')
                copy_spacing = request.form.get('copy_spacing', 10, type=float)

                # Limit copy count
                copy_count = max(1, min(copy_count, 50))

                furniture_type = item['furniture_type']

                # Extract prefix from current number (e.g., "B1" -> prefix="B")
                import re
                match = re.match(r'^([A-Za-z]*)(\d+)$', number)
                if match:
                    prefix = match.group(1)
                else:
                    prefix = ''

                created_count = 0
                for i in range(copy_count):
                    # Calculate position for this copy (start from current position)
                    if copy_layout == 'horizontal':
                        current_x = position_x + (i + 1) * (width + copy_spacing)
                        current_y = position_y
                    else:  # vertical
                        current_x = position_x
                        current_y = position_y + (i + 1) * (height + copy_spacing)

                    # Get next sequential number based on prefix
                    current_number = get_next_number_by_prefix(prefix)

                    create_furniture(
                        number=current_number,
                        zone_id=zone_id,
                        furniture_type=furniture_type,
                        capacity=capacity,
                        position_x=current_x,
                        position_y=current_y,
                        rotation=rotation,
                        width=width,
                        height=height,
                        features=features if features else ''
                    )
                    created_count += 1

                flash(f'{created_count} copia(s) creada(s) correctamente', 'success')
            else:
                # Normal edit mode
                updated = update_furniture(
                    furniture_id,
                    number=number,
                    zone_id=zone_id,
                    capacity=capacity,
                    position_x=position_x,
                    position_y=position_y,
                    rotation=rotation,
                    width=width,
                    height=height,
                    features=features if features else '',
                    active=active
                )

                if updated:
                    flash('Mobiliario actualizado correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')

            return redirect(url_for('beach.beach_config.furniture'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    # GET: Show form
    zones = get_all_zones()
    types = get_furniture_types()
    return render_template('beach/config/furniture_form.html',
                           furniture=item, zones=zones, types=types, mode='edit')


@config_bp.route('/furniture/<int:furniture_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_delete(furniture_id):
    """Delete furniture item."""
    try:
        deleted = delete_furniture(furniture_id)
        if deleted:
            flash('Mobiliario eliminado correctamente', 'success')
        else:
            flash('Error al eliminar mobiliario', 'error')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.beach_config.furniture'))


# ==================== API Endpoints for Map Positioning ====================

@config_bp.route('/api/furniture/<int:furniture_id>/position', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
def furniture_update_position(furniture_id):
    """Update furniture position (AJAX endpoint for map drag-drop)."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    position_x = data.get('position_x')
    position_y = data.get('position_y')
    rotation = data.get('rotation')

    update_data = {}
    if position_x is not None:
        update_data['position_x'] = float(position_x)
    if position_y is not None:
        update_data['position_y'] = float(position_y)
    if rotation is not None:
        update_data['rotation'] = int(rotation)

    if not update_data:
        return jsonify({'error': 'No position data provided'}), 400

    try:
        updated = update_furniture(furniture_id, **update_data)
        if updated:
            return jsonify({'success': True, 'message': 'Posición actualizada'})
        else:
            return jsonify({'error': 'No se pudo actualizar'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Preferences Routes ====================

@config_bp.route('/preferences')
@login_required
@permission_required('beach.furniture.view')
def preferences():
    """List all customer preferences."""
    from models.preference import get_all_preferences
    all_preferences = get_all_preferences(active_only=False)
    return render_template('beach/config/preferences.html', preferences=all_preferences)


@config_bp.route('/preferences/create', methods=['GET', 'POST'])
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


@config_bp.route('/preferences/<int:preference_id>/edit', methods=['GET', 'POST'])
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


@config_bp.route('/preferences/<int:preference_id>/delete', methods=['POST'])
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


# ==================== Tags Routes ====================

@config_bp.route('/tags')
@login_required
@permission_required('beach.furniture.view')
def tags():
    """List all tags."""
    from models.tag import get_all_tags
    all_tags = get_all_tags(active_only=False)
    return render_template('beach/config/tags.html', tags=all_tags)


@config_bp.route('/tags/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
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
            return redirect(url_for('beach.beach_config.tags'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error al crear: {str(e)}', 'error')

    return render_template('beach/config/tag_form.html', tag=None, mode='create')


@config_bp.route('/tags/<int:tag_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.furniture.manage')
def tags_edit(tag_id):
    """Edit existing tag."""
    from models.tag import get_tag_by_id, update_tag

    tag = get_tag_by_id(tag_id)
    if not tag:
        flash('Etiqueta no encontrada', 'error')
        return redirect(url_for('beach.beach_config.tags'))

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
            return redirect(url_for('beach.beach_config.tags'))

        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'error')

    return render_template('beach/config/tag_form.html', tag=tag, mode='edit')


@config_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.furniture.manage')
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
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.beach_config.tags'))
