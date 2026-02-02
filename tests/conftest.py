"""
Pytest configuration and fixtures.
Ensures tests use an isolated test database, not the production database.
"""

import os
import time
import pytest
import tempfile

# Use a unique database path per test session to avoid lock conflicts on Windows.
# The PID+timestamp ensures no collisions with other pytest processes.
_session_id = f'{os.getpid()}_{int(time.time())}'
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), f'purobeach_test_{_session_id}.db')
os.environ['DATABASE_PATH'] = TEST_DB_PATH


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Set up test environment before any tests run."""
    # Ensure test database path is set
    os.environ['DATABASE_PATH'] = TEST_DB_PATH
    os.environ['FLASK_ENV'] = 'test'

    yield

    # Cleanup: remove test database after all tests
    for suffix in ['', '-wal', '-shm']:
        path = TEST_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass  # Windows may have file locked


@pytest.fixture
def app():
    """Create test application with isolated database."""
    from app import create_app
    from database import init_db
    from database.migrations import run_all_migrations

    # Ensure test database path
    os.environ['DATABASE_PATH'] = TEST_DB_PATH

    app = create_app('test')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DATABASE_PATH'] = TEST_DB_PATH

    with app.app_context():
        init_db()
        # Run migrations to create waitlist and other feature tables
        run_all_migrations()
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(app, client):
    """Create authenticated test client with admin session."""
    # Login as admin (password matches database/seed.py)
    client.post('/login', data={
        'username': 'admin',
        'password': 'PuroAdmin2026!'
    }, follow_redirects=True)
    return client
