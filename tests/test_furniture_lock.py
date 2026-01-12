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
