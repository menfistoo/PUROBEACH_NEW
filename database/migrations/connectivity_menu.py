"""
Connectivity audit menu item.
Adds an 'admin.connectivity.view' permission (menu item under Administración)
pointing to the connectivity drop audit page, granted to admin and manager roles.
"""

from database import get_db


def migrate_connectivity_menu() -> bool:
    """
    Migration: add the 'Cortes de conexión' admin menu item + permission.

    Returns:
        bool: True if applied, False if already applied
    """
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM permissions WHERE code = 'admin.connectivity.view'"
        ).fetchone()
        if existing:
            print("Connectivity menu permission already exists, skipping...")
            return False

        parent = conn.execute(
            "SELECT id FROM permissions WHERE code = 'menu.admin'"
        ).fetchone()
        parent_id = parent[0] if parent else None

        conn.execute('''
            INSERT INTO permissions
            (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES ('admin.connectivity.view', 'Cortes de conexión', 'admin', 1, 16,
                    'fa-wifi', '/beach/admin/connectivity', ?)
        ''', (parent_id,))

        # Grant to admin (role 1) and manager (role 2), matching other admin tools.
        for role_id in (1, 2):
            conn.execute('''
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                SELECT ?, id FROM permissions WHERE code = 'admin.connectivity.view'
            ''', (role_id,))

        conn.commit()
        print("Connectivity menu permission added successfully.")
        return True
