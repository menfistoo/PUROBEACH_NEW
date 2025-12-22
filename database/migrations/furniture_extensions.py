"""
Furniture extensions migrations.
Adds furniture blocks and daily positions tables.
"""

from database.connection import get_db


def migrate_furniture_blocks_table() -> bool:
    """
    Create the beach_furniture_blocks table for blocking furniture.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table already exists
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_furniture_blocks'
    ''')

    if cursor.fetchone():
        print("  beach_furniture_blocks table already exists, skipping")
        return False

    print("Creating beach_furniture_blocks table...")

    cursor.execute('''
        CREATE TABLE beach_furniture_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furniture_id INTEGER NOT NULL REFERENCES beach_furniture(id) ON DELETE CASCADE,
            block_type TEXT CHECK(block_type IN ('maintenance','vip_hold','event','other')) DEFAULT 'other',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create index
    cursor.execute('''
        CREATE INDEX idx_furniture_blocks_dates
        ON beach_furniture_blocks(start_date, end_date, furniture_id)
    ''')

    cursor.execute('''
        CREATE INDEX idx_furniture_blocks_type
        ON beach_furniture_blocks(block_type)
    ''')

    db.commit()
    print("  beach_furniture_blocks table created successfully")
    return True


def migrate_furniture_daily_positions_table() -> bool:
    """
    Create the beach_furniture_daily_positions table for daily repositioning.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table already exists
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_furniture_daily_positions'
    ''')

    if cursor.fetchone():
        print("  beach_furniture_daily_positions table already exists, skipping")
        return False

    print("Creating beach_furniture_daily_positions table...")

    cursor.execute('''
        CREATE TABLE beach_furniture_daily_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furniture_id INTEGER NOT NULL REFERENCES beach_furniture(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            position_x REAL NOT NULL,
            position_y REAL NOT NULL,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(furniture_id, date)
        )
    ''')

    # Create index
    cursor.execute('''
        CREATE INDEX idx_daily_positions_date
        ON beach_furniture_daily_positions(date, furniture_id)
    ''')

    db.commit()
    print("  beach_furniture_daily_positions table created successfully")
    return True


def migrate_add_blocking_permission() -> bool:
    """
    Add the furniture blocking permission.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if permission exists
    cursor.execute('''
        SELECT id FROM permissions WHERE code = 'beach.furniture.block'
    ''')

    if cursor.fetchone():
        print("  beach.furniture.block permission already exists, skipping")
        return False

    print("Adding beach.furniture.block permission...")

    # Insert permission
    cursor.execute('''
        INSERT INTO permissions (code, name, description, module)
        VALUES ('beach.furniture.block', 'Bloquear mobiliario', 'Permite bloquear mobiliario para mantenimiento o eventos', 'beach')
    ''')

    # Assign to admin and manager roles
    cursor.execute('''
        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name IN ('admin', 'manager')
        AND p.code = 'beach.furniture.block'
    ''')

    db.commit()
    print("  beach.furniture.block permission added successfully")
    return True
