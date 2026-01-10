"""
Tests for insights model functions.
"""

import pytest
from datetime import date, timedelta


class TestGetOccupancyToday:
    """Tests for get_occupancy_today function."""

    def test_returns_zero_when_no_reservations(self, app):
        """Returns 0% occupancy when no reservations exist."""
        from models.insights import get_occupancy_today

        with app.app_context():
            result = get_occupancy_today()

            assert 'occupied' in result
            assert 'total' in result
            assert 'rate' in result
            assert result['occupied'] == 0
            assert result['rate'] == 0.0

    def test_returns_correct_rate_with_reservations(self, app):
        """Returns correct occupancy rate with active reservations."""
        from models.insights import get_occupancy_today
        from models.furniture import get_all_furniture

        with app.app_context():
            # Get total furniture count for reference
            furniture = get_all_furniture()
            total = len([f for f in furniture if f['active']])

            result = get_occupancy_today()

            assert result['total'] == total
            assert 0 <= result['rate'] <= 100

    def test_returns_by_type_breakdown(self, app):
        """Returns breakdown by furniture type."""
        from models.insights import get_occupancy_today

        with app.app_context():
            result = get_occupancy_today()

            assert 'by_type' in result
            assert isinstance(result['by_type'], dict)

            # If there are furniture types, check structure
            for type_code, type_data in result['by_type'].items():
                assert 'name' in type_data
                assert 'total' in type_data
                assert 'occupied' in type_data
                assert 'free' in type_data
                assert type_data['free'] == type_data['total'] - type_data['occupied']

    def test_total_matches_furniture_count(self, app):
        """Total should match active furniture count."""
        from models.insights import get_occupancy_today
        from database import get_db

        with app.app_context():
            # Get furniture count directly from database
            with get_db() as conn:
                cursor = conn.execute(
                    'SELECT COUNT(*) FROM beach_furniture WHERE active = 1'
                )
                db_count = cursor.fetchone()[0]

            result = get_occupancy_today()

            assert result['total'] == db_count


class TestGetOccupancyByZone:
    """Tests for get_occupancy_by_zone function."""

    def test_returns_all_active_zones(self, app):
        """Returns occupancy data for all active zones."""
        from models.insights import get_occupancy_by_zone
        from models.zone import get_all_zones

        with app.app_context():
            zones = get_all_zones(active_only=True)
            result = get_occupancy_by_zone()

            assert isinstance(result, list)
            # Should have same number of zones
            assert len(result) == len(zones)

    def test_zone_has_required_fields(self, app):
        """Each zone entry has required fields."""
        from models.insights import get_occupancy_by_zone

        with app.app_context():
            result = get_occupancy_by_zone()

            if result:  # Only test if zones exist
                zone = result[0]
                assert 'zone_id' in zone
                assert 'zone_name' in zone
                assert 'occupied' in zone
                assert 'total' in zone
                assert 'rate' in zone

    def test_rate_calculation_is_correct(self, app):
        """Rate should be calculated correctly as percentage."""
        from models.insights import get_occupancy_by_zone

        with app.app_context():
            result = get_occupancy_by_zone()

            for zone in result:
                if zone['total'] > 0:
                    expected_rate = round((zone['occupied'] / zone['total']) * 100, 1)
                    assert zone['rate'] == expected_rate
                else:
                    assert zone['rate'] == 0.0

    def test_accepts_target_date_parameter(self, app):
        """Accepts optional target_date parameter."""
        from models.insights import get_occupancy_by_zone
        from datetime import date, timedelta

        with app.app_context():
            # Should work with today
            result_today = get_occupancy_by_zone()
            assert isinstance(result_today, list)

            # Should work with specific date
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            result_tomorrow = get_occupancy_by_zone(target_date=tomorrow)
            assert isinstance(result_tomorrow, list)


class TestGetPendingCheckins:
    """Tests for get_pending_checkins_count function."""

    def test_returns_integer(self, app):
        """Returns an integer count."""
        from models.insights import get_pending_checkins_count

        with app.app_context():
            result = get_pending_checkins_count()
            assert isinstance(result, int)
            assert result >= 0


class TestGetOccupancyComparison:
    """Tests for get_occupancy_comparison function."""

    def test_returns_comparison_data(self, app):
        """Returns today vs yesterday comparison."""
        from models.insights import get_occupancy_comparison

        with app.app_context():
            result = get_occupancy_comparison()

            assert 'today_rate' in result
            assert 'yesterday_rate' in result
            assert 'difference' in result
            assert 'trend' in result
            assert result['trend'] in ('up', 'down', 'same')


