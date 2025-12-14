"""
Database tests.
Tests database initialization and data integrity.
"""

import sys
import os

# Change to project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

import pytest
from app import create_app
from database import get_db


def test_database_tables():
    """Test that all required tables exist."""
    app = create_app()

    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        # Required tables
        required_tables = [
            'users', 'roles', 'permissions', 'role_permissions',
            'beach_zones', 'beach_furniture', 'beach_furniture_types',
            'beach_customers', 'beach_reservations', 'beach_reservation_states',
            'hotel_guests', 'beach_config'
        ]

        for table in required_tables:
            assert table in tables, f"Table {table} should exist"


def test_seed_data():
    """Test that seed data was created correctly."""
    app = create_app()

    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Check admin user exists
        cursor.execute("SELECT username FROM users WHERE username='admin'")
        admin = cursor.fetchone()
        assert admin is not None, "Admin user should exist"

        # Check roles exist
        cursor.execute("SELECT COUNT(*) FROM roles")
        role_count = cursor.fetchone()[0]
        assert role_count >= 4, "Should have at least 4 roles"

        # Check permissions exist
        cursor.execute("SELECT COUNT(*) FROM permissions")
        perm_count = cursor.fetchone()[0]
        assert perm_count >= 30, "Should have at least 30 permissions"

        # Check beach zones exist
        cursor.execute("SELECT COUNT(*) FROM beach_zones")
        zone_count = cursor.fetchone()[0]
        assert zone_count >= 2, "Should have at least 2 zones"

        # Check furniture types exist (seed data)
        cursor.execute("SELECT COUNT(*) FROM beach_furniture_types")
        furniture_type_count = cursor.fetchone()[0]
        assert furniture_type_count >= 2, "Should have at least 2 furniture types"


if __name__ == '__main__':
    test_database_tables()
    test_seed_data()
    print("\n[SUCCESS] All database tests passed!")
