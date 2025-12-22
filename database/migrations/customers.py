"""
Customers migrations.
Enhancements to beach_customers table.
"""

from database.connection import get_db


def migrate_customers_language_phone() -> bool:
    """
    Migration: Add language and country_code columns to beach_customers.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_customers)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'language' in existing_columns:
        print("Migration already applied - language column exists.")
        return False

    print("Applying customers_language_phone migration...")

    try:
        columns_to_add = [
            ("ALTER TABLE beach_customers ADD COLUMN language TEXT", 'language'),
            ("ALTER TABLE beach_customers ADD COLUMN country_code TEXT DEFAULT '+34'", 'country_code'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_customers_language ON beach_customers(language)')
            print("  Created index: idx_customers_language")
        except Exception:
            pass

        db.commit()
        print("Migration customers_language_phone applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_customers_extended_stats() -> bool:
    """
    Migration: Add extended statistics columns to beach_customers.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_customers)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'no_shows' in existing_columns:
        print("Migration already applied - extended stats columns exist.")
        return False

    print("Applying customers_extended_stats migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE beach_customers ADD COLUMN no_shows INTEGER DEFAULT 0', 'no_shows'),
            ('ALTER TABLE beach_customers ADD COLUMN cancellations INTEGER DEFAULT 0', 'cancellations'),
            ('ALTER TABLE beach_customers ADD COLUMN total_reservations INTEGER DEFAULT 0', 'total_reservations'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_customers_stats ON beach_customers(total_visits, no_shows, total_reservations)')
            print("  Created index: idx_customers_stats")
        except Exception:
            pass

        db.commit()
        print("Migration customers_extended_stats applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
