"""
API routes for JSON endpoints.
Provides REST API access to beach club data.
"""

from flask import jsonify, request, Blueprint
from flask_login import login_required

from models.zone import get_all_zones
from models.furniture import get_all_furniture

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    """
    Health check endpoint (no authentication required).

    Returns:
        JSON with status and version
    """
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'app': 'PuroBeach Beach Club Management System'
    })


@api_bp.route('/zones')
@login_required
def api_zones():
    """
    Get all beach zones as JSON.

    Returns:
        JSON list of zones
    """
    zones = get_all_zones()

    return jsonify({
        'success': True,
        'zones': zones
    })


@api_bp.route('/furniture')
@login_required
def api_furniture():
    """
    Get beach furniture as JSON.

    Query params:
        zone_id: Filter by zone ID (optional)
        active: Filter by active status (optional, default: true)

    Returns:
        JSON list of furniture
    """
    zone_id = request.args.get('zone_id', type=int)
    active_only = request.args.get('active', 'true').lower() == 'true'

    furniture = get_all_furniture(zone_id=zone_id, active_only=active_only)

    return jsonify({
        'success': True,
        'furniture': furniture,
        'count': len(furniture)
    })


@api_bp.route('/furniture/<int:furniture_id>')
@login_required
def api_furniture_detail(furniture_id):
    """
    Get single furniture item details.

    Args:
        furniture_id: Furniture ID

    Returns:
        JSON furniture details
    """
    from models.furniture import get_furniture_by_id

    furniture = get_furniture_by_id(furniture_id)

    if not furniture:
        return jsonify({
            'success': False,
            'error': 'Mobiliario no encontrado'
        }), 404

    return jsonify({
        'success': True,
        'furniture': furniture
    })
