"""
Comprehensive test script to find all errors in the application.
Tests all routes, templates, and database operations.
"""

import sys
from app import create_app
from database import get_db

def test_app():
    """Run comprehensive tests."""
    print("=" * 60)
    print("PUROBEACH - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    errors = []

    # Create app
    from database import init_db
    app = create_app('test')
    app.config['TESTING'] = True

    # Initialize test database
    with app.app_context():
        init_db()

    with app.test_client() as client:
        with app.app_context():
            # Test 1: Database connection
            print("\n[TEST 1] Database Connection...")
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                print(f"  ✓ Database connected: {user_count} users found")
            except Exception as e:
                errors.append(f"Database connection: {e}")
                print(f"  ✗ Error: {e}")

            # Test 2: Login page
            print("\n[TEST 2] Login Page...")
            try:
                response = client.get('/login')
                if response.status_code == 200:
                    print(f"  ✓ Login page loads (status: {response.status_code})")
                else:
                    errors.append(f"Login page returned {response.status_code}")
                    print(f"  ✗ Status: {response.status_code}")
            except Exception as e:
                errors.append(f"Login page: {e}")
                print(f"  ✗ Error: {e}")

            # Test 3: Login authentication
            print("\n[TEST 3] Login Authentication...")
            try:
                response = client.post('/login', data={
                    'username': 'admin',
                    'password': 'admin123',
                    'csrf_token': 'test'  # Will fail CSRF but test the route
                }, follow_redirects=False)
                print(f"  ✓ Login route accessible (status: {response.status_code})")
            except Exception as e:
                errors.append(f"Login authentication: {e}")
                print(f"  ✗ Error: {e}")

            # Test 4: API health check (no auth required)
            print("\n[TEST 4] API Health Check...")
            try:
                response = client.get('/api/health')
                if response.status_code == 200:
                    print(f"  ✓ API health check OK")
                    print(f"    Response: {response.get_json()}")
                else:
                    errors.append(f"API health returned {response.status_code}")
            except Exception as e:
                errors.append(f"API health: {e}")
                print(f"  ✗ Error: {e}")

            # Test 5: Protected routes (should redirect to login)
            print("\n[TEST 5] Protected Routes (should redirect)...")
            protected_routes = [
                '/beach/map',
                '/beach/customers',
                '/beach/reservations',
                '/admin/dashboard',
                '/admin/users',
                '/admin/roles'
            ]

            for route in protected_routes:
                try:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code in [302, 401]:
                        print(f"  ✓ {route} - Protected (redirects)")
                    else:
                        errors.append(f"{route} returned {response.status_code}")
                        print(f"  ✗ {route} - Status: {response.status_code}")
                except Exception as e:
                    errors.append(f"{route}: {e}")
                    print(f"  ✗ {route} - Error: {e}")

            # Test 6: Template rendering issues
            print("\n[TEST 6] Template Rendering...")
            template_errors = []

            # Test each template individually
            templates_to_test = [
                'beach/map.html',
                'beach/customers.html',
                'beach/reservations.html'
            ]

            from flask import render_template_string, render_template

            for template in templates_to_test:
                try:
                    # Try to render template with minimal context
                    with app.test_request_context():
                        from models.zone import get_all_zones
                        from models.furniture import get_all_furniture

                        if 'map' in template:
                            render_template(template, zones=get_all_zones(), furniture=get_all_furniture())
                        else:
                            render_template(template)
                        print(f"  ✓ {template} renders OK")
                except Exception as e:
                    template_errors.append(f"{template}: {str(e)}")
                    print(f"  ✗ {template} - Error: {e}")
                    errors.append(f"Template {template}: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\n✗ FOUND {len(errors)} ERROR(S):\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
        return False
    else:
        print("\n✓ ALL TESTS PASSED!")
        return True

if __name__ == '__main__':
    success = test_app()
    sys.exit(0 if success else 1)
