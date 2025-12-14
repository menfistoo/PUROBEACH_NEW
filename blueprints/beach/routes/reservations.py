"""
Reservation management routes (Phase 1 placeholder, full implementation in Phase 6).
Handles reservation CRUD operations, multi-day bookings, and state management.
"""

from flask import render_template, Blueprint
from flask_login import login_required

from utils.decorators import permission_required

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.route('/reservations')
@login_required
@permission_required('beach.reservations.view')
def reservations_list():
    """
    Display reservation list.
    Phase 1: Placeholder page.
    Phase 6: Full reservation management with calendar view and multi-day support.
    """
    return render_template('beach/reservations.html')
