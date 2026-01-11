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


def migrate_zones_to_furniture_manager() -> bool:
    """
    Migration: Remove zones from sidebar menu (integrated into furniture-manager).

    This migration removes the 'beach.zones.view' permission from the sidebar
    menu since zones are now accessed through the Furniture Manager tabs.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if zones.view is still a menu item
    cursor.execute('''
        SELECT id, is_menu_item, menu_url FROM permissions
        WHERE code = 'beach.zones.view'
    ''')
    row = cursor.fetchone()

    if not row:
        print("Permission 'beach.zones.view' not found, creating as non-menu...")
        try:
            cursor.execute('''
                INSERT INTO permissions (code, name, module, is_menu_item)
                VALUES ('beach.zones.view', 'Ver Zonas', 'config', 0)
            ''')
            db.commit()
            print("Created beach.zones.view as non-menu permission")
            return True
        except Exception as e:
            db.rollback()
            print(f"Failed to create permission: {e}")
            return False

    if row['is_menu_item'] == 0:
        print("Zones permission already converted to non-menu item.")
        return False

    print("Converting zones permission from menu item to non-menu...")

    try:
        cursor.execute('''
            UPDATE permissions SET
                is_menu_item = 0,
                menu_order = NULL,
                menu_icon = NULL,
                menu_url = NULL,
                parent_permission_id = NULL
            WHERE code = 'beach.zones.view'
        ''')
        db.commit()
        print("Zones permission converted to non-menu successfully!")
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


def migrate_add_payment_reconciliation_permission() -> bool:
    """
    Add payment reconciliation report permission.

    Creates:
    - beach.reports.payment_reconciliation permission
    - Assigns to admin and manager roles
    - Adds to menu under Informes section

    Returns:
        True if migration applied, False if already exists
    """
    db = get_db()
    cursor = db.cursor()

    # Check if already exists
    cursor.execute(
        "SELECT id FROM permissions WHERE code = ?",
        ('beach.reports.payment_reconciliation',)
    )
    if cursor.fetchone():
        print("Payment reconciliation permission already exists")
        return False

    print("Adding payment reconciliation permission...")

    try:
        # Find or create Informes parent menu
        cursor.execute(
            "SELECT id FROM permissions WHERE code = ?",
            ('menu.reports',)
        )
        parent_row = cursor.fetchone()

        if not parent_row:
            # Create parent menu item for reports (values from seed.py)
            cursor.execute("""
                INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('menu.reports', 'Informes', 'reports', 1, 40, 'fa-chart-line'))
            parent_id = cursor.lastrowid
            print("  Created parent menu 'Informes'")
        else:
            parent_id = parent_row[0]
            print("  Found existing parent menu 'Informes'")

        # Create the permission
        cursor.execute("""
            INSERT INTO permissions (
                code, name, module, is_menu_item,
                menu_order, menu_icon, menu_url, parent_permission_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'beach.reports.payment_reconciliation',
            'Conciliación de Pagos',
            'reports',
            1,
            61,
            'fa-cash-register',
            '/beach/reports/payment-reconciliation',
            parent_id
        ))

        permission_id = cursor.lastrowid
        print(f"  Created permission: beach.reports.payment_reconciliation (id: {permission_id})")

        # Look up role IDs once
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_row = cursor.fetchone()
        admin_role_id = admin_row[0] if admin_row else None

        cursor.execute("SELECT id FROM roles WHERE name = 'manager'")
        manager_row = cursor.fetchone()
        manager_role_id = manager_row[0] if manager_row else None

        # Assign permission and parent menu to roles
        for role_name, role_id in [('admin', admin_role_id), ('manager', manager_role_id)]:
            if role_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                    VALUES (?, ?)
                """, (role_id, permission_id))
                cursor.execute("""
                    INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                    VALUES (?, ?)
                """, (role_id, parent_id))
                print(f"  Assigned to {role_name} role")

        db.commit()
        print("Payment reconciliation permission created successfully")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
