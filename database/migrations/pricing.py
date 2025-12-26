"""
Payment & Pricing System migrations.
Creates beach_packages table and updates minimum consumption policies.
"""

from database import get_db


def migrate_create_beach_packages():
    """
    Create beach_packages table for package pricing.

    Features:
    - Per-package or per-person pricing
    - Capacity constraints (min/standard/max)
    - Customer type and zone restrictions
    - Validity date ranges
    - Furniture types included

    Idempotent: Can be run multiple times safely.
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_packages'
    """)

    if cursor.fetchone():
        print("✓ beach_packages table already exists")
        return

    print("Creating beach_packages table...")

    cursor.execute('''
        CREATE TABLE beach_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            package_description TEXT,
            base_price REAL NOT NULL,
            price_type TEXT NOT NULL CHECK(price_type IN ('per_package', 'per_person')),
            min_people INTEGER NOT NULL DEFAULT 1,
            standard_people INTEGER NOT NULL DEFAULT 2,
            max_people INTEGER NOT NULL DEFAULT 4,
            furniture_types_included TEXT,
            customer_type TEXT CHECK(customer_type IN ('interno', 'externo', 'both')),
            zone_id INTEGER REFERENCES beach_zones(id),
            valid_from DATE,
            valid_until DATE,
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT valid_people_range CHECK(min_people <= standard_people AND standard_people <= max_people),
            CONSTRAINT valid_price CHECK(base_price > 0)
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX idx_packages_active ON beach_packages(active, display_order)')
    cursor.execute('CREATE INDEX idx_packages_customer_zone ON beach_packages(customer_type, zone_id)')
    cursor.execute('CREATE INDEX idx_packages_dates ON beach_packages(valid_from, valid_until)')

    db.commit()
    print("✓ beach_packages table created successfully")


def migrate_minimum_consumption_calculation_type():
    """
    Add calculation_type column to beach_minimum_consumption_policies.

    Allows policies to specify:
    - 'per_reservation': Fixed amount for entire reservation
    - 'per_person': Amount multiplied by number of guests

    Idempotent: Can be run multiple times safely.
    """
    db = get_db()
    cursor = db.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(beach_minimum_consumption_policies)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'calculation_type' in columns:
        print("✓ calculation_type column already exists in beach_minimum_consumption_policies")
        return

    print("Adding calculation_type to beach_minimum_consumption_policies...")

    cursor.execute('''
        ALTER TABLE beach_minimum_consumption_policies
        ADD COLUMN calculation_type TEXT DEFAULT 'per_reservation'
        CHECK(calculation_type IN ('per_reservation', 'per_person'))
    ''')

    # Create index for better query performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_min_consumption_priority
        ON beach_minimum_consumption_policies(priority_order, is_active)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_min_consumption_lookup
        ON beach_minimum_consumption_policies(furniture_type, customer_type, zone_id, is_active)
    ''')

    db.commit()
    print("✓ calculation_type column added successfully")


