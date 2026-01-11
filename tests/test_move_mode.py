"""
Tests for move mode feature.

Tests the model functions for unassigning and assigning furniture
during move mode operations.
"""

import pytest
from datetime import date, timedelta


def create_test_reservation_with_furniture(cursor, assignment_date: str):
    """
    Helper to create a test reservation with furniture assignment.
    Returns (reservation_id, furniture_id, assignment_date).
    """
    # Get or create a customer
    cursor.execute("""
        SELECT id FROM beach_customers LIMIT 1
    """)
    customer = cursor.fetchone()

    if not customer:
        cursor.execute("""
            INSERT INTO beach_customers (first_name, last_name, customer_type, phone)
            VALUES ('Test', 'Customer', 'externo', '555-1234')
        """)
        customer_id = cursor.lastrowid
    else:
        customer_id = customer['id']

    # Get a state
    cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
    state = cursor.fetchone()
    state_id = state['id'] if state else 1

    # Get furniture
    cursor.execute("""
        SELECT f.id FROM beach_furniture f
        WHERE f.active = 1
        LIMIT 2
    """)
    furniture_rows = cursor.fetchall()

    if len(furniture_rows) < 2:
        pytest.skip("Not enough furniture in test database")

    furniture_id_1 = furniture_rows[0]['id']
    furniture_id_2 = furniture_rows[1]['id']

    # Create reservation
    cursor.execute("""
        INSERT INTO beach_reservations
        (customer_id, state_id, start_date, end_date, num_people, created_at)
        VALUES (?, ?, ?, ?, 2, datetime('now'))
    """, (customer_id, state_id, assignment_date, assignment_date))
    reservation_id = cursor.lastrowid

    # Create furniture assignments
    cursor.execute("""
        INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
        VALUES (?, ?, ?)
    """, (reservation_id, furniture_id_1, assignment_date))

    cursor.execute("""
        INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
        VALUES (?, ?, ?)
    """, (reservation_id, furniture_id_2, assignment_date))

    return reservation_id, furniture_id_1, furniture_id_2, assignment_date


