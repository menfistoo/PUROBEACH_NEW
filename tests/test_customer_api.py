"""
Tests for unified customer update endpoint: PATCH /beach/api/customers/<id>/update.
"""

import pytest
from models.customer import create_customer


class TestCustomerUnifiedUpdate:
    """Test the unified customer update endpoint PATCH /beach/api/customers/<id>/update."""

    @pytest.fixture
    def authenticated_client(self, app, client):
        """Create authenticated test client with admin session."""
        client.post('/login', data={
            'username': 'admin',
            'password': 'PuroAdmin2026!'
        }, follow_redirects=True)
        return client

    @pytest.fixture
    def externo_customer(self, app):
        """Create an externo test customer and return its ID."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='externo',
                first_name='TestExt',
                last_name='Customer',
                phone='555-CUST-EXT'
            )
            return customer_id

    @pytest.fixture
    def interno_customer(self, app):
        """Create an interno test customer and return its ID."""
        with app.app_context():
            customer_id = create_customer(
                customer_type='interno',
                first_name='TestInt',
                last_name='Customer',
                phone='555-CUST-INT',
                room_number='101'
            )
            return customer_id

    def _patch(self, client, customer_id, data):
        """Helper to send PATCH request to unified update endpoint."""
        return client.patch(
            f'/beach/api/customers/{customer_id}/update',
            json=data,
            content_type='application/json'
        )

    # =========================================================================
    # HAPPY PATH TESTS
    # =========================================================================

    def test_update_name(self, app, authenticated_client, externo_customer):
        """Test updating first_name (happy path)."""
        response = self._patch(authenticated_client, externo_customer, {
            'first_name': 'NuevoNombre'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'first_name' in data['updated_fields']
        assert data['customer']['first_name'] == 'NuevoNombre'

    def test_update_phone(self, app, authenticated_client, externo_customer):
        """Test updating phone number."""
        response = self._patch(authenticated_client, externo_customer, {
            'phone': '666123456'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'phone' in data['updated_fields']
        assert data['customer']['phone'] == '666123456'

    def test_update_vip_status(self, app, authenticated_client, externo_customer):
        """Test that vip_status is coerced to 0 or 1."""
        # Set VIP to truthy value
        response = self._patch(authenticated_client, externo_customer, {
            'vip_status': 'yes'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['customer']['vip_status'] == 1

        # Set VIP to falsy value
        response = self._patch(authenticated_client, externo_customer, {
            'vip_status': 0
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['customer']['vip_status'] == 0

    # =========================================================================
    # VALIDATION ERROR TESTS
    # =========================================================================

    def test_reject_empty_first_name(self, app, authenticated_client, externo_customer):
        """Test that empty first_name is rejected."""
        response = self._patch(authenticated_client, externo_customer, {
            'first_name': ''
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'nombre' in data['error'].lower()

    def test_reject_interno_without_room(self, app, authenticated_client, interno_customer):
        """Test that clearing room_number on interno customer is rejected."""
        response = self._patch(authenticated_client, interno_customer, {
            'room_number': ''
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'habitación' in data['error'].lower() or 'habitacion' in data['error'].lower()

    # =========================================================================
    # EDGE CASE TESTS
    # =========================================================================

    def test_nonexistent_customer_404(self, app, authenticated_client):
        """Test that updating a nonexistent customer returns 404."""
        response = self._patch(authenticated_client, 999999, {
            'first_name': 'Ghost'
        })
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False

    def test_empty_payload_returns_success(self, app, authenticated_client, externo_customer):
        """Test that an empty payload returns success with 'Sin cambios'."""
        response = self._patch(authenticated_client, externo_customer, {})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Sin cambios'
