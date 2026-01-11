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
