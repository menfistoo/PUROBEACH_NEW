"""
Tests for state synchronization between current_state and state_id.

Issue #6: Furniture shows as occupied when it should be free.
Root cause: add_reservation_state() updates current_state but not state_id,
causing data inconsistency that breaks availability queries using state_id.
"""

import pytest
from datetime import date, timedelta


@pytest.fixture
def setup_state_test_data(app):
    """Setup test data for state sync tests."""
    from database import get_db

    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Get zone
        cursor.execute('SELECT id FROM beach_zones LIMIT 1')
        zone = cursor.fetchone()
        zone_id = zone['id'] if zone else 1

        # Create test furniture
        cursor.execute('''
            INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active)
            VALUES ('STATE_TEST_01', ?, 'hamaca', 2, 1)
        ''', (zone_id,))
        furniture_id = cursor.lastrowid

        # Create test customer
        cursor.execute('''
            INSERT INTO beach_customers (customer_type, first_name, last_name, phone)
            VALUES ('externo', 'State', 'TestCustomer', '600000001')
        ''')
        customer_id = cursor.lastrowid

        # Get Confirmada and Cancelada state IDs
        cursor.execute("SELECT id FROM beach_reservation_states WHERE name = 'Confirmada'")
        confirmada_state = cursor.fetchone()
        confirmada_id = confirmada_state['id'] if confirmada_state else 1

        cursor.execute("SELECT id FROM beach_reservation_states WHERE name = 'Cancelada'")
        cancelada_state = cursor.fetchone()
        cancelada_id = cancelada_state['id'] if cancelada_state else None

        db.commit()

        yield {
            'furniture_id': furniture_id,
            'customer_id': customer_id,
            'zone_id': zone_id,
            'confirmada_id': confirmada_id,
            'cancelada_id': cancelada_id
        }


class TestStateSynchronization:
    """Tests for state_id and current_state synchronization."""

    def test_add_reservation_state_updates_state_id(self, app, setup_state_test_data):
        """
        When add_reservation_state() is called, it should update BOTH
        current_state AND state_id to keep them in sync.
        """
        from database import get_db
        from models.reservation_state import add_reservation_state

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_state_test_data
            test_date = (date.today() + timedelta(days=100)).isoformat()

            # Create a reservation with Confirmada state
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'SYNC-001', ?, ?, ?, 2, 'Confirmada', 'Confirmada', ?)
            ''', (data['customer_id'], test_date, test_date, test_date, data['confirmada_id']))
            reservation_id = cursor.lastrowid

            # Assign furniture
            cursor.execute('''
                INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, ?)
            ''', (reservation_id, data['furniture_id'], test_date))
            db.commit()

            # Change state to Cancelada using add_reservation_state
            add_reservation_state(reservation_id, 'Cancelada', changed_by='test')

            # Verify BOTH current_state AND state_id are updated
            cursor.execute('''
                SELECT current_state, state_id
                FROM beach_reservations WHERE id = ?
            ''', (reservation_id,))
            row = cursor.fetchone()

            assert row['current_state'] == 'Cancelada', \
                f"current_state should be 'Cancelada', got '{row['current_state']}'"
            assert row['state_id'] == data['cancelada_id'], \
                f"state_id should be {data['cancelada_id']} (Cancelada), got {row['state_id']}"

    def test_remove_reservation_state_updates_state_id(self, app, setup_state_test_data):
        """
        When remove_reservation_state() removes the current state,
        state_id should update to match the new current_state.
        """
        from database import get_db
        from models.reservation_state import add_reservation_state, remove_reservation_state

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_state_test_data
            test_date = (date.today() + timedelta(days=101)).isoformat()

            # Create reservation with Confirmada
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'SYNC-002', ?, ?, ?, 2, 'Confirmada', 'Confirmada', ?)
            ''', (data['customer_id'], test_date, test_date, test_date, data['confirmada_id']))
            reservation_id = cursor.lastrowid
            db.commit()

            # Add Cancelada state
            add_reservation_state(reservation_id, 'Cancelada', changed_by='test')

            # Remove Cancelada state - should revert to Confirmada
            remove_reservation_state(reservation_id, 'Cancelada', changed_by='test')

            cursor.execute('''
                SELECT current_state, state_id
                FROM beach_reservations WHERE id = ?
            ''', (reservation_id,))
            row = cursor.fetchone()

            assert row['current_state'] == 'Confirmada', \
                f"current_state should be 'Confirmada', got '{row['current_state']}'"
            assert row['state_id'] == data['confirmada_id'], \
                f"state_id should be {data['confirmada_id']} (Confirmada), got {row['state_id']}"


