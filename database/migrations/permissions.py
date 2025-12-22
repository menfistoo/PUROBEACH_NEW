"""
Permissions migrations.
Menu items and permission additions.
"""

from database.connection import get_db


def migrate_add_furniture_types_menu() -> bool:
    """
    Migration: Add 'Tipos de Mobiliario' menu permission.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM permissions WHERE code = 'beach.furniture_types.view'")
    if cursor.fetchone():
        print("Menu permission 'beach.furniture_types.view' already exists.")
        return False

    print("Adding furniture types menu permission...")

    try:
        cursor.execute("SELECT id FROM permissions WHERE code = 'menu.config'")
        parent_row = cursor.fetchone()
        if not parent_row:
            print("ERROR: Parent menu 'menu.config' not found!")
            return False
        menu_config_id = parent_row[0]

        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('beach.furniture_types.view', 'Tipos de Mobiliario', 'config', 1, 22, 'fa-shapes', '/beach/config/furniture-types', menu_config_id))

        new_perm_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES (?, ?, ?, 0)
        ''', ('beach.furniture_types.manage', 'Gestionar Tipos Mobiliario', 'config'))

        manage_perm_id = cursor.lastrowid

        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_role_id = admin_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, new_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, manage_perm_id))

        cursor.execute("SELECT id FROM roles WHERE name = 'manager'")
        manager_row = cursor.fetchone()
        if manager_row:
            manager_role_id = manager_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, new_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, manage_perm_id))

        db.commit()
        print("Menu permission added successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_add_map_edit_permission() -> bool:
    """
    Migration: Add beach.map.edit permission for interactive map editing.

    This permission allows staff/managers to reposition furniture on the map.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if permission already exists
    cursor.execute('''
        SELECT id FROM permissions WHERE code = 'beach.map.edit'
    ''')
    if cursor.fetchone():
        print("Migration already applied - beach.map.edit permission exists.")
        return False

    print("Applying add_map_edit_permission migration...")

    try:
        # Add the permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES ('beach.map.edit', 'Editar Posiciones Mapa', 'operations', 0)
        ''')
        perm_id = cursor.lastrowid
        print(f"  Created permission: beach.map.edit (id: {perm_id})")

        # Assign to manager role
        cursor.execute("SELECT id FROM roles WHERE name = 'manager'")
        manager_row = cursor.fetchone()
        if manager_row:
            cursor.execute('''
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (manager_row['id'], perm_id))
            print("  Assigned to manager role")

        # Assign to staff role
        cursor.execute("SELECT id FROM roles WHERE name = 'staff'")
        staff_row = cursor.fetchone()
        if staff_row:
            cursor.execute('''
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (staff_row['id'], perm_id))
            print("  Assigned to staff role")

        db.commit()
        print("Migration add_map_edit_permission applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_add_map_editor_permission() -> bool:
    """
    Migration: Add menu item and permission for Map Editor in config.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM permissions WHERE code = 'beach.map_editor.view'")
    if cursor.fetchone():
        print("Map editor permission already exists.")
        return False

    print("Adding map editor permission...")

    try:
        # Find parent menu (config)
        cursor.execute("SELECT id FROM permissions WHERE code = 'menu.config'")
        parent_row = cursor.fetchone()
        if not parent_row:
            print("ERROR: Parent menu 'menu.config' not found!")
            return False
        menu_config_id = parent_row[0]

        # Add menu permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('beach.map_editor.view', 'Editor de Mapa', 'config', 1, 15, 'fa-map', '/beach/config/map-editor', menu_config_id))

        menu_perm_id = cursor.lastrowid

        # Add edit permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES (?, ?, ?, 0)
        ''', ('beach.map_editor.edit', 'Editar Mapa', 'config'))

        edit_perm_id = cursor.lastrowid

        # Assign to admin role
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_role_id = admin_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, menu_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, edit_perm_id))

        # Assign to manager role
        cursor.execute("SELECT id FROM roles WHERE name = 'manager'")
        manager_row = cursor.fetchone()
        if manager_row:
            manager_role_id = manager_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, menu_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, edit_perm_id))

        db.commit()
        print("Map editor permission added successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
