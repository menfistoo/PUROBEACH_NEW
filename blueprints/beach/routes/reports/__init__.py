"""Beach reports routes."""
from flask import Blueprint

reports_bp = Blueprint('beach_reports', __name__, url_prefix='/reports')

from blueprints.beach.routes.reports import payment_reconciliation
payment_reconciliation.register_routes(reports_bp)