class TestAvailabilityWithStateSync:
    """Tests that availability queries work correctly with synced states."""

    def test_cancelled_reservation_releases_furniture(self, app, setup_state_test_data):
        """
        When a reservation is cancelled, the furniture should be available.
        This tests the full flow including move_mode queries that use state_id.
        """
        from database import get_db
        from models.reservation_state import add_reservation_state
        from models.reservation_queries import check_furniture_availability

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_state_test_data
            test_date = (date.today() + timedelta(days=102)).isoformat()

            # Create reservation and assign furniture
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'AVAIL-001', ?, ?, ?, 2, 'Confirmada', 'Confirmada', ?)
            ''', (data['customer_id'], test_date, test_date, test_date, data['confirmada_id']))
            reservation_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, ?)
            ''', (reservation_id, data['furniture_id'], test_date))
            db.commit()

            # Furniture should NOT be available (reservation active)
            available_before = check_furniture_availability(
                data['furniture_id'], test_date, test_date
            )
            assert available_before is False, "Furniture should be occupied before cancellation"

            # Cancel the reservation
            add_reservation_state(reservation_id, 'Cancelada', changed_by='test')

            # Furniture should NOW be available
            available_after = check_furniture_availability(
                data['furniture_id'], test_date, test_date
            )
            assert available_after is True, "Furniture should be available after cancellation"

    def test_move_mode_query_respects_cancelled_state(self, app, setup_state_test_data):
        """
        The move_mode query uses state_id to filter reservations.
        After cancellation, reservation should NOT appear in move mode.
        """
        from database import get_db
        from models.reservation_state import add_reservation_state

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_state_test_data
            test_date = (date.today() + timedelta(days=103)).isoformat()

            # Create reservation
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'MOVE-001', ?, ?, ?, 2, 'Confirmada', 'Confirmada', ?)
            ''', (data['customer_id'], test_date, test_date, test_date, data['confirmada_id']))
            reservation_id = cursor.lastrowid
            db.commit()

            # Simulate the move_mode query that uses state_id
            def get_reservations_via_state_id():
                cursor.execute("""
                    SELECT r.id
                    FROM beach_reservations r
                    LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
                    WHERE r.reservation_date = ?
                      AND (rs.is_availability_releasing IS NULL OR rs.is_availability_releasing = 0)
                """, (test_date,))
                return [row['id'] for row in cursor.fetchall()]

            # Before cancellation - should appear
            before = get_reservations_via_state_id()
            assert reservation_id in before, "Reservation should appear before cancellation"

            # Cancel
            add_reservation_state(reservation_id, 'Cancelada', changed_by='test')

            # After cancellation - should NOT appear
            after = get_reservations_via_state_id()
            assert reservation_id not in after, \
                "Cancelled reservation should NOT appear in move mode query"


class TestDataCleanup:
    """Tests for data cleanup of inconsistent records."""

    def test_identify_inconsistent_records(self, app, setup_state_test_data):
        """
        Test that we can identify records where current_state and state_id don't match.
        """
        from database import get_db

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_state_test_data
            test_date = (date.today() + timedelta(days=104)).isoformat()

            # Create a deliberately INCONSISTENT reservation
            # current_state = 'Cancelada' but state_id = 1 (Confirmada)
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'INCON-001', ?, ?, ?, 2, 'Cancelada', 'Cancelada', ?)
            ''', (data['customer_id'], test_date, test_date, test_date, data['confirmada_id']))
            reservation_id = cursor.lastrowid
            db.commit()

            # Query to find inconsistencies
            cursor.execute('''
                SELECT r.id, r.current_state, r.state_id, rs.name as state_name
                FROM beach_reservations r
                LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
                WHERE r.current_state != rs.name
                  AND r.id = ?
            ''', (reservation_id,))
            inconsistent = cursor.fetchone()

            assert inconsistent is not None, "Should detect inconsistent record"
            assert inconsistent['current_state'] == 'Cancelada'
            assert inconsistent['state_name'] == 'Confirmada'
