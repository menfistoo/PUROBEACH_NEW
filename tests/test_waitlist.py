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
