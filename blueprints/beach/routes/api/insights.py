"""
Insights API endpoints.
Provides analytics data for dashboard and advanced views.
"""

from datetime import timedelta
from utils.datetime_helpers import get_today
from flask import current_app, request
from flask_login import login_required
from utils.decorators import permission_required
from utils.api_response import api_success, api_error
from models.insights import (
    get_occupancy_today,
    get_occupancy_by_zone,
    get_pending_checkins_count,
    get_occupancy_comparison,
    get_occupancy_range,
    get_occupancy_stats,
    get_revenue_stats,
    get_revenue_by_type,
    get_top_packages,
    get_customer_stats,
    get_customer_segmentation,
    get_top_customers,
    get_popular_preferences,
    get_popular_tags,
    get_pattern_stats,
    get_reservations_by_day_of_week,
    get_lead_time_distribution,
    get_cancellation_breakdown
)


def register_routes(bp):
    """Register insights API routes on the blueprint."""

    @bp.route('/insights/today', methods=['GET'])
    @login_required
    @permission_required('beach.insights.view')
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

            return api_success(
                occupancy=occupancy,
                comparison=comparison,
                pending_checkins=pending,
                zones=zones
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/insights/occupancy', methods=['GET'])
    @login_required
    @permission_required('beach.insights.view')
    def get_insights_occupancy():
        """
        Get occupancy analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {
                "avg_occupancy": 75.0,
                "total_reservations": 120,
                "noshow_rate": 5.0
            },
            "daily": [...],
            "by_zone": [...]
        }
        """
        try:
            # Get date range from params, default to last 30 days
            end_date = request.args.get('end_date', get_today().isoformat())
            start_date = request.args.get(
                'start_date',
                (get_today() - timedelta(days=29)).isoformat()
            )

            stats = get_occupancy_stats(start_date, end_date)
            daily = get_occupancy_range(start_date, end_date)
            by_zone = get_occupancy_by_zone(end_date)

            return api_success(stats=stats, daily=daily, by_zone=by_zone)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/insights/revenue', methods=['GET'])
    @login_required
    @permission_required('beach.insights.view')
    def get_insights_revenue():
        """
        Get revenue analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {
                "total_revenue": 5000.00,
                "paid_reservations": 50,
                "avg_per_reservation": 100.00
            },
            "breakdown": {
                "by_reservation_type": [...],
                "by_customer_type": [...]
            },
            "top_packages": [...]
        }
        """
        try:
            # Get date range from params, default to last 30 days
            end_date = request.args.get('end_date', get_today().isoformat())
            start_date = request.args.get(
                'start_date',
                (get_today() - timedelta(days=29)).isoformat()
            )

            stats = get_revenue_stats(start_date, end_date)
            breakdown = get_revenue_by_type(start_date, end_date)
            top_packages = get_top_packages(start_date, end_date)

            return api_success(
                stats=stats,
                breakdown=breakdown,
                top_packages=top_packages
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/insights/customers', methods=['GET'])
    @login_required
    @permission_required('beach.insights.view')
    def get_insights_customers():
        """
        Get customer analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {
                "unique_customers": 50,
                "avg_group_size": 2.5,
                "returning_rate": 30.0
            },
            "segmentation": {
                "by_status": [...],
                "by_type": [...]
            },
            "top_customers": [...],
            "preferences": [...],
            "tags": [...]
        }
        """
        try:
            # Get date range from params, default to last 30 days
            end_date = request.args.get('end_date', get_today().isoformat())
            start_date = request.args.get(
                'start_date',
                (get_today() - timedelta(days=29)).isoformat()
            )

            stats = get_customer_stats(start_date, end_date)
            segmentation = get_customer_segmentation(start_date, end_date)
            top_customers = get_top_customers(start_date, end_date)
            preferences = get_popular_preferences(start_date, end_date)
            tags = get_popular_tags(start_date, end_date)

            return api_success(
                stats=stats,
                segmentation=segmentation,
                top_customers=top_customers,
                preferences=preferences,
                tags=tags
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/insights/patterns', methods=['GET'])
    @login_required
    @permission_required('beach.insights.view')
    def get_insights_patterns():
        """
        Get booking patterns analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {
                "avg_lead_time": 5.0,
                "cancellation_rate": 10.0,
                "noshow_rate": 5.0
            },
            "by_day_of_week": [...],
            "lead_time": [...],
            "cancellation": {
                "by_customer_type": [...],
                "by_lead_time": [...]
            }
        }
        """
        try:
            # Get date range from params, default to last 30 days
            end_date = request.args.get('end_date', get_today().isoformat())
            start_date = request.args.get(
                'start_date',
                (get_today() - timedelta(days=29)).isoformat()
            )

            stats = get_pattern_stats(start_date, end_date)
            by_day_of_week = get_reservations_by_day_of_week(start_date, end_date)
            lead_time = get_lead_time_distribution(start_date, end_date)
            cancellation = get_cancellation_breakdown(start_date, end_date)

            return api_success(
                stats=stats,
                by_day_of_week=by_day_of_week,
                lead_time=lead_time,
                cancellation=cancellation
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)
