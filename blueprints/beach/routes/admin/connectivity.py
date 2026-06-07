"""
Connectivity audit page.
Shows client-reported network drops (WiFi roaming gaps) so staff connection
issues can be reviewed: when, who, which device, how long.
Admin-only ('admin.audit.view').
"""

from flask import render_template, request
from flask_login import login_required

from utils.decorators import permission_required


def register_routes(bp):
    """Register connectivity audit routes on the blueprint."""

    @bp.route('/connectivity')
    @login_required
    @permission_required('admin.connectivity.view')
    def connectivity():
        """Connectivity drop audit page (summary + recent events)."""
        from models.connectivity_log import (
            get_recent_connectivity_events,
            get_connectivity_summary,
        )

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 100, type=int), 200)
        offset = (page - 1) * per_page

        events = get_recent_connectivity_events(limit=per_page, offset=offset)
        summary = get_connectivity_summary(days=14)

        return render_template(
            'beach/admin/connectivity.html',
            events=events,
            summary=summary,
            page=page,
            per_page=per_page,
        )
