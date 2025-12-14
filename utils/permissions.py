"""
Permission checking and caching utilities.
Provides functions to load and check user permissions.
"""

from database import get_db
from models.role import get_role_permissions


def load_user_permissions(user_id: int) -> set:
    """
    Load all permissions for a user based on their role.

    Args:
        user_id: User ID

    Returns:
        Set of permission codes
    """
    db = get_db()
    cursor = db.cursor()

    # Get user's role
    cursor.execute('SELECT role_id FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()

    if not row or not row['role_id']:
        return set()

    # Get all permissions for the role
    permissions = get_role_permissions(row['role_id'])

    return {perm['code'] for perm in permissions}


def has_permission(user, permission_code: str) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user: User object (Flask-Login)
        permission_code: Permission code to check

    Returns:
        True if user has permission
    """
    user_permissions = load_user_permissions(user.id)
    return permission_code in user_permissions


def get_menu_items(user) -> list:
    """
    Generate hierarchical navigation menu based on user permissions.

    Args:
        user: User object (Flask-Login)

    Returns:
        List of parent menu dicts with children lists
    """
    user_permissions = load_user_permissions(user.id)

    db = get_db()
    cursor = db.cursor()

    # Get parent menu items (no parent_permission_id, no URL)
    cursor.execute('''
        SELECT * FROM permissions
        WHERE is_menu_item = 1 AND active = 1 AND parent_permission_id IS NULL
        ORDER BY menu_order
    ''')

    menu_structure = []
    for parent_row in cursor.fetchall():
        parent = dict(parent_row)

        # Get children for this parent
        cursor.execute('''
            SELECT * FROM permissions
            WHERE is_menu_item = 1 AND active = 1 AND parent_permission_id = ?
            ORDER BY menu_order
        ''', (parent['id'],))

        children = []
        for child_row in cursor.fetchall():
            child = dict(child_row)
            if child['code'] in user_permissions:
                children.append({
                    'code': child['code'],
                    'name': child['name'],
                    'icon': child['menu_icon'],
                    'url': child['menu_url'],
                    'module': child['module']
                })

        # Only include parent if user has access to at least one child
        if children:
            menu_structure.append({
                'id': parent['id'],
                'code': parent['code'],
                'name': parent['name'],
                'icon': parent['menu_icon'],
                'module': parent['module'],
                'children': children
            })

    return menu_structure


def cache_user_permissions(user_id: int):
    """
    Cache user permissions in flask g object.

    Args:
        user_id: User ID
    """
    from flask import g
    g.user_permissions = load_user_permissions(user_id)
