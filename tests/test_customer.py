"""
Tests for customer model and routes.
"""
import sys
import os

# Change to project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

import pytest
from app import create_app
from models.customer import (
    get_all_customers, get_customer_by_id, create_customer, update_customer,
    delete_customer, search_customers, find_duplicates, get_customers_filtered,
    get_customer_with_details, get_customer_stats, set_customer_preferences,
    set_customer_tags, merge_customers, find_potential_duplicates_for_customer
)


@pytest.fixture
def app():
    """Create application for testing."""
    from database import init_db

    app = create_app('test')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        init_db()
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestCustomerModel:
    """Test customer model functions."""

    def test_get_all_customers(self, app):
        """Test getting all customers."""
        with app.app_context():
            customers = get_all_customers()
            assert isinstance(customers, list)

    def test_create_customer_interno(self, app):
        """Test creating an interno customer."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='interno',
                first_name='Test',
                last_name='Guest',
                room_number='101',
                phone='555-1234'
            )
            assert customer_id is not None
            assert customer_id > 0

            customer = get_customer_by_id(customer_id)
            assert customer is not None
            assert customer['first_name'] == 'Test'
            assert customer['last_name'] == 'Guest'
            assert customer['customer_type'] == 'interno'
            assert customer['room_number'] == '101'

            # Clean up
            delete_customer(customer_id)

    def test_create_customer_externo(self, app):
        """Test creating an externo customer."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='externo',
                first_name='External',
                last_name='Customer',
                email='external@test.com',
                phone='555-5678'
            )
            assert customer_id is not None

            customer = get_customer_by_id(customer_id)
            assert customer['customer_type'] == 'externo'
            assert customer['email'] == 'external@test.com'

            # Clean up
            delete_customer(customer_id)

    def test_create_interno_requires_room(self, app):
        """Test that interno customers require room number."""
        with app.app_context():
            with pytest.raises(ValueError) as exc_info:
                create_customer(
                    customer_type='interno',
                    first_name='Test',
                    last_name='Guest'
                )
            assert 'habitación' in str(exc_info.value).lower()

    def test_update_customer(self, app):
        """Test updating a customer."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='externo',
                first_name='Original',
                last_name='Name',
                phone='555-0000'
            )

            result = update_customer(customer_id, first_name='Updated', vip_status=1)
            assert result is True

            customer = get_customer_by_id(customer_id)
            assert customer['first_name'] == 'Updated'
            assert customer['vip_status'] == 1

            # Clean up
            delete_customer(customer_id)

    def test_search_customers(self, app):
        """Test customer search."""
        with app.app_context():
            # Create a test customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Searchable',
                last_name='User',
                phone='555-9999'
            )

            # Search by name
            results = search_customers('Searchable')
            assert len(results) >= 1
            assert any(c['first_name'] == 'Searchable' for c in results)

            # Search by phone
            results = search_customers('555-9999')
            assert len(results) >= 1

            # Clean up
            delete_customer(customer_id)

    def test_get_customers_filtered(self, app):
        """Test filtered customer list."""
        with app.app_context():
            # Create test customers
            interno_id = create_customer(
                customer_type='interno',
                first_name='Interno',
                last_name='Test',
                room_number='200'
            )
            externo_id = create_customer(
                customer_type='externo',
                first_name='Externo',
                last_name='Test',
                phone='555-1111'
            )

            # Filter by type
            result = get_customers_filtered(customer_type='interno')
            assert 'customers' in result
            assert 'total' in result
            assert all(c['customer_type'] == 'interno' for c in result['customers'])

            # Clean up
            delete_customer(interno_id)
            delete_customer(externo_id)

    def test_find_duplicates(self, app):
        """Test duplicate detection."""
        with app.app_context():
            # Create a customer
            customer_id = create_customer(
                customer_type='externo',
                first_name='Duplicate',
                last_name='Test',
                phone='555-DUP'
            )

            # Try to find duplicates with same phone
            duplicates = find_duplicates('555-DUP', 'externo')
            assert len(duplicates) >= 1
            assert any(d['id'] == customer_id for d in duplicates)

            # Clean up
            delete_customer(customer_id)

    def test_get_customer_stats(self, app):
        """Test customer statistics."""
        with app.app_context():
            stats = get_customer_stats()
            assert 'total' in stats
            assert 'interno' in stats
            assert 'externo' in stats
            assert 'vip' in stats
            assert isinstance(stats['total'], int)


class TestCustomerPreferencesAndTags:
    """Test customer preferences and tags."""

    def test_set_customer_preferences(self, app):
        """Test setting customer preferences."""
        with app.app_context():
            from models.preference import get_all_preferences

            customer_id = create_customer(
                customer_type='externo',
                first_name='Pref',
                last_name='Test',
                phone='555-PREF'
            )

            preferences = get_all_preferences()
            if preferences:
                pref_ids = [preferences[0]['id']]
                set_customer_preferences(customer_id, pref_ids)

                customer = get_customer_with_details(customer_id)
                assert len(customer['preferences']) == 1

            # Clean up
            delete_customer(customer_id)

    def test_set_customer_tags(self, app):
        """Test setting customer tags."""
        with app.app_context():
            from models.tag import get_all_tags, create_tag

            customer_id = create_customer(
                customer_type='externo',
                first_name='Tag',
                last_name='Test',
                phone='555-TAG'
            )

            tags = get_all_tags()
            if not tags:
                tag_id = create_tag('Test Tag', '#FF0000')
                tags = [{'id': tag_id}]

            tag_ids = [tags[0]['id']]
            set_customer_tags(customer_id, tag_ids)

            customer = get_customer_with_details(customer_id)
            assert len(customer['tags']) == 1

            # Clean up
            delete_customer(customer_id)


class TestCustomerMerge:
    """Test customer merge functionality."""

    def test_merge_customers(self, app):
        """Test merging two customers."""
        with app.app_context():
            # Create source customer
            source_id = create_customer(
                customer_type='externo',
                first_name='Source',
                last_name='Customer',
                phone='555-SRC'
            )

            # Create target customer
            target_id = create_customer(
                customer_type='externo',
                first_name='Target',
                last_name='Customer',
                phone='555-TGT'
            )

            # Merge source into target
            result = merge_customers(source_id, target_id)
            assert result is True

            # Verify source was deleted
            source = get_customer_by_id(source_id)
            assert source is None

            # Verify target still exists
            target = get_customer_by_id(target_id)
            assert target is not None

            # Clean up
            delete_customer(target_id)

    def test_merge_same_customer_fails(self, app):
        """Test that merging a customer with itself fails."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='externo',
                first_name='Self',
                last_name='Merge',
                phone='555-SELF'
            )

            with pytest.raises(ValueError):
                merge_customers(customer_id, customer_id)

            # Clean up
            delete_customer(customer_id)


class TestCustomerRoutes:
    """Test customer routes."""

    def test_customers_list_requires_auth(self, client):
        """Test that customer list requires authentication."""
        response = client.get('/beach/customers')
        assert response.status_code in [302, 401]

    def test_customers_create_requires_auth(self, client):
        """Test that customer create requires authentication."""
        response = client.get('/beach/customers/create')
        assert response.status_code in [302, 401]

    def test_customer_api_search_requires_auth(self, client):
        """Test that customer search API requires authentication."""
        response = client.get('/beach/api/customers/search?q=test')
        assert response.status_code in [302, 401]