class TestUnassignFurniture:
    """Tests for unassigning furniture from reservations."""

    def test_unassign_single_furniture_success(self, app):
        """Should unassign one furniture from a reservation for a specific date."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, furniture_id, _, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            # Execute
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=assignment_date
            )

            # Verify
            assert result['success'] is True
            assert result['unassigned_count'] == 1
            assert furniture_id in result['furniture_ids']

            # Verify furniture is no longer assigned
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
                """, (reservation_id, furniture_id, assignment_date))
                assert cursor.fetchone()['cnt'] == 0

    def test_unassign_multiple_furniture_success(self, app):
        """Should unassign multiple furniture from a reservation."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, furniture_id_1, furniture_id_2, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            # Execute - unassign both
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id_1, furniture_id_2],
                assignment_date=assignment_date
            )

            # Verify
            assert result['success'] is True
            assert result['unassigned_count'] == 2

            # Verify all furniture is unassigned
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND assignment_date = ?
                """, (reservation_id, assignment_date))
                assert cursor.fetchone()['cnt'] == 0

    def test_unassign_nonexistent_furniture_returns_zero(self, app):
        """Should return zero count when furniture doesn't exist."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, _, _, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            # Try to unassign non-existent furniture
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[99999],
                assignment_date=assignment_date
            )

            # Should succeed but with 0 unassigned
            assert result['success'] is True
            assert result['unassigned_count'] == 0


class TestAssignFurniture:
    """Tests for assigning furniture to reservations."""

    def test_assign_furniture_success(self, app):
        """Should assign available furniture to a reservation for a specific date."""
        from models.move_mode import assign_furniture_for_date, unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()

                # Create reservation with furniture
                reservation_id, original_furniture_id, _, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)

                # Find available furniture (not assigned today)
                cursor.execute("""
                    SELECT f.id FROM beach_furniture f
                    WHERE f.active = 1
                    AND f.id NOT IN (
                        SELECT furniture_id
                        FROM beach_reservation_furniture
                        WHERE assignment_date = ?
                    )
                    LIMIT 1
                """, (assignment_date,))
                available = cursor.fetchone()
                conn.commit()

            if not available:
                pytest.skip("No available furniture for today")

            new_furniture_id = available['id']

            # First unassign original
            unassign_furniture_for_date(reservation_id, [original_furniture_id], assignment_date)

            # Execute: Assign new furniture
            result = assign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[new_furniture_id],
                assignment_date=assignment_date
            )

            # Verify
            assert result['success'] is True
            assert result['assigned_count'] == 1
            assert new_furniture_id in result['furniture_ids']

            # Verify furniture is assigned
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
                """, (reservation_id, new_furniture_id, assignment_date))
                assert cursor.fetchone()['cnt'] == 1

    def test_assign_furniture_already_taken_fails(self, app):
        """Should fail when furniture is already assigned to another reservation."""
        from models.move_mode import assign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()

                # Create first reservation with furniture
                res1_id, furniture_id_1, furniture_id_2, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)

                # Create second reservation (no furniture initially)
                cursor.execute("SELECT id FROM beach_customers LIMIT 1")
                customer = cursor.fetchone()
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state = cursor.fetchone()

                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, created_at)
                    VALUES (?, ?, ?, ?, 2, datetime('now'))
                """, (customer['id'], state['id'], assignment_date, assignment_date))
                res2_id = cursor.lastrowid
                conn.commit()

            # Try to assign reservation 1's furniture to reservation 2
            result = assign_furniture_for_date(
                reservation_id=res2_id,
                furniture_ids=[furniture_id_1],
                assignment_date=assignment_date
            )

            assert result['success'] is False
            assert 'error' in result

    def test_assign_already_assigned_to_same_reservation_succeeds(self, app):
        """Should succeed (idempotent) when furniture is already assigned to same reservation."""
        from models.move_mode import assign_furniture_for_date
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, furniture_id, _, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            # Try to assign furniture that's already assigned to this reservation
            result = assign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=assignment_date
            )

            # Should succeed (idempotent operation)
            assert result['success'] is True
            assert result['assigned_count'] == 1


class TestGetPoolData:
    """Tests for getting reservation data for the pool panel."""

    def test_get_reservation_pool_data(self, app):
        """Should return complete reservation data for pool display."""
        from models.move_mode import get_reservation_pool_data
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, _, _, assignment_date = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            result = get_reservation_pool_data(reservation_id, assignment_date)

            # Verify structure
            assert 'reservation_id' in result
            assert 'customer_name' in result
            assert 'room_number' in result
            assert 'num_people' in result
            assert 'preferences' in result
            assert 'original_furniture' in result
            assert 'is_multiday' in result
            assert 'total_days' in result

            # Verify values
            assert result['reservation_id'] == reservation_id
            assert result['num_people'] == 2  # From test setup
            assert len(result['original_furniture']) == 2  # Two furniture items

    def test_get_reservation_pool_data_not_found(self, app):
        """Should return error for non-existent reservation."""
        from models.move_mode import get_reservation_pool_data

        with app.app_context():
            today = date.today().isoformat()
            result = get_reservation_pool_data(99999, today)

            assert 'error' in result

    def test_get_reservation_pool_data_multiday(self, app):
        """Should identify multi-day reservations correctly."""
        from models.move_mode import get_reservation_pool_data
        from database import get_db

        with app.app_context():
            today = date.today()
            tomorrow = (today + timedelta(days=1)).isoformat()
            today_str = today.isoformat()

            with get_db() as conn:
                cursor = conn.cursor()

                # Create customer
                cursor.execute("SELECT id FROM beach_customers LIMIT 1")
                customer = cursor.fetchone()
                if not customer:
                    cursor.execute("""
                        INSERT INTO beach_customers (first_name, last_name, customer_type, phone)
                        VALUES ('MultiDay', 'Guest', 'externo', '555-9999')
                    """)
                    customer_id = cursor.lastrowid
                else:
                    customer_id = customer['id']

                # Get state
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state = cursor.fetchone()

                # Get furniture
                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()

                if not furniture:
                    pytest.skip("No furniture in test database")

                # Create multi-day reservation (2 days)
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, created_at)
                    VALUES (?, ?, ?, ?, 1, datetime('now'))
                """, (customer_id, state['id'], today_str, tomorrow))
                reservation_id = cursor.lastrowid

                # Add furniture for both days
                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, ?)
                """, (reservation_id, furniture['id'], today_str))
                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, ?)
                """, (reservation_id, furniture['id'], tomorrow))
                conn.commit()

            result = get_reservation_pool_data(reservation_id, today_str)

            assert result['is_multiday'] is True
            assert result['total_days'] == 2


class TestPreferenceMatching:
    """Tests for furniture preference matching."""

    def test_get_furniture_preference_matches_structure(self, app):
        """Should return furniture with preference match scores."""
        from models.move_mode import get_furniture_preference_matches

        with app.app_context():
            today = date.today().isoformat()

            result = get_furniture_preference_matches(
                preference_codes=['pref_sombra', 'pref_primera_linea'],
                target_date=today
            )

            assert 'furniture' in result
            assert isinstance(result['furniture'], list)

            # Each furniture should have match info
            for f in result['furniture']:
                assert 'id' in f
                assert 'number' in f
                assert 'available' in f
                assert 'match_score' in f
                assert 'matched_preferences' in f

    def test_get_furniture_preference_matches_availability(self, app):
        """Should mark occupied furniture as unavailable."""
        from models.move_mode import get_furniture_preference_matches
        from database import get_db

        with app.app_context():
            today = date.today().isoformat()

            # Create a reservation with furniture to make some occupied
            with get_db() as conn:
                cursor = conn.cursor()
                reservation_id, occupied_id, _, _ = \
                    create_test_reservation_with_furniture(cursor, today)
                conn.commit()

            result = get_furniture_preference_matches(
                preference_codes=[],
                target_date=today
            )

            # Find the occupied furniture in results
            occupied_furniture = next(
                (f for f in result['furniture'] if f['id'] == occupied_id),
                None
            )

            if occupied_furniture:
                assert occupied_furniture['available'] is False

    def test_get_furniture_preference_matches_empty_prefs(self, app):
        """Should work with empty preference list."""
        from models.move_mode import get_furniture_preference_matches

        with app.app_context():
            today = date.today().isoformat()

            result = get_furniture_preference_matches(
                preference_codes=[],
                target_date=today
            )

            assert 'furniture' in result
            # All furniture should have match_score of 0 with no preferences
            for f in result['furniture']:
                assert f['match_score'] == 0
                assert f['matched_preferences'] == []
