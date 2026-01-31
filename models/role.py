"""
Role and permission data access functions.
Handles role CRUD operations and role-permission assignments.
"""

from database import get_db


def get_all_roles(active_only: bool = True) -> list:
    """
    Get all roles.

    Args:
        active_only: If True, only return active roles

    Returns:
        List of role dicts with permission count
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT r.*,
                   COUNT(rp.permission_id) as permission_count,
                   (SELECT COUNT(*) FROM users WHERE role_id = r.id AND active = 1) as user_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
        '''

        if active_only:
            query += ' WHERE r.active = 1'

        query += ' GROUP BY r.id ORDER BY r.id'

        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_role_by_id(role_id: int) -> dict:
    """
    Get role by ID.

    Args:
        role_id: Role ID

    Returns:
        Role dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles WHERE id = ?', (role_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_role_by_name(name: str) -> dict:
    """
    Get role by name.

    Args:
        name: Role name

    Returns:
        Role dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_role_permissions(role_id: int) -> list:
    """
    Get all permissions assigned to a role.

    Args:
        role_id: Role ID

    Returns:
        List of permission dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = ?
            ORDER BY p.module, p.code
        ''', (role_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_role(name: str, display_name: str, description: str = None, is_system: bool = False) -> int:
    """
    Create new role.

    Args:
        name: Unique role name
        display_name: Display name for UI
        description: Role description
        is_system: Whether role is system-managed

    Returns:
        New role ID
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO roles (name, display_name, description, is_system)
            VALUES (?, ?, ?, ?)
        ''', (name, display_name, description, 1 if is_system else 0))

        conn.commit()
        return cursor.lastrowid


def update_role(role_id: int, **kwargs) -> bool:
    """
    Update role fields.

    Args:
        role_id: Role ID to update
        **kwargs: Fields to update (display_name, description, active)

    Returns:
        True if updated successfully
    """
    allowed_fields = ['display_name', 'description', 'active']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(role_id)
    query = f'UPDATE roles SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()

        return cursor.rowcount > 0


def assign_permission(role_id: int, permission_id: int) -> bool:
    """
    Assign permission to role.

    Args:
        role_id: Role ID
        permission_id: Permission ID

    Returns:
        True if assigned successfully (or already assigned)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, permission_id))
            conn.commit()
            return True
        except Exception:
            # Already exists
            return True


def revoke_permission(role_id: int, permission_id: int) -> bool:
    """
    Revoke permission from role.

    Args:
        role_id: Role ID
        permission_id: Permission ID

    Returns:
        True if revoked successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM role_permissions
            WHERE role_id = ? AND permission_id = ?
        ''', (role_id, permission_id))

        conn.commit()
        return cursor.rowcount > 0


def has_users(role_id: int) -> bool:
    """
    Check if role has any users assigned.

    Args:
        role_id: Role ID

    Returns:
        True if role has active users
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM users
            WHERE role_id = ? AND active = 1
        ''', (role_id,))

        row = cursor.fetchone()
        return row['count'] > 0


def bulk_set_permissions(role_id: int, permission_ids: list) -> dict:
    """
    Replace all permissions for a role with the given set.

    Args:
        role_id: Role ID
        permission_ids: List of permission IDs to assign

    Returns:
        Dict with 'added' and 'removed' lists of permission dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        conn.execute('BEGIN IMMEDIATE')

        # Get current permissions
        cursor.execute('''
            SELECT p.id, p.code, p.name
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = ?
        ''', (role_id,))
        current = {row['id']: dict(row) for row in cursor.fetchall()}

        current_ids = set(current.keys())
        new_ids = set(permission_ids)

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        # Remove revoked permissions
        if to_remove:
            placeholders = ','.join('?' * len(to_remove))
            cursor.execute(f'''
                DELETE FROM role_permissions
                WHERE role_id = ? AND permission_id IN ({placeholders})
            ''', [role_id] + list(to_remove))

        # Add new permissions
        for perm_id in to_add:
            cursor.execute('''
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, perm_id))

        # Get details of added permissions for audit
        added_details = []
        if to_add:
            placeholders = ','.join('?' * len(to_add))
            cursor.execute(f'SELECT id, code, name FROM permissions WHERE id IN ({placeholders})',
                          list(to_add))
            added_details = [dict(row) for row in cursor.fetchall()]

        removed_details = [current[pid] for pid in to_remove]

        conn.commit()

        return {'added': added_details, 'removed': removed_details}


def delete_role(role_id: int) -> bool:
    """
    Delete a custom role.

    Args:
        role_id: Role ID to delete

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM roles WHERE id = ? AND is_system = 0', (role_id,))
        conn.commit()
        return cursor.rowcount > 0