class TestGetOccupancyRange:
    """Tests for get_occupancy_range function."""

    def test_returns_list_for_date_range(self, app):
        """Returns occupancy data for each day in range."""
        from models.insights import get_occupancy_range

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            result = get_occupancy_range(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)
            assert len(result) == 7  # 7 days

    def test_each_day_has_required_fields(self, app):
        """Each day entry has date, occupied, total, rate."""
        from models.insights import get_occupancy_range

        with app.app_context():
            today = date.today().isoformat()
            result = get_occupancy_range(today, today)

            assert len(result) == 1
            day = result[0]
            assert 'date' in day
            assert 'occupied' in day
            assert 'total' in day
            assert 'rate' in day


class TestGetOccupancyStats:
    """Tests for get_occupancy_stats function."""

    def test_returns_summary_stats(self, app):
        """Returns average occupancy, total reservations, no-show rate."""
        from models.insights import get_occupancy_stats

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_occupancy_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'avg_occupancy' in result
            assert 'total_reservations' in result
            assert 'noshow_rate' in result
            assert isinstance(result['avg_occupancy'], float)
            assert isinstance(result['total_reservations'], int)


class TestGetRevenueStats:
    """Tests for get_revenue_stats function."""

    def test_returns_revenue_summary(self, app):
        """Returns total revenue, paid reservations, average."""
        from models.insights import get_revenue_stats

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_revenue_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'total_revenue' in result
            assert 'paid_reservations' in result
            assert 'avg_per_reservation' in result
            assert isinstance(result['total_revenue'], (int, float))


