"""
Map furniture blocking API routes.
Endpoints for blocking/unblocking furniture (maintenance, VIP hold, etc.).
"""

import logging
from flask import current_app, request, jsonify
from flask_login import login_required, current_user
from datetime import date

logger = logging.getLogger(__name__)

from utils.decorators import permission_required
from models.furniture import get_furniture_by_id
from models.furniture_block import (
    create_furniture_block, get_blocks_for_date, get_block_by_id,
    delete_block, is_furniture_blocked, partial_unblock, BLOCK_TYPES
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
        end_date = data.get('end_date') or start_date  # Handle empty/null end_date
        block_type = data.get('block_type', 'other')
        reason = data.get('reason') or ''
        notes = data.get('notes') or ''

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
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
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

    @bp.route('/map/furniture/<int:furniture_id>/unblock-partial', methods=['POST'])
    @login_required
    @permission_required('beach.furniture.block')
    def partial_unblock_furniture(furniture_id):
        """
        Partially unblock furniture for a specific date range.

        This endpoint handles splitting blocks when unblocking a range in the middle.

        Request body:
            block_id: Block ID to modify
            unblock_start: Start date to unblock YYYY-MM-DD
            unblock_end: End date to unblock YYYY-MM-DD

        Returns:
            JSON with success status and action taken
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        block_id = data.get('block_id')
        unblock_start = data.get('unblock_start')
        unblock_end = data.get('unblock_end')

        if not block_id:
            return jsonify({'success': False, 'error': 'block_id requerido'}), 400

        if not unblock_start or not unblock_end:
            return jsonify({'success': False, 'error': 'Fechas de desbloqueo requeridas'}), 400

        # Verify block belongs to this furniture
        block = get_block_by_id(block_id)
        if not block:
            return jsonify({'success': False, 'error': 'Bloqueo no encontrado'}), 404

        if block['furniture_id'] != furniture_id:
            return jsonify({'success': False, 'error': 'Bloqueo no corresponde al mobiliario'}), 400

        try:
            result = partial_unblock(block_id, unblock_start, unblock_end)

            action_messages = {
                'deleted': 'Bloqueo eliminado completamente',
                'shrunk_start': 'Bloqueo ajustado (inicio movido)',
                'shrunk_end': 'Bloqueo ajustado (fin movido)',
                'split': 'Bloqueo dividido en dos'
            }

            return jsonify({
                'success': True,
                'action': result['action'],
                'message': action_messages.get(result['action'], 'Desbloqueo parcial completado'),
                'block_ids': result.get('block_ids', [])
            })

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
        except Exception as e:
            logger.error(f"Partial unblock error for furniture {furniture_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'Error al procesar desbloqueo parcial'}), 500

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
