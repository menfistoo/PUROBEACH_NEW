"""
Insights API endpoints.
Provides analytics data for dashboard and advanced views.
"""

from flask import jsonify
from flask_login import login_required
from models.insights import (
    get_occupancy_today,
    get_occupancy_by_zone,
    get_pending_checkins_count,
    get_occupancy_comparison
)


def register_routes(bp):
    """Register insights API routes on the blueprint."""

    @bp.route('/insights/today', methods=['GET'])
    @login_required
    def get_insights_today():
        """
        Get today's operational metrics for dashboard.

        Response JSON:
        {
            "success": true,
            "occupancy": {
                "occupied": 45,
                "total": 60,
                "rate": 75.0,
                "by_type": {...}
            },
            "comparison": {
                "today_rate": 75.0,
                "yesterday_rate": 70.0,
                "difference": 5.0,
                "trend": "up"
            },
            "pending_checkins": 7,
            "zones": [...]
        }
        """
        try:
            occupancy = get_occupancy_today()
            comparison = get_occupancy_comparison()
            pending = get_pending_checkins_count()
            zones = get_occupancy_by_zone()

            return jsonify({
                'success': True,
                'occupancy': occupancy,
                'comparison': comparison,
                'pending_checkins': pending,
                'zones': zones
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
