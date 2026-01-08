"""
Tests for waitlist model functions.
"""

import pytest
from datetime import date, timedelta


class TestWaitlistCount:
    """Tests for get_waitlist_count function."""

    def test_count_returns_zero_for_empty(self, app):
        """Count returns 0 when no entries exist."""
        from models.waitlist import get_waitlist_count

        with app.app_context():
            count = get_waitlist_count(date.today().isoformat())
            assert count == 0

    def test_count_only_waiting_status(self, app):
        """Count only includes entries with 'waiting' status."""
        from models.waitlist import get_waitlist_count, create_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            # Create test customer
            customer_id = create_customer(
                first_name='Test',
                last_name='Customer',
                customer_type='externo',
                phone='600123456'
            )

            today = date.today().isoformat()

            # Create entry (status defaults to 'waiting')
            create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 2
            }, created_by=1)

            count = get_waitlist_count(today)
            assert count == 1


class TestWaitlistByDate:
    """Tests for get_waitlist_by_date function."""

    def test_returns_entries_for_date(self, app):
        """Returns all waiting entries for a specific date."""
        from models.waitlist import get_waitlist_by_date, create_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Test',
                last_name='User',
                customer_type='externo',
                phone='600111222'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 2,
                'notes': 'Test entry'
            }, created_by=1)

            entries = get_waitlist_by_date(today)

            assert len(entries) == 1
            assert entries[0]['id'] == entry_id
            assert entries[0]['customer_name'] is not None
            assert entries[0]['num_people'] == 2

    def test_excludes_non_waiting_status(self, app):
        """Does not return entries with non-waiting status."""
        from models.waitlist import get_waitlist_by_date, create_waitlist_entry, update_waitlist_status
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Another',
                last_name='User',
                customer_type='externo',
                phone='600333444'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 3
            }, created_by=1)

            # Change status to contacted
            update_waitlist_status(entry_id, 'contacted')

            entries = get_waitlist_by_date(today)
            assert len(entries) == 0

            # But history should include it
            entries = get_waitlist_by_date(today, include_all=True)
            assert len(entries) == 1


