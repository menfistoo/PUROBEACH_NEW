"""Beach reports routes."""
from flask import Blueprint, redirect, url_for
from flask_login import login_required

reports_bp = Blueprint('beach_reports', __name__, url_prefix='/reports')

from blueprints.beach.routes.reports import payment_reconciliation
payment_reconciliation.register_routes(reports_bp)


@reports_bp.route('/')
@login_required
def reports_index():
    """Redirect to payment reconciliation (only report available)."""
    return redirect(url_for('beach.beach_reports.payment_reconciliation_view'))