def migrate_reservations_pricing_fields():
    """
    Add pricing-related fields to beach_reservations table.

    New fields:
    - reservation_type: 'incluido', 'paquete', or 'consumo_minimo'
    - package_id: FK to beach_packages (if type='paquete')
    - minimum_consumption_policy_id: FK to policies (if type='consumo_minimo')
    - calculated_price: Auto-calculated price at booking time
    - minimum_consumption_amount: Required minimum spend

    Idempotent: Can be run multiple times safely.
    """
    db = get_db()
    cursor = db.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(beach_reservations)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    fields_to_add = {
        'reservation_type': "TEXT DEFAULT 'incluido' CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo'))",
        'package_id': "INTEGER REFERENCES beach_packages(id)",
        'minimum_consumption_policy_id': "INTEGER REFERENCES beach_minimum_consumption_policies(id)",
        'calculated_price': "REAL DEFAULT 0.00",
        'minimum_consumption_amount': "REAL DEFAULT 0.00"
    }

    for field_name, field_def in fields_to_add.items():
        if field_name in existing_columns:
            print(f"✓ {field_name} column already exists in beach_reservations")
            continue

        print(f"Adding {field_name} to beach_reservations...")
        cursor.execute(f'ALTER TABLE beach_reservations ADD COLUMN {field_name} {field_def}')

    # Create indexes for better query performance
    try:
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_reservations_type
            ON beach_reservations(reservation_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_reservations_package
            ON beach_reservations(package_id)
        ''')
    except Exception as e:
        print(f"Note: Index creation skipped (may already exist): {e}")

    db.commit()
    print("✓ Pricing fields added to beach_reservations successfully")


def migrate_add_package_permissions():
    """
    Add permissions for package and minimum consumption management.

    Permissions added:
    - beach.config.packages.view
    - beach.config.packages.create
    - beach.config.packages.edit
    - beach.config.packages.delete
    - beach.config.minimum_consumption.view
    - beach.config.minimum_consumption.manage

    Also adds menu items for configuration screens.

    Idempotent: Can be run multiple times safely.
    """
    db = get_db()
    cursor = db.cursor()

    permissions = [
        {
            'code': 'packages_view',
            'name': 'beach.config.packages.view',
            'description': 'Paquetes',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 1,
            'menu_url': '/beach/config/packages',
            'menu_icon': 'fa-box',
            'menu_order': 60
        },
        {
            'code': 'packages_create',
            'name': 'beach.config.packages.create',
            'description': 'Crear nuevos paquetes',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 0
        },
        {
            'code': 'packages_edit',
            'name': 'beach.config.packages.edit',
            'description': 'Editar paquetes existentes',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 0
        },
        {
            'code': 'packages_delete',
            'name': 'beach.config.packages.delete',
            'description': 'Eliminar paquetes',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 0
        },
        {
            'code': 'minimum_consumption_view',
            'name': 'beach.config.minimum_consumption.view',
            'description': 'Consumo Mínimo',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 1,
            'menu_url': '/beach/config/minimum-consumption',
            'menu_icon': 'fa-dollar-sign',
            'menu_order': 61
        },
        {
            'code': 'minimum_consumption_manage',
            'name': 'beach.config.minimum_consumption.manage',
            'description': 'Gestionar políticas de consumo mínimo',
            'module': 'beach',
            'category': 'beach_config',
            'is_menu_item': 0
        },
    ]

    for perm in permissions:
        # Check if permission already exists
        cursor.execute('SELECT id FROM permissions WHERE name = ?', (perm['name'],))
        if cursor.fetchone():
            print(f"✓ Permission '{perm['name']}' already exists")
            continue

        print(f"Adding permission: {perm['name']}")
        cursor.execute('''
            INSERT INTO permissions (
                code, name, description, module, category, is_menu_item,
                menu_url, menu_icon, menu_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            perm['code'],
            perm['name'],
            perm['description'],
            perm['module'],
            perm['category'],
            perm.get('is_menu_item', 0),
            perm.get('menu_url'),
            perm.get('menu_icon'),
            perm.get('menu_order')
        ))

    # Grant all package permissions to admin role
    cursor.execute('SELECT id FROM roles WHERE name = ?', ('admin',))
    admin_role = cursor.fetchone()

    if admin_role:
        admin_role_id = admin_role['id']
        for perm in permissions:
            cursor.execute('SELECT id FROM permissions WHERE name = ?', (perm['name'],))
            perm_row = cursor.fetchone()
            if perm_row:
                perm_id = perm_row['id']
                # Check if role_permission already exists
                cursor.execute('''
                    SELECT 1 FROM role_permissions
                    WHERE role_id = ? AND permission_id = ?
                ''', (admin_role_id, perm_id))

                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (?, ?)
                    ''', (admin_role_id, perm_id))
                    print(f"✓ Granted '{perm['name']}' to admin role")

    db.commit()
    print("✓ Package permissions added successfully")


# Export all migrations
__all__ = [
    'migrate_create_beach_packages',
    'migrate_minimum_consumption_calculation_type',
    'migrate_reservations_pricing_fields',
    'migrate_add_package_permissions',
]