class TestGetRevenueByType:
    """Tests for get_revenue_by_type function."""

    def test_returns_breakdown_by_reservation_type(self, app):
        """Returns revenue breakdown by reservation type."""
        from models.insights import get_revenue_by_type

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_revenue_by_type(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'by_reservation_type' in result
            assert 'by_customer_type' in result
            assert isinstance(result['by_reservation_type'], list)
            assert isinstance(result['by_customer_type'], list)


class TestGetTopPackages:
    """Tests for get_top_packages function."""

    def test_returns_package_list(self, app):
        """Returns list of top packages by usage."""
        from models.insights import get_top_packages

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_top_packages(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)


class TestGetCustomerStats:
    """Tests for get_customer_stats function."""

    def test_returns_required_fields(self, app):
        """Returns unique_customers, avg_group_size, returning_rate."""
        from models.insights import get_customer_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'unique_customers' in result
            assert 'avg_group_size' in result
            assert 'returning_rate' in result
            assert isinstance(result['unique_customers'], int)
            assert isinstance(result['avg_group_size'], float)
            assert isinstance(result['returning_rate'], float)

    def test_returns_zero_when_no_reservations(self, app):
        """Returns 0 values when no reservations exist in range."""
        from models.insights import get_customer_stats

        with app.app_context():
            # Use a date range in the past with no reservations
            result = get_customer_stats('2020-01-01', '2020-01-02')

            assert result['unique_customers'] == 0
            assert result['avg_group_size'] == 0.0


class TestGetCustomerSegmentation:
    """Tests for get_customer_segmentation function."""

    def test_returns_by_status_and_by_type(self, app):
        """Returns segmentation by status and by type."""
        from models.insights import get_customer_segmentation
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_segmentation(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'by_status' in result
            assert 'by_type' in result
            assert isinstance(result['by_status'], list)
            assert isinstance(result['by_type'], list)

    def test_status_items_have_required_fields(self, app):
        """Each status item has status, count, percentage."""
        from models.insights import get_customer_segmentation
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_segmentation(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for item in result['by_status']:
                assert 'status' in item
                assert 'count' in item
                assert 'percentage' in item
                assert item['status'] in ('new', 'returning')

    def test_type_items_have_required_fields(self, app):
        """Each type item has type, count, percentage."""
        from models.insights import get_customer_segmentation
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_segmentation(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for item in result['by_type']:
                assert 'type' in item
                assert 'count' in item
                assert 'percentage' in item


class TestGetTopCustomers:
    """Tests for get_top_customers function."""

    def test_returns_list(self, app):
        """Returns a list of top customers."""
        from models.insights import get_top_customers
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_top_customers(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)

    def test_each_customer_has_required_fields(self, app):
        """Each customer entry has required fields."""
        from models.insights import get_top_customers
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_top_customers(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for customer in result:
                assert 'customer_id' in customer
                assert 'customer_name' in customer
                assert 'customer_type' in customer
                assert 'reservation_count' in customer
                assert 'total_spend' in customer

    def test_respects_limit_parameter(self, app):
        """Respects the limit parameter."""
        from models.insights import get_top_customers
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_top_customers(
                start_date.isoformat(),
                end_date.isoformat(),
                limit=5
            )

            assert len(result) <= 5


class TestGetPopularPreferences:
    """Tests for get_popular_preferences function."""

    def test_returns_list(self, app):
        """Returns a list of popular preferences."""
        from models.insights import get_popular_preferences
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_popular_preferences(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)

    def test_each_preference_has_required_fields(self, app):
        """Each preference entry has required fields."""
        from models.insights import get_popular_preferences
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_popular_preferences(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for pref in result:
                assert 'preference_id' in pref
                assert 'preference_name' in pref
                assert 'preference_code' in pref
                assert 'count' in pref


class TestGetPopularTags:
    """Tests for get_popular_tags function."""

    def test_returns_list(self, app):
        """Returns a list of popular tags."""
        from models.insights import get_popular_tags
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_popular_tags(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)

    def test_each_tag_has_required_fields(self, app):
        """Each tag entry has required fields."""
        from models.insights import get_popular_tags
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_popular_tags(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for tag in result:
                assert 'tag_id' in tag
                assert 'tag_name' in tag
                assert 'tag_color' in tag
                assert 'count' in tag


class TestInsightsAPI:
    """Tests for insights API endpoints."""

    def test_today_endpoint_returns_data(self, authenticated_client, app):
        """GET /beach/api/insights/today returns today's metrics."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/today')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'occupancy' in data
            assert 'pending_checkins' in data
            assert 'zones' in data

    def test_today_endpoint_requires_auth(self, client, app):
        """GET /beach/api/insights/today requires authentication."""
        with app.app_context():
            response = client.get('/beach/api/insights/today')
            # Should redirect to login or return 401
            assert response.status_code in (302, 401)

    def test_occupancy_endpoint_returns_range_data(self, authenticated_client, app):
        """GET /beach/api/insights/occupancy returns occupancy data for range."""
        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            response = authenticated_client.get(
                f'/beach/api/insights/occupancy?start_date={start_date}&end_date={end_date}'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
            assert 'daily' in data
            assert 'by_zone' in data

    def test_revenue_endpoint_returns_data(self, authenticated_client, app):
        """GET /beach/api/insights/revenue returns revenue data."""
        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            response = authenticated_client.get(
                f'/beach/api/insights/revenue?start_date={start_date}&end_date={end_date}'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
            assert 'breakdown' in data
            assert 'top_packages' in data

    def test_customers_endpoint_returns_data(self, authenticated_client, app):
        """GET /beach/api/insights/customers returns customer analytics."""
        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            response = authenticated_client.get(
                f'/beach/api/insights/customers?start_date={start_date}&end_date={end_date}'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
            assert 'segmentation' in data
            assert 'top_customers' in data
            assert 'preferences' in data
            assert 'tags' in data

    def test_customers_endpoint_stats_structure(self, authenticated_client, app):
        """GET /beach/api/insights/customers returns correct stats structure."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/customers')

            assert response.status_code == 200
            data = response.get_json()
            stats = data['stats']
            assert 'unique_customers' in stats
            assert 'avg_group_size' in stats
            assert 'returning_rate' in stats

    def test_customers_endpoint_segmentation_structure(self, authenticated_client, app):
        """GET /beach/api/insights/customers returns correct segmentation structure."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/customers')

            assert response.status_code == 200
            data = response.get_json()
            segmentation = data['segmentation']
            assert 'by_status' in segmentation
            assert 'by_type' in segmentation


# =============================================================================
# PHASE 5: BOOKING PATTERNS TESTS
# =============================================================================

class TestGetPatternStats:
    """Tests for get_pattern_stats function."""

    def test_returns_required_fields(self, app):
        """Returns avg_lead_time, cancellation_rate, noshow_rate."""
        from models.insights import get_pattern_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_pattern_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'avg_lead_time' in result
            assert 'cancellation_rate' in result
            assert 'noshow_rate' in result
            assert isinstance(result['avg_lead_time'], (int, float))
            assert isinstance(result['cancellation_rate'], (int, float))
            assert isinstance(result['noshow_rate'], (int, float))

    def test_returns_zero_when_no_reservations(self, app):
        """Returns 0 values when no reservations exist in range."""
        from models.insights import get_pattern_stats

        with app.app_context():
            # Use a date range in the past with no reservations
            result = get_pattern_stats('2020-01-01', '2020-01-02')

            assert result['avg_lead_time'] == 0.0
            assert result['cancellation_rate'] == 0.0
            assert result['noshow_rate'] == 0.0

    def test_rates_are_percentages(self, app):
        """Rates should be between 0 and 100."""
        from models.insights import get_pattern_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_pattern_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 0 <= result['cancellation_rate'] <= 100
            assert 0 <= result['noshow_rate'] <= 100


class TestGetReservationsByDayOfWeek:
    """Tests for get_reservations_by_day_of_week function."""

    def test_returns_list_with_seven_days(self, app):
        """Returns list with 7 days of week."""
        from models.insights import get_reservations_by_day_of_week
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_reservations_by_day_of_week(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)
            assert len(result) == 7

    def test_each_day_has_required_fields(self, app):
        """Each day entry has day_of_week, name, count."""
        from models.insights import get_reservations_by_day_of_week
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_reservations_by_day_of_week(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for day in result:
                assert 'day_of_week' in day
                assert 'name' in day
                assert 'count' in day
                assert day['day_of_week'] in range(7)

    def test_day_names_in_spanish(self, app):
        """Day names should be in Spanish."""
        from models.insights import get_reservations_by_day_of_week
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_reservations_by_day_of_week(
                start_date.isoformat(),
                end_date.isoformat()
            )

            expected_names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
            names = [day['name'] for day in result]
            assert set(names) == set(expected_names)


class TestGetLeadTimeDistribution:
    """Tests for get_lead_time_distribution function."""

    def test_returns_five_buckets(self, app):
        """Returns 5 lead time buckets."""
        from models.insights import get_lead_time_distribution
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_lead_time_distribution(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)
            assert len(result) == 5

    def test_each_bucket_has_required_fields(self, app):
        """Each bucket entry has bucket, name, count, percentage."""
        from models.insights import get_lead_time_distribution
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_lead_time_distribution(
                start_date.isoformat(),
                end_date.isoformat()
            )

            expected_buckets = ['same_day', '1_2_days', '3_7_days', '8_14_days', '15_plus_days']
            for bucket in result:
                assert 'bucket' in bucket
                assert 'name' in bucket
                assert 'count' in bucket
                assert 'percentage' in bucket
                assert bucket['bucket'] in expected_buckets

    def test_percentages_sum_to_100_or_zero(self, app):
        """Percentages should sum to 100 (or 0 if no data)."""
        from models.insights import get_lead_time_distribution
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_lead_time_distribution(
                start_date.isoformat(),
                end_date.isoformat()
            )

            total_percentage = sum(b['percentage'] for b in result)
            # Should be 0 (no data) or close to 100 (with data)
            assert total_percentage == 0 or abs(total_percentage - 100) < 1


class TestGetCancellationBreakdown:
    """Tests for get_cancellation_breakdown function."""

    def test_returns_by_customer_type_and_by_lead_time(self, app):
        """Returns breakdown by customer type and by lead time."""
        from models.insights import get_cancellation_breakdown
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_cancellation_breakdown(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'by_customer_type' in result
            assert 'by_lead_time' in result
            assert isinstance(result['by_customer_type'], list)
            assert isinstance(result['by_lead_time'], list)

    def test_by_customer_type_has_required_fields(self, app):
        """Each customer type entry has type, rate."""
        from models.insights import get_cancellation_breakdown
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_cancellation_breakdown(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for item in result['by_customer_type']:
                assert 'type' in item
                assert 'rate' in item

    def test_by_lead_time_has_required_fields(self, app):
        """Each lead time entry has bucket, name, rate."""
        from models.insights import get_cancellation_breakdown
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_cancellation_breakdown(
                start_date.isoformat(),
                end_date.isoformat()
            )

            for item in result['by_lead_time']:
                assert 'bucket' in item
                assert 'name' in item
                assert 'rate' in item


class TestInsightsPatternsAPI:
    """Tests for /insights/patterns API endpoint."""

    def test_patterns_endpoint_returns_data(self, authenticated_client, app):
        """GET /beach/api/insights/patterns returns booking patterns data."""
        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            response = authenticated_client.get(
                f'/beach/api/insights/patterns?start_date={start_date}&end_date={end_date}'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
            assert 'by_day_of_week' in data
            assert 'lead_time' in data
            assert 'cancellation' in data

    def test_patterns_endpoint_requires_auth(self, client, app):
        """GET /beach/api/insights/patterns requires authentication."""
        with app.app_context():
            response = client.get('/beach/api/insights/patterns')
            # Should redirect to login or return 401
            assert response.status_code in (302, 401)

    def test_patterns_stats_structure(self, authenticated_client, app):
        """GET /beach/api/insights/patterns returns correct stats structure."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/patterns')

            assert response.status_code == 200
            data = response.get_json()
            stats = data['stats']
            assert 'avg_lead_time' in stats
            assert 'cancellation_rate' in stats
            assert 'noshow_rate' in stats

    def test_patterns_by_day_of_week_structure(self, authenticated_client, app):
        """GET /beach/api/insights/patterns returns 7 days of week."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/patterns')

            assert response.status_code == 200
            data = response.get_json()
            assert len(data['by_day_of_week']) == 7

    def test_patterns_lead_time_structure(self, authenticated_client, app):
        """GET /beach/api/insights/patterns returns 5 lead time buckets."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/patterns')

            assert response.status_code == 200
            data = response.get_json()
            assert len(data['lead_time']) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
