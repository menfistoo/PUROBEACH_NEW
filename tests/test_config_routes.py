"""
Config routes tests.
Tests for beach configuration routes (furniture, zones, types, etc).
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


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestConfigRoutesRequireAuth:
    """Tests that config routes require authentication."""

    def test_furniture_list_requires_auth(self, client):
        """Test that furniture list requires authentication."""
        response = client.get('/beach/config/furniture')
        assert response.status_code == 302  # Redirect to login

    def test_furniture_create_requires_auth(self, client):
        """Test that furniture create requires authentication."""
        response = client.get('/beach/config/furniture/create')
        assert response.status_code == 302

    def test_zones_list_requires_auth(self, client):
        """Test that zones list requires authentication."""
        response = client.get('/beach/config/zones')
        assert response.status_code == 302

    def test_furniture_types_requires_auth(self, client):
        """Test that furniture types list requires authentication."""
        response = client.get('/beach/config/furniture-types')
        assert response.status_code == 302

    def test_preferences_requires_auth(self, client):
        """Test that preferences list requires authentication."""
        response = client.get('/beach/config/preferences')
        assert response.status_code == 302

    def test_tags_requires_auth(self, client):
        """Test that tags list requires authentication."""
        response = client.get('/beach/config/tags')
        assert response.status_code == 302


class TestConfigRoutesExist:
    """Tests that config route endpoints exist."""

    def test_furniture_routes_exist(self, app):
        """Test that furniture routes are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/beach/config/furniture' in rules
        assert '/beach/config/furniture/create' in rules

    def test_zone_routes_exist(self, app):
        """Test that zone routes are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/beach/config/zones' in rules
        assert '/beach/config/zones/create' in rules

    def test_furniture_type_routes_exist(self, app):
        """Test that furniture type routes are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/beach/config/furniture-types' in rules

    def test_preference_routes_exist(self, app):
        """Test that preference routes are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/beach/config/preferences' in rules

    def test_tag_routes_exist(self, app):
        """Test that tag routes are registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/beach/config/tags' in rules


class TestFurnitureModelIntegration:
    """Integration tests for furniture functionality."""

    def test_create_and_delete_furniture(self, app):
        """Test creating and deleting furniture through the model."""
        from models.furniture import (
            create_furniture, delete_furniture, get_furniture_by_id
        )

        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get valid zone
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()

            if zone:
                # Create
                furniture_id = create_furniture(
                    number='INTEGRATION_TEST',
                    zone_id=zone['id'],
                    furniture_type='hamaca',
                    capacity=2
                )

                assert furniture_id is not None

                # Verify exists
                furniture = get_furniture_by_id(furniture_id)
                assert furniture is not None
                assert furniture['number'] == 'INTEGRATION_TEST'

                # Delete (soft)
                delete_furniture(furniture_id)

                # Hard delete for cleanup
                cursor.execute("DELETE FROM beach_furniture WHERE id = ?", (furniture_id,))
                db.commit()


class TestDuplicationLogic:
    """Tests for furniture duplication logic."""

    def test_next_number_by_prefix(self, app):
        """Test that next number by prefix works correctly."""
        from models.furniture import get_next_number_by_prefix, create_furniture, delete_furniture

        with app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Get valid zone
            cursor.execute("SELECT id FROM beach_zones LIMIT 1")
            zone = cursor.fetchone()

            if zone:
                # Create test furniture
                ids = []
                for num in ['Y1', 'Y2', 'Y5']:
                    fid = create_furniture(
                        number=num,
                        zone_id=zone['id'],
                        furniture_type='hamaca',
                        capacity=2
                    )
                    ids.append(fid)

                # Test next number (should be Y6 since Y5 is max)
                next_num = get_next_number_by_prefix('Y')
                assert next_num == 'Y6', f"Expected Y6, got {next_num}"

                # Cleanup
                for fid in ids:
                    cursor.execute("DELETE FROM beach_furniture WHERE id = ?", (fid,))
                db.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
