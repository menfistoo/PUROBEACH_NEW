"""
Furniture model tests.
Tests for furniture CRUD operations and helper functions.
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
from models.furniture import (
    get_all_furniture,
    get_furniture_by_id,
    create_furniture,
    update_furniture,
    delete_furniture,
    get_furniture_types,
    get_next_number_by_prefix
)


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestFurnitureModel:
    """Tests for furniture model functions."""

    def test_get_all_furniture(self, app):
        """Test getting all furniture items."""
        with app.app_context():
            furniture = get_all_furniture()
            assert isinstance(furniture, list)

    def test_get_furniture_types(self, app):
        """Test getting furniture types."""
        with app.app_context():
            types = get_furniture_types()
            assert isinstance(types, list)
            assert len(types) >= 2, "Should have at least 2 furniture types"

            # Check structure
            if types:
                assert 'id' in types[0]
                assert 'type_code' in types[0]
                assert 'display_name' in types[0]

    def test_create_furniture(self, app):
        """Test creating a furniture item."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get a valid zone_id
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()
            assert zone is not None, "Need at least one zone"
            zone_id = zone['id']

            # Create furniture
            furniture_id = create_furniture(
                number='TEST1',
                zone_id=zone_id,
                furniture_type='hamaca',
                capacity=2,
                position_x=100,
                position_y=100,
                rotation=0,
                width=60,
                height=40,
                features='test_feature'
            )

            assert furniture_id is not None
            assert furniture_id > 0

            # Verify it was created
            furniture = get_furniture_by_id(furniture_id)
            assert furniture is not None
            assert furniture['number'] == 'TEST1'
            assert furniture['capacity'] == 2
            assert furniture['position_x'] == 100

            # Cleanup
            delete_furniture(furniture_id)

    def test_update_furniture(self, app):
        """Test updating a furniture item."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get a valid zone_id
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()
            zone_id = zone['id']

            # Create furniture
            furniture_id = create_furniture(
                number='TEST_UPDATE',
                zone_id=zone_id,
                furniture_type='hamaca',
                capacity=2
            )

            # Update it
            updated = update_furniture(
                furniture_id,
                number='TEST_UPDATED',
                zone_id=zone_id,
                capacity=4,
                position_x=200,
                position_y=200
            )

            assert updated == True

            # Verify update
            furniture = get_furniture_by_id(furniture_id)
            assert furniture['number'] == 'TEST_UPDATED'
            assert furniture['capacity'] == 4
            assert furniture['position_x'] == 200

            # Cleanup
            delete_furniture(furniture_id)

    def test_delete_furniture(self, app):
        """Test deleting a furniture item (soft delete)."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get a valid zone_id
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()
            zone_id = zone['id']

            # Create furniture
            furniture_id = create_furniture(
                number='TEST_DELETE',
                zone_id=zone_id,
                furniture_type='hamaca',
                capacity=2
            )

            # Delete it (soft delete)
            deleted = delete_furniture(furniture_id)
            assert deleted == True

            # Verify soft deletion (active = 0)
            cursor.execute("SELECT active FROM beach_furniture WHERE id = ?", (furniture_id,))
            row = cursor.fetchone()
            assert row is not None
            assert row['active'] == 0

            # Hard delete for cleanup
            cursor.execute("DELETE FROM beach_furniture WHERE id = ?", (furniture_id,))
            db.commit()

    def test_get_next_number_by_prefix(self, app):
        """Test sequential number generation by prefix."""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get a valid zone_id
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()
            zone_id = zone['id']

            # Create some furniture with prefix 'X'
            ids_created = []
            for i in range(1, 4):
                fid = create_furniture(
                    number=f'X{i}',
                    zone_id=zone_id,
                    furniture_type='hamaca',
                    capacity=2
                )
                ids_created.append(fid)

            # Test next number
            next_num = get_next_number_by_prefix('X')
            assert next_num == 'X4', f"Expected X4, got {next_num}"

            # Cleanup
            for fid in ids_created:
                delete_furniture(fid)

    def test_get_next_number_by_prefix_empty(self, app):
        """Test sequential number generation with no existing items."""
        with app.app_context():
            # Use a prefix that doesn't exist
            next_num = get_next_number_by_prefix('ZZZ')
            assert next_num == 'ZZZ1', f"Expected ZZZ1, got {next_num}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
