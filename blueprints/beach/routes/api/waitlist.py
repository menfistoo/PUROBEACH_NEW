"""
Waitlist API routes.
Endpoints for managing the beach waiting list.
"""

import logging
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

from utils.decorators import permission_required
from models.waitlist import (
    get_waitlist_by_date,
    get_waitlist_count,
    get_waitlist_entry,
    create_waitlist_entry,
    update_waitlist_status,
    convert_to_reservation,
    get_waitlist_history,
    expire_old_entries,
    WAITLIST_STATUSES
)

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register waitlist routes on the blueprint."""

    @bp.route('/waitlist', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def list_waitlist():
        """
        Get waitlist entries for a date.

        Query params:
            date: Date (YYYY-MM-DD), defaults to today
            include_all: If 'true', include non-waiting entries

        Returns:
            JSON list of entries
        """
        requested_date = request.args.get('date', date.today().isoformat())
        include_all = request.args.get('include_all', '').lower() == 'true'

        try:
            entries = get_waitlist_by_date(requested_date, include_all=include_all)
            return jsonify({
                'success': True,
                'entries': entries,
                'count': len([e for e in entries if e['status'] == 'waiting'])
            })
        except Exception as e:
            logger.error(f"Error listing waitlist: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener lista'}), 500

    @bp.route('/waitlist/count', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def waitlist_count():
        """
        Get count of waiting entries for badge.

        Query params:
            date: Date (YYYY-MM-DD), defaults to today

        Returns:
            JSON with count
        """
        requested_date = request.args.get('date', date.today().isoformat())

        try:
            count = get_waitlist_count(requested_date)
            return jsonify({'success': True, 'count': count})
        except Exception as e:
            logger.error(f"Error getting waitlist count: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener conteo'}), 500

    @bp.route('/waitlist/<int:entry_id>', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def get_entry(entry_id):
        """Get single waitlist entry."""
        entry = get_waitlist_entry(entry_id)
        if not entry:
            return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404

        return jsonify({'success': True, 'entry': entry})

    @bp.route('/waitlist', methods=['POST'])
    @login_required
    @permission_required('beach.waitlist.create')
    def create_entry():
        """
        Create new waitlist entry.

        Request body:
            customer_id: Customer ID (required)
            requested_date: Date (required)
            num_people: Number of people (required)
            preferred_zone_id: Zone ID (optional)
            preferred_furniture_type_id: Furniture type ID (optional)
            time_preference: morning/afternoon/all_day (optional)
            reservation_type: incluido/paquete/consumo_minimo (optional)
            package_id: Package ID if type is paquete (optional)
            notes: Notes (optional)

        Returns:
            JSON with entry ID
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        try:
            entry_id = create_waitlist_entry(data, created_by=current_user.id)
            return jsonify({
                'success': True,
                'entry_id': entry_id,
                'message': 'Agregado a lista de espera'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error creating waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al crear entrada'}), 500

    @bp.route('/waitlist/<int:entry_id>', methods=['PUT'])
    @login_required
    @permission_required('beach.waitlist.manage')
    def update_entry(entry_id):
        """
        Update waitlist entry status.

        Request body:
            status: New status

        Returns:
            JSON with success
        """
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400

        try:
            update_waitlist_status(entry_id, data['status'])
            return jsonify({
                'success': True,
                'message': 'Estado actualizado'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error updating waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al actualizar'}), 500

    @bp.route('/waitlist/<int:entry_id>/convert', methods=['POST'])
    @login_required
    @permission_required('beach.waitlist.manage')
    def convert_entry(entry_id):
        """
        Mark entry as converted after reservation created.

        Request body:
            reservation_id: Created reservation ID

        Returns:
            JSON with success
        """
        data = request.get_json()

        if not data or 'reservation_id' not in data:
            return jsonify({'success': False, 'error': 'ID de reserva requerido'}), 400

        try:
            convert_to_reservation(entry_id, data['reservation_id'])
            return jsonify({
                'success': True,
                'message': 'Entrada convertida a reserva'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error converting waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al convertir'}), 500

    @bp.route('/waitlist/history', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def waitlist_history():
        """
        Get waitlist history (non-waiting entries).

        Query params:
            date: Filter by date (optional)
            customer_id: Filter by customer (optional)

        Returns:
            JSON list of entries
        """
        requested_date = request.args.get('date')
        customer_id = request.args.get('customer_id', type=int)

        # Expire old entries before showing history
        expire_old_entries()

        try:
            entries = get_waitlist_history(
                requested_date=requested_date,
                customer_id=customer_id
            )
            return jsonify({'success': True, 'entries': entries})
        except Exception as e:
            logger.error(f"Error getting waitlist history: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener historial'}), 500

    @bp.route('/waitlist/statuses', methods=['GET'])
    @login_required
    def get_statuses():
        """Get available waitlist statuses."""
        return jsonify({
            'success': True,
            'statuses': WAITLIST_STATUSES
        })

    @bp.route('/zones', methods=['GET'])
    @login_required
    def get_zones():
        """Get active zones for dropdown."""
        from models.zone import get_all_zones
        try:
            zones = get_all_zones(active_only=True)
            return jsonify({
                'success': True,
                'zones': zones
            })
        except Exception as e:
            logger.error(f"Error getting zones: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener zonas'}), 500

    @bp.route('/furniture-types', methods=['GET'])
    @login_required
    def get_furniture_types():
        """Get active furniture types for dropdown."""
        from models.furniture_type import get_all_furniture_types
        try:
            types = get_all_furniture_types(active_only=True)
            return jsonify({
                'success': True,
                'furniture_types': types
            })
        except Exception as e:
            logger.error(f"Error getting furniture types: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener tipos'}), 500

    @bp.route('/packages', methods=['GET'])
    @login_required
    def get_packages():
        """Get active packages for dropdown."""
        from database import get_db
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, package_name, package_description, base_price,
                           per_person_price, min_people, max_people, is_active
                    FROM beach_packages
                    WHERE is_active = 1
                    ORDER BY package_name
                ''')
                rows = cursor.fetchall()
                packages = [dict(row) for row in rows]
            return jsonify({
                'success': True,
                'packages': packages
            })
        except Exception as e:
            logger.error(f"Error getting packages: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener paquetes'}), 500
