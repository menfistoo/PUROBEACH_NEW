"""
Beach map route (Phase 1 placeholder, full implementation in Phase 7).
Displays interactive beach map with furniture and real-time availability.
"""

from flask import render_template, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture

map_bp = Blueprint('map', __name__)


@map_bp.route('/map')
@login_required
@permission_required('beach.map.view')
def map_view():
    """
    Display beach map.
    Phase 1: Static placeholder with basic data.
    Phase 7: Interactive SVG map with drag-drop and real-time availability.
    """
    # Get zones and furniture for basic display
    zones = get_all_zones()
    furniture = get_all_furniture()

    return render_template('beach/map.html', zones=zones, furniture=furniture)
