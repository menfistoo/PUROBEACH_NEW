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

            # Login first (password matches database/seed.py)
            client.post('/login', data={
                'username': 'admin',
                'password': 'PuroAdmin2026!'
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

            # Login first (password matches database/seed.py)
            client.post('/login', data={
                'username': 'admin',
                'password': 'PuroAdmin2026!'
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


class TestCreateFurnitureBlockConflict:
    """Block creation must reject furniture that has active reservations in the date range."""

    def _create_furniture(self, conn, zone_id: int, number: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active) "
            "VALUES (?, ?, 'hamaca', 2, 1)",
            (number, zone_id)
        )
        return cursor.lastrowid

    def _create_customer(self, conn, email: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_customers "
            "(first_name, last_name, customer_type, email, phone, created_at) "
            "VALUES ('Block', 'Test', 'externo', ?, '600000001', datetime('now'))",
            (email,)
        )
        return cursor.lastrowid

    def _assign_furniture(self, conn, furniture_id: int, date: str) -> None:
        """Create a minimal Confirmada reservation with furniture on `date`."""
        cust_id = self._create_customer(conn, f'blk_{date}_{furniture_id}@test.com')
        cursor = conn.execute(
            "INSERT INTO beach_reservations "
            "(customer_id, ticket_number, reservation_date, start_date, end_date, "
            " num_people, current_state, current_states, state_id, "
            " reservation_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, 2, 'Confirmada', 'Confirmada', 1, 'normal', datetime('now'))",
            (cust_id, f'BLKTEST{furniture_id}{date.replace("-","")}',
             date, date, date)
        )
        res_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date) "
            "VALUES (?, ?, ?)",
            (res_id, furniture_id, date)
        )
        conn.commit()

    def test_raises_when_active_reservation_exists_in_range(self, app):
        """create_furniture_block must raise ValueError when furniture is already reserved."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKCONFLICT01')
            db.commit()

            # Create a Confirmada reservation for '2026-07-10'
            self._assign_furniture(db, furniture_id, '2026-07-10')

            # Block overlapping that date must raise
            with pytest.raises(ValueError, match="reservas activas"):
                create_furniture_block(
                    furniture_id=furniture_id,
                    start_date='2026-07-08',
                    end_date='2026-07-12',
                    block_type='maintenance',
                    created_by='test'
                )

    def test_succeeds_when_only_releasing_state_reservations_exist(self, app):
        """Block should be allowed when conflicting reservations are all Cancelada/No-Show/Liberada."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKNOCONFLICT01')
            cust_id = self._create_customer(db, 'blk_releasing@test.com')
            db.commit()

            # Create a Cancelada reservation on '2026-08-05'
            cursor.execute(
                "INSERT INTO beach_reservations "
                "(customer_id, ticket_number, reservation_date, start_date, end_date, "
                " num_people, current_state, current_states, state_id, "
                " reservation_type, created_at) "
                "VALUES (?, 'BLKREL01', '2026-08-05', '2026-08-05', '2026-08-05', "
                "        2, 'Cancelada', 'Cancelada', 1, 'normal', datetime('now'))",
                (cust_id,)
            )
            res_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date) "
                "VALUES (?, ?, '2026-08-05')",
                (res_id, furniture_id)
            )
            db.commit()

            # Block on the same range must succeed (Cancelada is a releasing state)
            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date='2026-08-01',
                end_date='2026-08-10',
                block_type='maintenance',
                created_by='test'
            )
            assert isinstance(block_id, int)
            assert block_id > 0

    def test_succeeds_when_no_reservations_in_range(self, app):
        """Block must succeed when no reservations exist in the date range."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKEMPTY01')
            db.commit()

            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date='2026-09-01',
                end_date='2026-09-05',
                block_type='vip_hold',
                created_by='test'
            )
            assert isinstance(block_id, int)
