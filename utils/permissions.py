"""
Permission checking and caching utilities.
Provides functions to load and check user permissions.
"""

from flask import g
from database import get_db
from models.role import get_role_permissions


def load_user_permissions(user_id: int) -> set:
    """
    Load all permissions for a user based on their role.
    Caches result in flask.g for per-request reuse.

    Args:
        user_id: User ID

    Returns:
        Set of permission codes
    """
    # Return cached if available
    if hasattr(g, 'user_permissions') and g.user_permissions is not None:
        return g.user_permissions

    db = get_db()
    cursor = db.cursor()

    # Get user's role
    cursor.execute('SELECT role_id FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()

    if not row or not row['role_id']:
        g.user_permissions = set()
        return g.user_permissions

    # Get all permissions for the role
    permissions = get_role_permissions(row['role_id'])
    g.user_permissions = {perm['code'] for perm in permissions}

    return g.user_permissions


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
    Uses a single query instead of N+1 queries.
    Caches result in flask.g for per-request reuse.

    Args:
        user: User object (Flask-Login)

    Returns:
        List of parent menu dicts with children lists
    """
    # Return cached if available
    if hasattr(g, 'menu_items') and g.menu_items is not None:
        return g.menu_items

    user_permissions = load_user_permissions(user.id)

    db = get_db()
    cursor = db.cursor()

    # Single query: get all menu items at once
    cursor.execute('''
        SELECT id, code, name, menu_icon, menu_url, module,
               parent_permission_id, menu_order
        FROM permissions
        WHERE is_menu_item = 1 AND active = 1
        ORDER BY menu_order
    ''')

    all_items = [dict(row) for row in cursor.fetchall()]

    # Separate parents and children in Python
    parents = []
    children_by_parent = {}

    for item in all_items:
        if item['parent_permission_id'] is None:
            parents.append(item)
        else:
            parent_id = item['parent_permission_id']
            if parent_id not in children_by_parent:
                children_by_parent[parent_id] = []
            children_by_parent[parent_id].append(item)

    # Build menu structure filtered by permissions
    menu_structure = []
    for parent in parents:
        children = []
        for child in children_by_parent.get(parent['id'], []):
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

    g.menu_items = menu_structure
    return g.menu_items


def cache_user_permissions(user_id: int):
    """
    Cache user permissions in flask g object.

    Args:
        user_id: User ID
    """
    g.user_permissions = load_user_permissions(user_id)
