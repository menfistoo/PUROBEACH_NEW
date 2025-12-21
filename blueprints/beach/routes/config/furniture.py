"""
Furniture configuration routes.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import (get_all_furniture, get_furniture_by_id,
                              get_furniture_types, create_furniture,
                              update_furniture, delete_furniture)


def register_routes(bp):
    """Register furniture routes on the blueprint."""

    @bp.route('/furniture')
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

    @bp.route('/furniture/create', methods=['GET', 'POST'])
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

    @bp.route('/furniture/<int:furniture_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.furniture.manage')
    def furniture_edit(furniture_id):
        """Edit existing furniture item or duplicate it."""
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
                    import re

                    copy_count = request.form.get('copy_count', 1, type=int)
                    copy_layout = request.form.get('copy_layout', 'horizontal')
                    copy_spacing = request.form.get('copy_spacing', 10, type=float)

                    # Limit copy count
                    copy_count = max(1, min(copy_count, 50))

                    furniture_type = item['furniture_type']

                    # Extract prefix from current number (e.g., "B1" -> prefix="B")
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

    @bp.route('/furniture/<int:furniture_id>/delete', methods=['POST'])
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

    # API Endpoint for Map Positioning
    @bp.route('/api/furniture/<int:furniture_id>/position', methods=['POST'])
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
