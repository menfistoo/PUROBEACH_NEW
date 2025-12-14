"""
Template rendering tests.
Tests that all templates render without errors.
"""

import sys
import os

# Change to project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

import pytest
from app import create_app
from flask import render_template


def test_all_templates():
    """Test that all templates render correctly."""
    app = create_app()
    errors = []

    with app.app_context():
        from models.zone import get_all_zones
        from models.furniture import get_all_furniture
        from models.user import get_all_users
        from models.role import get_all_roles
        from blueprints.auth.forms import LoginForm

        templates = [
            ('beach/map.html', {'zones': get_all_zones(), 'furniture': get_all_furniture()}),
            ('beach/customers.html', {}),
            ('beach/reservations.html', {}),
            ('admin/dashboard.html', {
                'stats': {
                    'total_users': 1,
                    'active_users': 1,
                    'total_roles': 4,
                    'active_reservations': 0
                }
            }),
            ('admin/users.html', {
                'users': get_all_users(),
                'roles': get_all_roles(),
                'role_filter': '',
                'active_filter': '',
                'search': ''
            }),
            ('admin/roles.html', {'roles': get_all_roles()}),
            ('errors/404.html', {}),
            ('errors/500.html', {}),
            ('errors/403.html', {}),
        ]

        for template, context in templates:
            try:
                with app.test_request_context():
                    render_template(template, **context)
                print(f'[OK] {template}')
            except Exception as e:
                errors.append((template, str(e)))
                print(f'[ERROR] {template}: {e}')

    assert len(errors) == 0, f"Template errors: {errors}"


if __name__ == '__main__':
    test_all_templates()
    print("\n[SUCCESS] All template tests passed!")
