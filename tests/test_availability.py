"""
Tests for reservation availability functions.
"""

import pytest
from datetime import date, timedelta
from app import create_app
from database import get_db, init_db, migrate_reservations_v2, migrate_status_history_v2


@pytest.fixture
def app():
    """Create test application with migrations."""
    app = create_app('test')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        init_db()
        # Run required migrations
        migrate_reservations_v2()
        migrate_status_history_v2()
        yield app


@pytest.fixture
def setup_test_data(app):
    """Setup test data for availability tests."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Get a zone
        cursor.execute('SELECT id FROM beach_zones LIMIT 1')
        zone = cursor.fetchone()
        zone_id = zone['id'] if zone else 1

        # Create test furniture
        cursor.execute('''
            INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active)
            VALUES ('TEST01', ?, 'hamaca', 2, 1)
        ''', (zone_id,))
        furniture_id_1 = cursor.lastrowid

        cursor.execute('''
            INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active)
            VALUES ('TEST02', ?, 'hamaca', 2, 1)
        ''', (zone_id,))
        furniture_id_2 = cursor.lastrowid

        # Create test customer
        cursor.execute('''
            INSERT INTO beach_customers (customer_type, first_name, last_name, phone)
            VALUES ('externo', 'Test', 'Customer', '612345678')
        ''')
        customer_id = cursor.lastrowid

        db.commit()

        yield {
            'furniture_ids': [furniture_id_1, furniture_id_2],
            'customer_id': customer_id,
            'zone_id': zone_id
        }


class TestCheckFurnitureAvailabilityBulk:
    """Tests for bulk availability checking."""

    def test_empty_inputs(self, app):
        """Test with empty furniture_ids or dates."""
        with app.app_context():
            from models.reservation_availability import check_furniture_availability_bulk

            result = check_furniture_availability_bulk([], ['2025-01-15'])
            assert result['all_available'] is True
            assert result['unavailable'] == []

            result = check_furniture_availability_bulk([1, 2], [])
            assert result['all_available'] is True

    def test_all_available(self, app, setup_test_data):
        """Test when all furniture is available."""
        with app.app_context():
            from models.reservation_availability import check_furniture_availability_bulk

            furniture_ids = setup_test_data['furniture_ids']
            future_date = (date.today() + timedelta(days=30)).isoformat()

            result = check_furniture_availability_bulk(furniture_ids, [future_date])

            assert result['all_available'] is True
            assert result['unavailable'] == []
            assert future_date in result['availability_matrix']

    def test_availability_matrix_structure(self, app, setup_test_data):
        """Test availability matrix structure."""
        with app.app_context():
            from models.reservation_availability import check_furniture_availability_bulk

            furniture_ids = setup_test_data['furniture_ids']
            dates = [
                (date.today() + timedelta(days=30)).isoformat(),
                (date.today() + timedelta(days=31)).isoformat()
            ]

            result = check_furniture_availability_bulk(furniture_ids, dates)

            # Check matrix has all dates
            for d in dates:
                assert d in result['availability_matrix']
                # Check all furniture IDs present
                for furn_id in furniture_ids:
                    assert furn_id in result['availability_matrix'][d]


class TestCheckDuplicateReservation:
    """Tests for duplicate reservation detection."""

    def test_no_duplicate_empty_inputs(self, app):
        """Test with empty inputs."""
        with app.app_context():
            from models.reservation_availability import check_duplicate_reservation

            is_dup, existing = check_duplicate_reservation(None, ['2025-01-15'])
            assert is_dup is False
            assert existing is None

            is_dup, existing = check_duplicate_reservation(1, [])
            assert is_dup is False
            assert existing is None

    def test_no_duplicate_new_customer(self, app, setup_test_data):
        """Test no duplicate for new customer."""
        with app.app_context():
            from models.reservation_availability import check_duplicate_reservation

            customer_id = setup_test_data['customer_id']
            future_date = (date.today() + timedelta(days=60)).isoformat()

            is_dup, existing = check_duplicate_reservation(customer_id, [future_date])

            assert is_dup is False
            assert existing is None


class TestGetFurnitureAvailabilityMap:
    """Tests for availability map generation."""

    def test_empty_furniture(self, app):
        """Test with no active furniture matching filters."""
        with app.app_context():
            from models.reservation_availability import get_furniture_availability_map

            # Use non-existent zone
            result = get_furniture_availability_map(
                '2025-01-01', '2025-01-07',
                zone_id=99999
            )

            assert result['furniture'] == []
            assert result['dates'] == []
            assert result['availability'] == {}

    def test_availability_map_structure(self, app, setup_test_data):
        """Test availability map structure."""
        with app.app_context():
            from models.reservation_availability import get_furniture_availability_map

            date_from = (date.today() + timedelta(days=30)).isoformat()
            date_to = (date.today() + timedelta(days=32)).isoformat()

            result = get_furniture_availability_map(date_from, date_to)

            # Check structure
            assert 'furniture' in result
            assert 'dates' in result
            assert 'availability' in result
            assert 'summary' in result

            # Check dates list
            assert len(result['dates']) == 3  # 3 days

            # Check summary structure
            for d in result['dates']:
                assert d in result['summary']
                assert 'total' in result['summary'][d]
                assert 'available' in result['summary'][d]
                assert 'occupied' in result['summary'][d]
                assert 'occupancy_rate' in result['summary'][d]

    def test_availability_map_with_filters(self, app, setup_test_data):
        """Test availability map with zone filter."""
        with app.app_context():
            from models.reservation_availability import get_furniture_availability_map

            zone_id = setup_test_data['zone_id']
            date_from = (date.today() + timedelta(days=30)).isoformat()
            date_to = (date.today() + timedelta(days=30)).isoformat()

            result = get_furniture_availability_map(
                date_from, date_to,
                zone_id=zone_id
            )

            # Should have furniture from that zone
            assert isinstance(result['furniture'], list)
            assert isinstance(result['availability'], dict)


class TestGetConflictingReservations:
    """Tests for conflicting reservations lookup."""

    def test_empty_furniture_ids(self, app):
        """Test with empty furniture IDs."""
        with app.app_context():
            from models.reservation_availability import get_conflicting_reservations

            result = get_conflicting_reservations([], '2025-01-15')
            assert result == []

    def test_no_conflicts(self, app, setup_test_data):
        """Test when there are no conflicts."""
        with app.app_context():
            from models.reservation_availability import get_conflicting_reservations

            furniture_ids = setup_test_data['furniture_ids']
            future_date = (date.today() + timedelta(days=90)).isoformat()

            result = get_conflicting_reservations(furniture_ids, future_date)

            assert isinstance(result, list)
            assert len(result) == 0
