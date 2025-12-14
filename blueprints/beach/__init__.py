"""
Beach blueprint initialization.
Registers all beach-related routes (map, customers, reservations, config).
"""

from flask import Blueprint, render_template
from flask_login import login_required
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture

# Create main beach blueprint
beach_bp = Blueprint('beach', __name__, template_folder='../../templates/beach')

# Register config sub-blueprint
from blueprints.beach.routes.config import config_bp
beach_bp.register_blueprint(config_bp)


@beach_bp.route('/map')
@login_required
@permission_required('beach.map.view')
def map():
    """Display beach map."""
    zones = get_all_zones()
    furniture = get_all_furniture()
    return render_template('beach/map.html', zones=zones, furniture=furniture)


@beach_bp.route('/customers')
@login_required
@permission_required('beach.customers.view')
def customers():
    """Display customer list."""
    return render_template('beach/customers.html')


@beach_bp.route('/reservations')
@login_required
@permission_required('beach.reservations.view')
def reservations():
    """Display reservation list."""
    return render_template('beach/reservations.html')
