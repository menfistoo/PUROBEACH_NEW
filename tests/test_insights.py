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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
