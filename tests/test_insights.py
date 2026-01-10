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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
