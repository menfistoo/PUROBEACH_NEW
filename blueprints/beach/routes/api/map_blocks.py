"""
Map furniture blocking API routes.
Endpoints for blocking/unblocking furniture (maintenance, VIP hold, etc.).
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

from utils.decorators import permission_required
from models.furniture import get_furniture_by_id
from models.furniture_block import (
    create_furniture_block, get_blocks_for_date, get_block_by_id,
    delete_block, is_furniture_blocked, BLOCK_TYPES
)


def register_routes(bp):
    """Register map blocking routes on the blueprint."""

    @bp.route('/map/furniture/<int:furniture_id>/block', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.block')
    def block_furniture(furniture_id):
        """
        Block furniture for a date range.

        Request body:
            start_date: Block start date YYYY-MM-DD
            end_date: Block end date YYYY-MM-DD
            block_type: Type (maintenance, vip_hold, event, other)
            reason: Reason for blocking
            notes: Additional notes

        Returns:
            JSON with block ID
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        start_date = data.get('start_date')
        end_date = data.get('end_date', start_date)
        block_type = data.get('block_type', 'other')
        reason = data.get('reason', '')
        notes = data.get('notes', '')

        if not start_date:
            return jsonify({'success': False, 'error': 'Fecha de inicio requerida'}), 400

        # Check furniture exists
        furniture = get_furniture_by_id(furniture_id)
        if not furniture:
            return jsonify({'success': False, 'error': 'Mobiliario no encontrado'}), 404

        try:
            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date=start_date,
                end_date=end_date,
                block_type=block_type,
                reason=reason,
                notes=notes,
                created_by=current_user.username if current_user else 'system'
            )

            return jsonify({
                'success': True,
                'block_id': block_id,
                'message': f'Mobiliario {furniture["number"]} bloqueado'
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error al bloquear mobiliario'}), 500

    @bp.route('/map/furniture/<int:furniture_id>/block', methods=['DELETE'])
    @login_required
    @permission_required('beach.furniture.block')
    def unblock_furniture(furniture_id):
        """
        Remove a block from furniture.

        Query params:
            date: Date to unblock (finds block covering this date)
            block_id: Specific block ID to remove

        Returns:
            JSON with success status
        """
        date_str = request.args.get('date')
        block_id = request.args.get('block_id', type=int)

        if block_id:
            # Delete specific block
            block = get_block_by_id(block_id)
            if not block:
                return jsonify({'success': False, 'error': 'Bloqueo no encontrado'}), 404

            if block['furniture_id'] != furniture_id:
                return jsonify({'success': False, 'error': 'Bloqueo no corresponde al mobiliario'}), 400

            delete_block(block_id)
            return jsonify({'success': True, 'message': 'Bloqueo eliminado'})

        elif date_str:
            # Find and delete block for this date
            block = is_furniture_blocked(furniture_id, date_str)
            if not block:
                return jsonify({'success': False, 'error': 'No hay bloqueo para esta fecha'}), 404

            delete_block(block['id'])
            return jsonify({'success': True, 'message': 'Bloqueo eliminado'})

        else:
            return jsonify({'success': False, 'error': 'Se requiere date o block_id'}), 400

    @bp.route('/map/blocks')
    @login_required
    @permission_required('beach.map.view')
    def list_blocks():
        """
        List all blocks for a date.

        Query params:
            date: Date to check YYYY-MM-DD (default: today)
            zone_id: Filter by zone (optional)

        Returns:
            JSON with blocks list
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        zone_id = request.args.get('zone_id', type=int)

        blocks = get_blocks_for_date(date_str, zone_id)

        return jsonify({
            'success': True,
            'date': date_str,
            'blocks': blocks,
            'block_types': BLOCK_TYPES
        })
