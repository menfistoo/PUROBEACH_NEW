"""
Customer management routes (Phase 1 placeholder, full implementation in Phase 5).
Handles customer CRUD operations, preferences, and deduplication.
"""

from flask import render_template, Blueprint
from flask_login import login_required

from utils.decorators import permission_required

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/customers')
@login_required
@permission_required('beach.customers.view')
def customers_list():
    """
    Display customer list.
    Phase 1: Placeholder page.
    Phase 5: Full customer management with search, filters, and CRUD operations.
    """
    return render_template('beach/customers.html')
