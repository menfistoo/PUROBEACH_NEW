"""
Tests for reservation model and routes.
Phase 6A: Core CRUD + State Management
"""

import pytest
from datetime import date, timedelta
from app import create_app
from database import get_db, init_db
from database.migrations import run_all_migrations


@pytest.fixture
def app():
    """Create test application with migrations."""
    import os
    # Use conftest.py's test database path
    test_db = os.environ.get('DATABASE_PATH', 'instance/test_beach_club.db')

    app = create_app('test')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DATABASE_PATH'] = test_db

    with app.app_context():
        init_db()
        # Run all migrations to ensure schema is complete
        run_all_migrations()
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestReservationModel:
    """Test reservation model functions."""

    def test_get_reservation_states(self, app):
        """Test getting all reservation states."""
        with app.app_context():
            from models.reservation import get_reservation_states

            states = get_reservation_states()
            assert len(states) > 0

            # Check default states exist
            state_names = [s['name'] for s in states]
            assert 'Confirmada' in state_names

    def test_get_reservation_stats(self, app):
        """Test getting reservation statistics."""
        with app.app_context():
            from models.reservation import get_reservation_stats

            today = date.today().isoformat()
            stats = get_reservation_stats(today)

            # Check new stats structure
            assert 'total' in stats
            assert 'by_state' in stats
            assert 'by_type' in stats
            assert 'interno' in stats
            assert 'externo' in stats

    def test_get_reservations_filtered(self, app):
        """Test filtered reservation listing."""
        with app.app_context():
            from models.reservation import get_reservations_filtered

            result = get_reservations_filtered()

            # Check new return structure
            assert 'items' in result
            assert 'total' in result
            assert 'page' in result
            assert 'pages' in result
            assert isinstance(result['items'], list)
            assert isinstance(result['total'], int)

    def test_generate_reservation_number(self, app):
        """Test ticket number generation (YYMMDDRR format)."""
        with app.app_context():
            from models.reservation import generate_reservation_number

            today = date.today().isoformat()
            ticket = generate_reservation_number(today)

            # Check format: YYMMDDRR (8 chars)
            assert len(ticket) == 8
            assert ticket[:6] == date.today().strftime('%y%m%d')

    def test_create_beach_reservation(self, app):
        """Test creating a reservation with new API."""
        with app.app_context():
            from models.reservation import create_beach_reservation
            from models.customer import create_customer

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Test',
                last_name='Reservation',
                phone='555-TEST-001'
            )

            today = date.today().isoformat()

            # Get a furniture ID
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1')
            row = cursor.fetchone()

            if row:
                furniture_id = row['id']

                reservation_id, ticket = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=today,
                    num_people=2,
                    furniture_ids=[furniture_id],
                    created_by='test'
                )

                assert reservation_id > 0
                assert len(ticket) == 8  # YYMMDDRR

    def test_get_available_furniture(self, app):
        """Test getting available furniture for a date."""
        with app.app_context():
            from models.reservation import get_available_furniture

            today = date.today().isoformat()

            furniture = get_available_furniture(today)

            assert isinstance(furniture, list)
            if len(furniture) > 0:
                f = furniture[0]
                assert 'id' in f
                assert 'number' in f
                assert 'furniture_type' in f

    def test_check_furniture_availability(self, app):
        """Test checking single furniture availability."""
        with app.app_context():
            from models.reservation import check_furniture_availability

            today = date.today().isoformat()

            # Get a furniture ID
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1')
            row = cursor.fetchone()

            if row:
                furniture_id = row['id']
                is_available = check_furniture_availability(furniture_id, today, today)
                assert isinstance(is_available, bool)

    def test_change_reservation_state(self, app):
        """Test changing reservation state."""
        with app.app_context():
            from models.reservation import (
                create_beach_reservation, change_reservation_state,
                get_beach_reservation_by_id
            )
            from models.customer import create_customer

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='State',
                last_name='Test',
                phone='555-STATE-01'
            )

            today = date.today().isoformat()

            # Get a furniture ID
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1')
            row = cursor.fetchone()

            if row:
                furniture_id = row['id']

                # Create reservation
                reservation_id, _ = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=today,
                    num_people=2,
                    furniture_ids=[furniture_id],
                    created_by='test'
                )

                # Change state
                result = change_reservation_state(
                    reservation_id=reservation_id,
                    new_state='Sentada',
                    changed_by='test'
                )
                assert result is True

                # Verify state changed
                res = get_beach_reservation_by_id(reservation_id)
                assert res['current_state'] == 'Sentada'

    def test_add_remove_reservation_state(self, app):
        """Test adding and removing states (CSV multi-state)."""
        with app.app_context():
            from models.reservation import (
                create_beach_reservation, add_reservation_state,
                remove_reservation_state, get_beach_reservation_by_id
            )
            from models.customer import create_customer

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='MultiState',
                last_name='Test',
                phone='555-MULTI-01'
            )

            today = date.today().isoformat()

            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1')
            row = cursor.fetchone()

            if row:
                furniture_id = row['id']

                # Create reservation (starts with Confirmada)
                reservation_id, _ = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=today,
                    num_people=2,
                    furniture_ids=[furniture_id],
                    created_by='test'
                )

                # Add another state
                add_reservation_state(reservation_id, 'Sentada', 'test')

                # Check both states exist
                res = get_beach_reservation_by_id(reservation_id)
                assert 'Confirmada' in res['current_states']
                assert 'Sentada' in res['current_states']

                # Remove a state
                remove_reservation_state(reservation_id, 'Confirmada', 'test')

                # Verify
                res = get_beach_reservation_by_id(reservation_id)
                assert 'Confirmada' not in res['current_states']
                assert 'Sentada' in res['current_states']


