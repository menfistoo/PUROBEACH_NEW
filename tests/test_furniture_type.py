"""
Furniture Type model tests.
Tests for furniture type CRUD and auto-numbering functions.
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
from models.furniture_type import (
    get_all_furniture_types,
    get_furniture_type_by_id,
    get_furniture_type_by_code,
    create_furniture_type,
    update_furniture_type,
    delete_furniture_type,
    get_next_number_for_type,
    get_furniture_type_svg
)


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


class TestFurnitureTypeModel:
    """Tests for furniture type model functions."""

    def test_get_all_furniture_types(self, app):
        """Test getting all furniture types."""
        with app.app_context():
            types = get_all_furniture_types()
            assert isinstance(types, list)
            assert len(types) >= 2, "Should have at least 2 furniture types (seed data)"

    def test_get_furniture_type_by_id(self, app):
        """Test getting furniture type by ID."""
        with app.app_context():
            types = get_all_furniture_types()
            if types:
                ftype = get_furniture_type_by_id(types[0]['id'])
                assert ftype is not None
                assert 'type_code' in ftype
                assert 'display_name' in ftype

    def test_get_furniture_type_by_code(self, app):
        """Test getting furniture type by code."""
        with app.app_context():
            # Test with known seed data codes
            hamaca = get_furniture_type_by_code('hamaca')
            if hamaca:
                assert hamaca['type_code'] == 'hamaca'
                assert hamaca['display_name'] is not None

    def test_create_furniture_type(self, app):
        """Test creating a new furniture type."""
        with app.app_context():
            type_id = create_furniture_type(
                type_code='test_type',
                display_name='Test Type',
                icon='fa-test',
                default_color='#FF0000',
                min_capacity=1,
                max_capacity=4,
                default_capacity=2,
                number_prefix='T'
            )

            assert type_id is not None
            assert type_id > 0

            # Verify creation
            ftype = get_furniture_type_by_id(type_id)
            assert ftype is not None
            assert ftype['type_code'] == 'test_type'
            assert ftype['display_name'] == 'Test Type'
            assert ftype['number_prefix'] == 'T'

            # Cleanup
            delete_furniture_type(type_id)

    def test_update_furniture_type(self, app):
        """Test updating a furniture type."""
        with app.app_context():
            from database import get_db
            db = get_db()
            cursor = db.cursor()

            # Create a type to update
            type_id = create_furniture_type(
                type_code='test_update_type',
                display_name='Before Update',
                min_capacity=1,
                max_capacity=2
            )

            # Update it (must include default_capacity between min and max)
            updated = update_furniture_type(
                type_id,
                display_name='After Update',
                min_capacity=2,
                max_capacity=6,
                default_capacity=4
            )

            assert updated == True

            # Verify update
            ftype = get_furniture_type_by_id(type_id)
            assert ftype['display_name'] == 'After Update'
            assert ftype['min_capacity'] == 2
            assert ftype['max_capacity'] == 6
            assert ftype['default_capacity'] == 4

            # Hard delete for cleanup
            cursor.execute("DELETE FROM beach_furniture_types WHERE id = ?", (type_id,))
            db.commit()

    def test_delete_furniture_type(self, app):
        """Test deleting a furniture type (soft delete)."""
        with app.app_context():
            from database import get_db
            db = get_db()
            cursor = db.cursor()

            # Create a type to delete
            type_id = create_furniture_type(
                type_code='test_delete_type',
                display_name='To Delete'
            )

            # Delete it (soft delete)
            deleted = delete_furniture_type(type_id)
            assert deleted == True

            # Verify soft deletion (active = 0)
            cursor.execute("SELECT active FROM beach_furniture_types WHERE id = ?", (type_id,))
            row = cursor.fetchone()
            assert row is not None
            assert row['active'] == 0

            # Hard delete for cleanup
            cursor.execute("DELETE FROM beach_furniture_types WHERE id = ?", (type_id,))
            db.commit()

    def test_get_next_number_for_type(self, app):
        """Test auto-numbering for furniture type."""
        with app.app_context():
            # Create a type with prefix
            type_id = create_furniture_type(
                type_code='test_numbering',
                display_name='Test Numbering',
                number_prefix='TN'
            )

            # Get next number (should be TN1 with no furniture)
            next_num = get_next_number_for_type(type_id)
            assert next_num.startswith('TN'), f"Expected TN prefix, got {next_num}"

            # Cleanup
            delete_furniture_type(type_id)

    def test_furniture_type_structure(self, app):
        """Test that furniture type has all expected fields."""
        with app.app_context():
            types = get_all_furniture_types()
            if types:
                ftype = types[0]
                expected_fields = [
                    'id', 'type_code', 'display_name', 'icon',
                    'min_capacity', 'max_capacity', 'default_capacity',
                    'map_shape', 'default_width', 'default_height',
                    'fill_color', 'stroke_color', 'number_prefix'
                ]

                for field in expected_fields:
                    assert field in ftype, f"Missing field: {field}"


class TestFurnitureTypeSVG:
    """Tests for SVG generation functions."""

    def test_get_furniture_type_svg_rounded_rect(self, app):
        """Test SVG generation for rounded rectangle."""
        with app.app_context():
            type_config = {
                'map_shape': 'rounded_rect',
                'default_width': 60,
                'default_height': 40,
                'border_radius': 8,
                'fill_color': '#A0522D',
                'stroke_color': '#654321'
            }

            svg = get_furniture_type_svg(type_config)
            assert svg is not None
            assert 'rect' in svg
            assert '#A0522D' in svg or 'A0522D' in svg

    def test_get_furniture_type_svg_circle(self, app):
        """Test SVG generation for circle."""
        with app.app_context():
            type_config = {
                'map_shape': 'circle',
                'default_width': 50,
                'default_height': 50,
                'fill_color': '#FF0000',
                'stroke_color': '#990000'
            }

            svg = get_furniture_type_svg(type_config)
            assert svg is not None
            assert 'circle' in svg

    def test_get_furniture_type_svg_ellipse(self, app):
        """Test SVG generation for ellipse."""
        with app.app_context():
            type_config = {
                'map_shape': 'ellipse',
                'default_width': 80,
                'default_height': 40,
                'fill_color': '#00FF00',
                'stroke_color': '#009900'
            }

            svg = get_furniture_type_svg(type_config)
            assert svg is not None
            assert 'ellipse' in svg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
