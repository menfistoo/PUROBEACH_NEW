"""
Beach blueprint initialization.
Registers all beach-related routes (map, customers, reservations, config, api, reports).

This module serves as the blueprint factory, assembling route modules into
the main beach blueprint. Individual route logic is in:
- routes/map.py - Map views
- routes/customers.py - Customer CRUD
- routes/reservations.py - Reservation CRUD
- routes/config.py - Infrastructure configuration
- routes/api.py - REST API endpoints
- routes/reports.py - Reporting views
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture

# Create main beach blueprint
beach_bp = Blueprint('beach', __name__, template_folder='../../templates/beach')

# =============================================================================
# REGISTER SUB-BLUEPRINTS
# =============================================================================

# Config routes (infrastructure management)
from blueprints.beach.routes.config import config_bp
beach_bp.register_blueprint(config_bp)

# API routes (all REST endpoints)
from blueprints.beach.routes.api import api_bp
beach_bp.register_blueprint(api_bp, url_prefix='/api')

# Reports routes
from blueprints.beach.routes.reports import reports_bp
beach_bp.register_blueprint(reports_bp)

# Admin routes (audit logs, system management)
from blueprints.beach.routes.admin import admin_bp
beach_bp.register_blueprint(admin_bp)


# =============================================================================
# MAP ROUTES
# =============================================================================

@beach_bp.route('/map')
@login_required
@permission_required('beach.map.view')
def map():
    """Display beach map."""
    zones = get_all_zones()
    furniture = get_all_furniture()
    return render_template('beach/map.html', zones=zones, furniture=furniture)


# =============================================================================
# CUSTOMER ROUTES (delegated to customers module)
# =============================================================================

from blueprints.beach.routes.customers import customers_bp

# Import customer route functions for registration
from blueprints.beach.routes.customers import (
    list as customers_list_view,
    create as customers_create_view,
    detail as customers_detail_view,
    edit as customers_edit_view,
    delete as customers_delete_view,
    merge as customers_merge_view
)


@beach_bp.route('/customers')
@login_required
@permission_required('beach.customers.view')
def customers():
    """Display customer list."""
    return customers_list_view()


@beach_bp.route('/customers/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.create')
def customers_create():
    """Create new customer."""
    return customers_create_view()


@beach_bp.route('/customers/<int:customer_id>')
@login_required
@permission_required('beach.customers.view')
def customers_detail(customer_id):
    """Display customer detail."""
    return customers_detail_view(customer_id)


@beach_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.edit')
def customers_edit(customer_id):
    """Edit customer."""
    return customers_edit_view(customer_id)


@beach_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.customers.edit')
def customers_delete(customer_id):
    """Delete customer."""
    return customers_delete_view(customer_id)


@beach_bp.route('/customers/<int:customer_id>/merge', methods=['GET', 'POST'])
@login_required
@permission_required('beach.customers.merge')
def customers_merge(customer_id):
    """Merge customer."""
    return customers_merge_view(customer_id)


@beach_bp.route('/customers/export')
@login_required
@permission_required('beach.reports.export')
def customers_export():
    """Export customers to Excel."""
    from blueprints.beach.routes.reports.exports import export_customers_handler
    return export_customers_handler()


# =============================================================================
# RESERVATION ROUTES (delegated to reservations module)
# =============================================================================

from blueprints.beach.routes.reservations import (
    list as reservations_list_view,
    create as reservations_create_view,
    detail as reservations_detail_view,
    edit as reservations_edit_view,
    delete as reservations_delete_view,
    cancel as reservations_cancel_view,
    export as reservations_export_view
)


@beach_bp.route('/reservations')
@login_required
@permission_required('beach.reservations.view')
def reservations():
    """Display reservation list."""
    return reservations_list_view()


@beach_bp.route('/reservations/create', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.create')
def reservations_create():
    """Create new reservation."""
    return reservations_create_view()


@beach_bp.route('/reservations/<int:reservation_id>')
@login_required
@permission_required('beach.reservations.view')
def reservations_detail(reservation_id):
    """Display reservation detail."""
    return reservations_detail_view(reservation_id)


@beach_bp.route('/reservations/<int:reservation_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('beach.reservations.edit')
def reservations_edit(reservation_id):
    """Edit reservation."""
    return reservations_edit_view(reservation_id)


@beach_bp.route('/reservations/<int:reservation_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.reservations.delete')
def reservations_delete(reservation_id):
    """Delete reservation."""
    return reservations_delete_view(reservation_id)


@beach_bp.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
@permission_required('beach.reservations.change_state')
def reservations_cancel(reservation_id):
    """Cancel reservation."""
    return reservations_cancel_view(reservation_id)


@beach_bp.route('/reservations/export')
@login_required
@permission_required('beach.reports.export')
def reservations_export():
    """Export reservations to Excel."""
    return reservations_export_view()


# =============================================================================
# INSIGHTS ROUTES
# =============================================================================

@beach_bp.route('/insights')
@login_required
@permission_required('beach.insights.view')
def insights_dashboard():
    """Display operational insights dashboard."""
    return render_template('beach/insights/dashboard.html')


@beach_bp.route('/insights/analytics')
@login_required
@permission_required('beach.insights.analytics')
def insights_analytics():
    """Display advanced analytics."""
    return render_template('beach/insights/analytics.html')


# =============================================================================
# REPORTS & ANALYTICS ROUTES (Menu items)
# =============================================================================

@beach_bp.route('/analytics')
@login_required
@permission_required('beach.analytics.view')
def analytics_dashboard():
    """Display analytics dashboard with button to advanced analytics."""
    return render_template('beach/insights/dashboard.html')


# =============================================================================
# TEMPLATE CONTEXT PROCESSORS
# =============================================================================

@beach_bp.app_context_processor
def inject_permission_helper():
    """Inject permission helper into templates."""
    from utils.permissions import has_permission

    def current_user_can(permission_code):
        if not current_user.is_authenticated:
            return False
        return has_permission(current_user, permission_code)

    return {'current_user_can': current_user_can}
