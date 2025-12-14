"""
Route tests.
Tests that all routes are accessible and return correct status codes.
"""

import sys
import os

# Change to project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

import pytest
from app import create_app


def test_public_routes():
    """Test public routes (no authentication required)."""
    app = create_app()

    with app.test_client() as client:
        # Test login page
        response = client.get('/login')
        assert response.status_code == 200, "Login page should be accessible"

        # Test API health check
        response = client.get('/api/health')
        assert response.status_code == 200, "API health check should be accessible"
        data = response.get_json()
        assert data['status'] == 'ok', "Health check should return OK status"

        # Test index redirect
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302, "Index should redirect when not authenticated"


def test_protected_routes():
    """Test that protected routes redirect to login."""
    app = create_app()

    protected_routes = [
        '/beach/map',
        '/beach/customers',
        '/beach/reservations',
        '/admin/dashboard',
        '/admin/users',
        '/admin/roles'
    ]

    with app.test_client() as client:
        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code in [302, 401], f"{route} should be protected"


if __name__ == '__main__':
    test_public_routes()
    test_protected_routes()
    print("\n[SUCCESS] All route tests passed!")