class TestWaitlistConvert:
    """Tests for convert_to_reservation function."""

    def test_convert_sets_status_and_reservation_id(self, app):
        """Convert marks entry as converted and links reservation."""
        from models.waitlist import create_waitlist_entry, convert_to_reservation, get_waitlist_entry
        from models.customer import create_customer
        from database import get_db

        with app.app_context():
            customer_id = create_customer(
                first_name='Convert',
                last_name='Test',
                customer_type='externo',
                phone='600555666'
            )

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': date.today().isoformat(),
                'num_people': 2
            }, created_by=1)

            # Create a real reservation to satisfy FK constraint
            today = date.today().isoformat()
            with get_db() as conn:
                cursor = conn.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, start_date, end_date, num_people, created_by
                    ) VALUES (?, ?, ?, 2, 1)
                ''', (customer_id, today, today))
                reservation_id = cursor.lastrowid
                conn.commit()

            convert_to_reservation(entry_id, reservation_id)

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'converted'
            assert entry['converted_reservation_id'] == reservation_id

    def test_convert_fails_on_already_converted(self, app):
        """Cannot convert an already converted entry."""
        from models.waitlist import create_waitlist_entry, convert_to_reservation
        from models.customer import create_customer
        from database import get_db

        with app.app_context():
            customer_id = create_customer(
                first_name='Double',
                last_name='Convert',
                customer_type='externo',
                phone='600555777'
            )

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': date.today().isoformat(),
                'num_people': 2
            }, created_by=1)

            # Create real reservations to satisfy FK constraint
            today = date.today().isoformat()
            with get_db() as conn:
                cursor = conn.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, start_date, end_date, num_people, created_by
                    ) VALUES (?, ?, ?, 2, 1)
                ''', (customer_id, today, today))
                reservation_id_1 = cursor.lastrowid
                cursor = conn.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, start_date, end_date, num_people, created_by
                    ) VALUES (?, ?, ?, 2, 1)
                ''', (customer_id, today, today))
                reservation_id_2 = cursor.lastrowid
                conn.commit()

            # First conversion succeeds
            convert_to_reservation(entry_id, reservation_id_1)

            # Second conversion should fail
            with pytest.raises(ValueError, match="No se puede convertir"):
                convert_to_reservation(entry_id, reservation_id_2)

    def test_convert_fails_on_nonexistent_entry(self, app):
        """Cannot convert a nonexistent entry."""
        from models.waitlist import convert_to_reservation

        with app.app_context():
            with pytest.raises(ValueError, match="Entrada no encontrada"):
                convert_to_reservation(99999, 100)


class TestWaitlistExpire:
    """Tests for expire_old_entries function."""

    def test_expires_past_date_entries(self, app):
        """Entries with past dates are expired."""
        from models.waitlist import create_waitlist_entry, expire_old_entries, get_waitlist_entry
        from models.customer import create_customer
        from database import get_db

        with app.app_context():
            customer_id = create_customer(
                first_name='Expire',
                last_name='Test',
                customer_type='externo',
                phone='600777888'
            )

            # Create entry with future date first (to pass validation)
            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': date.today().isoformat(),
                'num_people': 1
            }, created_by=1)

            # Manually backdate it
            with get_db() as conn:
                yesterday = (date.today() - timedelta(days=1)).isoformat()
                conn.execute(
                    'UPDATE beach_waitlist SET requested_date = ? WHERE id = ?',
                    (yesterday, entry_id)
                )
                conn.commit()

            # Run expire
            expired_count = expire_old_entries()
            assert expired_count >= 1

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'expired'

    def test_does_not_expire_future_entries(self, app):
        """Entries with future dates are not expired."""
        from models.waitlist import create_waitlist_entry, expire_old_entries, get_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Future',
                last_name='Entry',
                customer_type='externo',
                phone='600888999'
            )

            # Create entry with tomorrow's date
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': tomorrow,
                'num_people': 1
            }, created_by=1)

            # Run expire - should not affect future entries
            expire_old_entries()

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'waiting'

    def test_does_not_expire_already_converted(self, app):
        """Already converted entries are not expired."""
        from models.waitlist import create_waitlist_entry, expire_old_entries, convert_to_reservation, get_waitlist_entry
        from models.customer import create_customer
        from database import get_db

        with app.app_context():
            customer_id = create_customer(
                first_name='Converted',
                last_name='Entry',
                customer_type='externo',
                phone='600999111'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 1
            }, created_by=1)

            # Create a real reservation to satisfy FK constraint
            with get_db() as conn:
                cursor = conn.execute('''
                    INSERT INTO beach_reservations (
                        customer_id, start_date, end_date, num_people, created_by
                    ) VALUES (?, ?, ?, 1, 1)
                ''', (customer_id, today, today))
                reservation_id = cursor.lastrowid
                conn.commit()

            # Convert it first
            convert_to_reservation(entry_id, reservation_id)

            # Backdate it
            with get_db() as conn:
                yesterday = (date.today() - timedelta(days=1)).isoformat()
                conn.execute(
                    'UPDATE beach_waitlist SET requested_date = ? WHERE id = ?',
                    (yesterday, entry_id)
                )
                conn.commit()

            # Run expire - should not affect converted entries
            expire_old_entries()

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'converted'


class TestWaitlistHistory:
    """Tests for get_waitlist_history function."""

    def test_returns_non_waiting_entries(self, app):
        """History returns entries that are not in waiting status."""
        from models.waitlist import create_waitlist_entry, update_waitlist_status, get_waitlist_history
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='History',
                last_name='Test',
                customer_type='externo',
                phone='600111333'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 2
            }, created_by=1)

            # While waiting, should not appear in history
            history = get_waitlist_history(requested_date=today)
            assert len(history) == 0

            # Change to declined
            update_waitlist_status(entry_id, 'declined')

            # Now should appear in history
            history = get_waitlist_history(requested_date=today)
            assert len(history) == 1
            assert history[0]['status'] == 'declined'

    def test_filters_by_customer(self, app):
        """History can filter by customer_id."""
        from models.waitlist import create_waitlist_entry, update_waitlist_status, get_waitlist_history
        from models.customer import create_customer

        with app.app_context():
            customer1_id = create_customer(
                first_name='Customer',
                last_name='One',
                customer_type='externo',
                phone='600222444'
            )
            customer2_id = create_customer(
                first_name='Customer',
                last_name='Two',
                customer_type='externo',
                phone='600222555'
            )

            today = date.today().isoformat()

            entry1_id = create_waitlist_entry({
                'customer_id': customer1_id,
                'requested_date': today,
                'num_people': 1
            }, created_by=1)
            entry2_id = create_waitlist_entry({
                'customer_id': customer2_id,
                'requested_date': today,
                'num_people': 1
            }, created_by=1)

            # Decline both
            update_waitlist_status(entry1_id, 'declined')
            update_waitlist_status(entry2_id, 'declined')

            # Filter by customer1
            history = get_waitlist_history(customer_id=customer1_id)
            assert len(history) == 1
            assert history[0]['customer_id'] == customer1_id
