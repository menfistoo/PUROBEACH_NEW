"""
Insights analytics module.
Re-exports all analytics functions for backward compatibility.

Submodules:
    - occupancy: Dashboard and occupancy range analytics
    - revenue: Revenue statistics and breakdown
    - customers: Customer stats, segmentation, preferences
    - patterns: Booking patterns and cancellation analytics
"""

# Occupancy analytics
from models.insights.occupancy import (
    get_occupancy_today,
    get_occupancy_by_zone,
    get_pending_checkins_count,
    get_occupancy_comparison,
    get_occupancy_range,
    get_occupancy_stats,
)

# Revenue analytics
from models.insights.revenue import (
    get_revenue_stats,
    get_revenue_by_type,
    get_top_packages,
)

# Customer analytics
from models.insights.customers import (
    get_customer_stats,
    get_customer_segmentation,
    get_top_customers,
    get_popular_preferences,
    get_popular_tags,
)

# Booking patterns
from models.insights.patterns import (
    get_pattern_stats,
    get_reservations_by_day_of_week,
    get_lead_time_distribution,
    get_cancellation_breakdown,
)

__all__ = [
    # Occupancy
    'get_occupancy_today',
    'get_occupancy_by_zone',
    'get_pending_checkins_count',
    'get_occupancy_comparison',
    'get_occupancy_range',
    'get_occupancy_stats',
    # Revenue
    'get_revenue_stats',
    'get_revenue_by_type',
    'get_top_packages',
    # Customers
    'get_customer_stats',
    'get_customer_segmentation',
    'get_top_customers',
    'get_popular_preferences',
    'get_popular_tags',
    # Patterns
    'get_pattern_stats',
    'get_reservations_by_day_of_week',
    'get_lead_time_distribution',
    'get_cancellation_breakdown',
]
