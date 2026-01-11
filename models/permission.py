"""
Permission data access functions.
Handles permission queries and menu generation.
"""

from database import get_db


def get_all_permissions(active_only: bool = True) -> list:
    """
    Get all permissions.

    Args:
        active_only: If True, only return active permissions

    Returns:
        List of permission dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM permissions'

        if active_only:
            query += ' WHERE active = 1'

        query += ' ORDER BY module, menu_order, code'

        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_permission_by_id(permission_id: int) -> dict:
    """
    Get permission by ID.

    Args:
        permission_id: Permission ID

    Returns:
        Permission dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM permissions WHERE id = ?', (permission_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_permission_by_code(code: str) -> dict:
    """
    Get permission by code.

    Args:
        code: Permission code (e.g., 'beach.map.view')

    Returns:
        Permission dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM permissions WHERE code = ?', (code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_menu_permissions() -> list:
    """
    Get permissions that should appear in navigation menu.

    Returns:
        List of menu permission dicts, ordered by menu_order
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM permissions
            WHERE is_menu_item = 1 AND active = 1
            ORDER BY menu_order
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_permissions_by_module(module: str, active_only: bool = True) -> list:
    """
    Get permissions for a specific module.

    Args:
        module: Module name ('admin', 'beach', 'api')
        active_only: If True, only return active permissions

    Returns:
        List of permission dicts for the module
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM permissions WHERE module = ?'

        if active_only:
            query += ' AND active = 1'

        query += ' ORDER BY code'

        cursor.execute(query, (module,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
