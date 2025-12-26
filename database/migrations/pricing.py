"""
Pricing and packages migrations.
Creates beach_packages table and updates minimum consumption policies.
"""

from database.connection import get_db


def migrate_create_beach_packages() -> bool:
    """
    Migration: Create beach_packages table for package pricing.

    Features:
    - Per-package or per-person pricing
    - Capacity constraints (min/standard/max)
    - Customer type and zone restrictions
    - Validity date ranges
    - Furniture types included

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_packages'
    """)

    if cursor.fetchone():
        print("Migration already applied - beach_packages table exists.")
        return False

    print("Applying create_beach_packages migration...")

    try:
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

        # Create indexes for better query performance
        cursor.execute('CREATE INDEX idx_packages_active ON beach_packages(active, display_order)')
        cursor.execute('CREATE INDEX idx_packages_customer_zone ON beach_packages(customer_type, zone_id)')
        cursor.execute('CREATE INDEX idx_packages_dates ON beach_packages(valid_from, valid_until)')

        db.commit()
        print("Migration create_beach_packages applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_minimum_consumption_calculation_type() -> bool:
    """
    Migration: Add calculation_type column to beach_minimum_consumption_policies.

    Allows policies to specify:
    - 'per_reservation': Fixed amount for entire reservation
    - 'per_person': Amount multiplied by number of guests

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(beach_minimum_consumption_policies)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'calculation_type' in existing_columns:
        print("Migration already applied - calculation_type column exists.")
        return False

    print("Applying minimum_consumption_calculation_type migration...")

    try:
        cursor.execute('''
            ALTER TABLE beach_minimum_consumption_policies
            ADD COLUMN calculation_type TEXT DEFAULT 'per_reservation'
            CHECK(calculation_type IN ('per_reservation', 'per_person'))
        ''')

        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_min_consumption_priority
            ON beach_minimum_consumption_policies(priority_order, is_active)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_min_consumption_lookup
            ON beach_minimum_consumption_policies(furniture_type, customer_type, zone_id, is_active)
        ''')

        db.commit()
        print("Migration minimum_consumption_calculation_type applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


# Export migrations
__all__ = [
    'migrate_create_beach_packages',
    'migrate_minimum_consumption_calculation_type',
]
