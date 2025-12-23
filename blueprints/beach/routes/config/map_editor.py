"""
Map Editor configuration routes.
Visual editor for designing beach map layout.
"""

from flask import render_template, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.zone import get_all_zones, get_zone_by_id, get_zone_with_furniture, update_zone
from models.furniture import (
    create_furniture, update_furniture, delete_furniture,
    update_furniture_position, get_furniture_by_id
)
from models.furniture_type import get_all_furniture_types


def register_routes(bp):
    """Register map editor routes on the blueprint."""

    @bp.route('/map-editor')
    @login_required
    @permission_required('beach.map_editor.view')
    def map_editor():
        """Map editor - redirect to unified furniture manager."""
        return redirect(url_for('beach.beach_config.furniture_manager', tab='map-editor'))

    @bp.route('/map-editor/zone/<int:zone_id>')
    @login_required
    @permission_required('beach.map_editor.view')
    def map_editor_zone_data(zone_id):
        """Get zone data with furniture for editor canvas."""
        zone = get_zone_with_furniture(zone_id)
        if not zone:
            return jsonify({'success': False, 'error': 'Zona no encontrada'}), 404

        furniture_types = get_all_furniture_types(active_only=True)
        types_dict = {ft['type_code']: ft for ft in furniture_types}

        return jsonify({
            'success': True,
            'zone': zone,
            'furniture_types': types_dict
        })

    @bp.route('/map-editor/zone/<int:zone_id>/settings', methods=['POST'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_zone_settings(zone_id):
        """Update zone canvas settings."""
        try:
            zone = get_zone_by_id(zone_id)
            if not zone:
                return jsonify({'success': False, 'error': 'Zona no encontrada'}), 404

            data = request.get_json(silent=True)
            if not data:
                return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400

            updates = {}

            if 'canvas_width' in data:
                updates['canvas_width'] = float(data['canvas_width'])
            if 'canvas_height' in data:
                updates['canvas_height'] = float(data['canvas_height'])
            if 'background_color' in data:
                updates['background_color'] = data['background_color']

            if updates:
                update_zone(zone_id, **updates)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map-editor/furniture', methods=['POST'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_create_furniture():
        """Create new furniture item on map."""
        data = request.get_json()

        required_fields = ['zone_id', 'furniture_type', 'number']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }), 400

        try:
            furniture_id = create_furniture(
                number=data['number'],
                zone_id=int(data['zone_id']),
                furniture_type=data['furniture_type'],
                capacity=int(data.get('capacity', 2)),
                position_x=float(data.get('position_x', 50)),
                position_y=float(data.get('position_y', 50)),
                rotation=int(data.get('rotation', 0)),
                width=float(data.get('width', 60)),
                height=float(data.get('height', 40)),
                features=data.get('features')
            )

            return jsonify({
                'success': True,
                'furniture_id': furniture_id
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map-editor/furniture/<int:furniture_id>/position', methods=['PUT'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_update_position(furniture_id):
        """Update furniture position on map."""
        data = request.get_json()

        x = data.get('x')
        y = data.get('y')
        rotation = data.get('rotation')

        if x is None or y is None:
            return jsonify({
                'success': False,
                'error': 'Posicion X e Y son requeridas'
            }), 400

        try:
            update_furniture_position(furniture_id, float(x), float(y),
                                      int(rotation) if rotation is not None else None)
            return jsonify({
                'success': True,
                'furniture_id': furniture_id
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map-editor/furniture/<int:furniture_id>', methods=['PUT'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_update_furniture(furniture_id):
        """Update furniture properties."""
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        data = request.get_json()
        updates = {}

        # Allowed fields for update
        allowed = ['number', 'capacity', 'rotation', 'width', 'height', 'features', 'fill_color']
        for field in allowed:
            if field in data:
                updates[field] = data[field]

        if updates:
            update_furniture(furniture_id, **updates)

        return jsonify({'success': True})

    @bp.route('/map-editor/furniture/<int:furniture_id>', methods=['DELETE'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_delete_furniture(furniture_id):
        """Delete furniture from map."""
        try:
            deleted = delete_furniture(furniture_id)
            if deleted:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'No se pudo eliminar'}), 400
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map-editor/furniture/next-number/<int:zone_id>/<furniture_type>')
    @login_required
    @permission_required('beach.map_editor.view')
    def map_editor_next_number(zone_id, furniture_type):
        """Get next available number for furniture type in zone."""
        from models.furniture_type import get_furniture_type_by_code, get_next_number_for_type

        ft = get_furniture_type_by_code(furniture_type)
        if not ft:
            return jsonify({'success': False, 'error': 'Tipo no encontrado'}), 404

        try:
            next_num = get_next_number_for_type(ft['id'], zone_id)
            return jsonify({
                'success': True,
                'next_number': next_num
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/map-editor/features')
    @login_required
    @permission_required('beach.map_editor.view')
    def map_editor_get_features():
        """Get available furniture features from preferences."""
        from models.preference import get_all_preferences

        preferences = get_all_preferences(active_only=True)
        # Only return preferences that map to furniture features
        features = [
            {
                'code': p['maps_to_feature'],
                'name': p['name'],
                'icon': p['icon']
            }
            for p in preferences if p.get('maps_to_feature')
        ]

        return jsonify({
            'success': True,
            'features': features
        })

    @bp.route('/map-editor/furniture/<int:furniture_id>/duplicate', methods=['POST'])
    @login_required
    @permission_required('beach.map_editor.edit')
    def map_editor_duplicate_furniture(furniture_id):
        """Duplicate furniture item horizontally or vertically."""
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        data = request.get_json()
        direction = data.get('direction', 'horizontal')  # 'horizontal' or 'vertical'
        spacing = int(data.get('spacing', 10))  # Gap between items
        count = min(int(data.get('count', 1)), 50)  # Max 50 copies

        # Get zone canvas dimensions for bounds checking
        zone = get_zone_by_id(furniture['zone_id'])
        if not zone:
            return jsonify({'success': False, 'error': 'Zona no encontrada'}), 404

        canvas_width = zone.get('canvas_width', 2000)
        canvas_height = zone.get('canvas_height', 1000)

        try:
            from models.furniture_type import get_furniture_type_by_code, get_next_number_for_type

            ft = get_furniture_type_by_code(furniture['furniture_type'])
            created = []

            # Starting position
            base_x = furniture['position_x']
            base_y = furniture['position_y']

            for i in range(count):
                # Calculate position for this copy
                if direction == 'horizontal':
                    new_x = base_x + (furniture['width'] + spacing) * (i + 1)
                    new_y = base_y
                else:  # vertical
                    new_x = base_x
                    new_y = base_y + (furniture['height'] + spacing) * (i + 1)

                # Check bounds - stop if element would be outside canvas
                if new_x + furniture['width'] > canvas_width or new_y + furniture['height'] > canvas_height:
                    if len(created) == 0:
                        return jsonify({
                            'success': False,
                            'error': 'No hay espacio en el canvas para duplicar'
                        }), 400
                    break  # Stop creating more, but keep what we have

                next_num = get_next_number_for_type(ft['id'], furniture['zone_id']) if ft else f"{furniture['number']}_copy{i+1}"

                new_id = create_furniture(
                    number=next_num,
                    zone_id=furniture['zone_id'],
                    furniture_type=furniture['furniture_type'],
                    capacity=furniture['capacity'],
                    position_x=new_x,
                    position_y=new_y,
                    rotation=furniture['rotation'],
                    width=furniture['width'],
                    height=furniture['height'],
                    features=furniture.get('features')
                )

                created.append({
                    'id': new_id,
                    'number': next_num,
                    'position_x': new_x,
                    'position_y': new_y
                })

            return jsonify({
                'success': True,
                'count': len(created),
                'created': created
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
