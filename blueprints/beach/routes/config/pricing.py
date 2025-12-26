"""
Pricing configuration routes.
Unified interface for packages and minimum consumption policies.
"""

from flask import render_template, redirect, url_for, request
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register pricing routes on the blueprint."""

    @bp.route('/pricing')
    @login_required
    @permission_required('beach.config.pricing.view')
    def pricing():
        """Unified pricing configuration page with tabs."""
        from models.package import get_all_packages
        from models.pricing import get_all_minimum_consumption_policies

        # Get active tab from query parameter
        active_tab = request.args.get('tab', 'packages')

        # Get show inactive flags
        show_inactive_packages = request.args.get('show_inactive_packages', '0') == '1'
        show_inactive_policies = request.args.get('show_inactive_policies', '0') == '1'

        # Load data for both tabs
        packages = get_all_packages(active_only=not show_inactive_packages)
        policies = get_all_minimum_consumption_policies(active_only=not show_inactive_policies)

        return render_template('beach/config/pricing.html',
                             active_tab=active_tab,
                             packages=packages,
                             policies=policies,
                             show_inactive_packages=show_inactive_packages,
                             show_inactive_policies=show_inactive_policies)