class TestReservationRoutes:
    """Test reservation routes."""

    def test_reservations_list_requires_auth(self, client):
        """Test that reservations list requires authentication."""
        response = client.get('/beach/reservations')
        assert response.status_code == 302
        assert '/auth/login' in response.location or 'login' in response.location.lower()

    def test_reservations_create_requires_auth(self, client):
        """Test that reservations create requires authentication."""
        response = client.get('/beach/reservations/create')
        assert response.status_code == 302

    def test_reservation_api_requires_auth(self, client):
        """Test that reservation API requires authentication."""
        response = client.get('/beach/api/reservations/1')
        # API endpoints return JSON 401 instead of redirect
        assert response.status_code == 401

    def test_available_furniture_api_requires_auth(self, client):
        """Test that available furniture API requires authentication."""
        response = client.get('/beach/api/furniture/available?date=2025-01-01')
        # API endpoints return JSON 401 instead of redirect
        assert response.status_code == 401


class TestReservationPreferences:
    """Test reservation preference syncing."""

    def test_get_customer_preference_codes(self, app):
        """Test getting customer preference codes."""
        with app.app_context():
            from models.reservation import get_customer_preference_codes
            from models.customer import create_customer, set_customer_preferences

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Pref',
                last_name='Test',
                phone='555-PREF-TST'
            )

            # Get characteristic IDs (preferences are now characteristics)
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_characteristics LIMIT 2')
            pref_ids = [r['id'] for r in cursor.fetchall()]

            if pref_ids:
                # Set preferences
                set_customer_preferences(customer_id, pref_ids)

                # Get codes
                codes = get_customer_preference_codes(customer_id)
                assert isinstance(codes, list)
                assert len(codes) == len(pref_ids)

    def test_sync_preferences_to_customer(self, app):
        """Test syncing reservation preferences to customer profile."""
        with app.app_context():
            from models.reservation import sync_preferences_to_customer, get_customer_preference_codes
            from models.customer import create_customer

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Sync',
                last_name='Prefs',
                phone='555-SYNC-001'
            )

            # Get characteristic codes (preferences are now characteristics)
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT code FROM beach_characteristics LIMIT 2')
            pref_codes = [r['code'] for r in cursor.fetchall()]

            if pref_codes:
                # Sync preferences
                prefs_csv = ','.join(pref_codes)
                sync_preferences_to_customer(customer_id, prefs_csv)

                # Verify
                customer_codes = get_customer_preference_codes(customer_id)
                assert len(customer_codes) == len(pref_codes)


class TestTicketNumberGeneration:
    """Test ticket number generation."""

    def test_sequential_numbers(self, app):
        """Test that ticket numbers are sequential for same day via reservations."""
        with app.app_context():
            from models.reservation import create_beach_reservation
            from models.customer import create_customer

            today = date.today().isoformat()

            # Create test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Seq',
                last_name='Test',
                phone='555-SEQ-001'
            )

            # Get a furniture ID
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_furniture WHERE active = 1 LIMIT 2')
            rows = cursor.fetchall()

            if len(rows) >= 2:
                # Create two reservations
                _, ticket1 = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=today,
                    num_people=2,
                    furniture_ids=[rows[0]['id']],
                    created_by='test'
                )

                _, ticket2 = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=today,
                    num_people=2,
                    furniture_ids=[rows[1]['id']],
                    created_by='test'
                )

                # Same date prefix
                assert ticket1[:6] == ticket2[:6]

                # Sequential
                seq1 = int(ticket1[6:])
                seq2 = int(ticket2[6:])
                assert seq2 == seq1 + 1

    def test_different_dates(self, app):
        """Test different dates get different prefixes."""
        with app.app_context():
            from models.reservation import generate_reservation_number

            today = date.today().isoformat()
            tomorrow = (date.today() + timedelta(days=1)).isoformat()

            ticket1 = generate_reservation_number(today)
            ticket2 = generate_reservation_number(tomorrow)

            # Different date prefixes
            assert ticket1[:6] != ticket2[:6]
