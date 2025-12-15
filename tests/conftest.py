"""
Pytest configuration and fixtures.
Ensures tests use an isolated test database, not the production database.
"""

import os
import pytest
import tempfile

# Set test database path BEFORE importing app
# This ensures all tests use an isolated database
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), 'purobeach_test.db')
os.environ['DATABASE_PATH'] = TEST_DB_PATH


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Set up test environment before any tests run."""
    # Ensure test database path is set
    os.environ['DATABASE_PATH'] = TEST_DB_PATH
    os.environ['FLASK_ENV'] = 'test'

    yield

    # Cleanup: remove test database after all tests
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass  # Windows may have file locked


@pytest.fixture
def app():
    """Create test application with isolated database."""
    from app import create_app
    from database import init_db

    # Ensure test database path
    os.environ['DATABASE_PATH'] = TEST_DB_PATH

    app = create_app('test')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DATABASE_PATH'] = TEST_DB_PATH

    with app.app_context():
        init_db()
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(app, client):
    """Create authenticated test client."""
    with app.app_context():
        # Login as admin
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
    return client
