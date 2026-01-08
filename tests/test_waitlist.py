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
