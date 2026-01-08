"""
Waitlist migrations.
Creates the beach_waitlist table for interest registration.
"""

from database.connection import get_db


def migrate_waitlist_table() -> bool:
    """
    Create the beach_waitlist table.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table already exists
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_waitlist'
    ''')

    if cursor.fetchone():
        print("  beach_waitlist table already exists, skipping")
        return False

    print("Creating beach_waitlist table...")

    cursor.execute('''
        CREATE TABLE beach_waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            external_name TEXT,
            external_phone TEXT,
            requested_date DATE NOT NULL,
            num_people INTEGER NOT NULL DEFAULT 1,
            preferred_zone_id INTEGER REFERENCES beach_zones(id),
            preferred_furniture_type_id INTEGER REFERENCES beach_furniture_types(id),
            time_preference TEXT CHECK(time_preference IN ('morning', 'afternoon', 'all_day', 'manana', 'tarde', 'mediodia', 'todo_el_dia')),
            reservation_type TEXT DEFAULT 'incluido' CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo')),
            package_id INTEGER REFERENCES beach_packages(id),
            notes TEXT,
            status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'contacted', 'converted', 'declined', 'no_answer', 'expired')),
            converted_reservation_id INTEGER REFERENCES beach_reservations(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        )
    ''')

    # Create indexes
    cursor.execute('''
        CREATE INDEX idx_waitlist_date_status
        ON beach_waitlist(requested_date, status)
    ''')

    cursor.execute('''
        CREATE INDEX idx_waitlist_customer
        ON beach_waitlist(customer_id)
    ''')

    db.commit()
    print("  beach_waitlist table created successfully")
    return True


def migrate_waitlist_permissions() -> bool:
    """
    Add waitlist permissions.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # (code, name, description, module, is_menu)
    permissions = [
        ('beach.waitlist.view', 'Lista de Espera', 'Ver lista de espera', 'beach', 0),
        ('beach.waitlist.create', 'Crear Lista Espera', 'Agregar a lista de espera', 'beach', 0),
        ('beach.waitlist.manage', 'Gestionar Lista Espera', 'Gestionar lista de espera', 'beach', 0),
    ]

    added = 0
    for code, name, description, module, is_menu in permissions:
        cursor.execute('SELECT id FROM permissions WHERE code = ?', (code,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO permissions (code, name, description, module, is_menu_item)
                VALUES (?, ?, ?, ?, ?)
            ''', (code, name, description, module, is_menu))
            added += 1

    if added > 0:
        # Grant to admin and manager roles
        cursor.execute('SELECT id FROM roles WHERE name IN ("admin", "manager")')
        role_ids = [row[0] for row in cursor.fetchall()]

        for role_id in role_ids:
            for code, _, _, _, _ in permissions:
                cursor.execute('SELECT id FROM permissions WHERE code = ?', (code,))
                perm = cursor.fetchone()
                if perm:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (?, ?)
                    ''', (role_id, perm[0]))

        db.commit()
        print(f"  Added {added} waitlist permissions")
        return True

    print("  Waitlist permissions already exist, skipping")
    return False


def migrate_waitlist_external_fields() -> bool:
    """
    Add external_name and external_phone columns for external guests
    who don't have a customer record yet.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(beach_waitlist)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'external_name' in columns:
        print("  External fields already exist, skipping")
        return False

    print("Adding external_name and external_phone columns...")

    # Add columns
    cursor.execute('ALTER TABLE beach_waitlist ADD COLUMN external_name TEXT')
    cursor.execute('ALTER TABLE beach_waitlist ADD COLUMN external_phone TEXT')

    db.commit()
    print("  External fields added successfully")
    return True


# Export migrations
__all__ = [
    'migrate_waitlist_table',
    'migrate_waitlist_permissions',
    'migrate_waitlist_external_fields',
]
