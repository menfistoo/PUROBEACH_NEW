"""Add missing map editor permissions"""
from app import create_app
from database import get_db

app = create_app()

with app.app_context():
    db = get_db()
    cursor = db.cursor()

    # Get admin role ID
    cursor.execute('SELECT id FROM roles WHERE name = ?', ('admin',))
    admin_role = cursor.fetchone()

    if not admin_role:
        print('ERROR: Admin role not found')
        exit(1)

    admin_role_id = admin_role['id']

    # Create map editor permissions
    permissions = [
        ('beach.config.map_editor.view', 'Ver Editor de Mapa', 'Ver y usar el editor de mapa de zonas'),
        ('beach.config.map_editor.edit', 'Editar Mapa', 'Editar posiciones de mobiliario en el mapa'),
    ]

    for code, name, description in permissions:
        # Check if permission exists
        cursor.execute('SELECT id FROM permissions WHERE code = ?', (code,))
        existing = cursor.fetchone()

        if existing:
            print(f'Permission {code} already exists')
            continue

        # Create permission
        cursor.execute('''
            INSERT INTO permissions (code, name, description, module, is_menu_item)
            VALUES (?, ?, ?, 'beach', 0)
        ''', (code, name, description))

        perm_id = cursor.lastrowid
        print(f'[OK] Created permission: {code}')

        # Grant to admin role
        cursor.execute('''
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (?, ?)
        ''', (admin_role_id, perm_id))

        print(f'[OK] Granted {code} to admin role')

    db.commit()
    print('\n=== Map editor permissions fixed ===')
