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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
