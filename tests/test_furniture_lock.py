"""
Tests for furniture lock feature.
"""

import pytest
from database import get_db


class TestFurnitureLockToggle:
    """Tests for toggling furniture lock on reservations."""

    def test_toggle_lock_on(self, app):
        """Should set is_furniture_locked to 1."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            # Create test customer and get state
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create test reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid
                conn.commit()

            # Toggle lock ON
            result = toggle_furniture_lock(reservation_id, locked=True)

            assert result['success'] is True
            assert result['is_furniture_locked'] is True

            # Verify in database
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
                    (reservation_id,)
                )
                row = cursor.fetchone()
                assert row['is_furniture_locked'] == 1

    def test_toggle_lock_off(self, app):
        """Should set is_furniture_locked to 0."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            # Create test customer and get state
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create locked reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, 1, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid
                conn.commit()

            # Toggle lock OFF
            result = toggle_furniture_lock(reservation_id, locked=False)

            assert result['success'] is True
            assert result['is_furniture_locked'] is False

    def test_toggle_lock_nonexistent_reservation(self, app):
        """Should return error for nonexistent reservation."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            result = toggle_furniture_lock(99999, locked=True)

            assert result['success'] is False
            assert 'error' in result


class TestMoveModeLockCheck:
    """Tests for lock checking in move mode operations."""

    def test_unassign_blocked_when_locked(self, app):
        """Should block unassign when reservation is locked."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create locked reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, 1, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid

                # Get or create furniture
                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()
                if not furniture:
                    cursor.execute("""
                        INSERT INTO beach_furniture (furniture_name, furniture_type_id, active)
                        SELECT 'Test Furniture', id, 1 FROM beach_furniture_types LIMIT 1
                    """)
                    furniture_id = cursor.lastrowid
                else:
                    furniture_id = furniture['id']

                # Assign furniture
                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, date('now'))
                """, (reservation_id, furniture_id))

                today = cursor.execute("SELECT date('now') as d").fetchone()['d']
                conn.commit()

            # Try to unassign - should be blocked
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=today
            )

            assert result['success'] is False
            assert result.get('error') == 'locked'

    def test_unassign_allowed_when_unlocked(self, app):
        """Should allow unassign when reservation is not locked."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create unlocked reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, 0, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid

                # Get or create furniture
                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()
                if not furniture:
                    cursor.execute("""
                        INSERT INTO beach_furniture (furniture_name, furniture_type_id, active)
                        SELECT 'Test Furniture', id, 1 FROM beach_furniture_types LIMIT 1
                    """)
                    furniture_id = cursor.lastrowid
                else:
                    furniture_id = furniture['id']

                # Assign furniture
                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, date('now'))
                """, (reservation_id, furniture_id))

                today = cursor.execute("SELECT date('now') as d").fetchone()['d']
                conn.commit()

            # Unassign - should work
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=today
            )

            assert result['success'] is True


class TestToggleLockAPI:
    """Tests for the toggle lock API endpoint."""

    def test_toggle_lock_endpoint(self, client, app):
        """Should toggle lock via API."""
        from database import get_db

        with app.app_context():
            # Create test customer and reservation
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create test reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid
                conn.commit()

            # Login first
            client.post('/login', data={
                'username': 'admin',
                'password': 'admin123'
            }, follow_redirects=True)

            # Toggle lock ON
            response = client.patch(
                f'/beach/api/map/reservations/{reservation_id}/toggle-lock',
                json={'locked': True}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['is_furniture_locked'] is True

    def test_toggle_lock_requires_auth(self, client, app):
        """Should require authentication."""
        response = client.patch(
            '/beach/api/map/reservations/1/toggle-lock',
            json={'locked': True}
        )
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]


class TestReassignLockCheck:
    """Tests for lock checking in reassign furniture endpoint."""

    def test_reassign_blocked_when_locked(self, client, app):
        """Should block reassign when reservation is locked."""
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()

                # Get state ID
                cursor.execute("SELECT id FROM beach_reservation_states LIMIT 1")
                state_row = cursor.fetchone()
                state_id = state_row['id'] if state_row else None

                if not state_id:
                    pytest.skip("No reservation states available")

                # Create test customer
                cursor.execute("""
                    INSERT INTO beach_customers
                    (first_name, last_name, customer_type, email, phone, created_at)
                    VALUES ('Test', 'Customer', 'externo', 'test@test.com', '123456789', datetime('now'))
                """)
                customer_id = cursor.lastrowid

                # Create locked reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked, created_at)
                    VALUES (?, ?, date('now'), date('now'), 2, 1, datetime('now'))
                """, (customer_id, state_id))
                reservation_id = cursor.lastrowid

                # Get or create furniture
                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()
                if not furniture:
                    cursor.execute("""
                        INSERT INTO beach_furniture (furniture_name, furniture_type_id, active)
                        SELECT 'Test Furniture', id, 1 FROM beach_furniture_types LIMIT 1
                    """)
                    furniture_id = cursor.lastrowid
                else:
                    furniture_id = furniture['id']

                today = cursor.execute("SELECT date('now') as d").fetchone()['d']
                conn.commit()

            # Login first
            client.post('/login', data={
                'username': 'admin',
                'password': 'admin123'
            }, follow_redirects=True)

            # Try to reassign
            response = client.post(
                f'/beach/api/map/reservations/{reservation_id}/reassign-furniture',
                json={'furniture_ids': [furniture_id], 'date': today}
            )

            assert response.status_code == 403
            data = response.get_json()
            assert data['success'] is False
            assert data.get('error') == 'locked'
