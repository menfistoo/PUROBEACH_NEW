"""
Migration: Convert preferences to caracteristicas system.

Run: python migrations/migrate_preferences_to_characteristics.py
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db


def check_tables_exist(conn):
    """Check if old tables exist."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_preferences'
    """)
    return cursor.fetchone() is not None


def check_new_tables_exist(conn):
    """Check if new tables already exist."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_characteristics'
    """)
    return cursor.fetchone() is not None


def create_new_tables(conn):
    """Create new caracteristicas tables."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_characteristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            color TEXT DEFAULT '#D4AF37',
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_furniture_characteristics (
            furniture_id INTEGER REFERENCES beach_furniture(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (furniture_id, characteristic_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_reservation_characteristics (
            reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (reservation_id, characteristic_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_customer_characteristics (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, characteristic_id)
        )
    ''')
    conn.commit()
    print("Created new tables")


def migrate_preferences_to_characteristics(conn):
    """Migrate beach_preferences to beach_characteristics."""
    # Map old preference codes to cleaner codes (remove 'pref_' prefix)
    cursor = conn.execute("""
        SELECT id, code, name, description, icon, active
        FROM beach_preferences
    """)
    preferences = cursor.fetchall()

    if not preferences:
        print("No preferences to migrate")
        return {}

    code_mapping = {}  # old_code -> new_id

    for pref in preferences:
        old_id, old_code, name, description, icon, active = pref

        # Clean up code: remove 'pref_' prefix if present
        new_code = old_code.replace('pref_', '') if old_code.startswith('pref_') else old_code

        # Assign colors based on typical use
        color = '#D4AF37'  # Default gold
        if 'sombra' in new_code:
            color = '#4A7C59'  # Green for shade
        elif 'primera' in new_code or 'mar' in new_code:
            color = '#1A3A5C'  # Ocean blue
        elif 'vip' in new_code:
            color = '#D4AF37'  # Gold for VIP
        elif 'bar' in new_code:
            color = '#C1444F'  # Red for bar
        elif 'familia' in new_code:
            color = '#E5A33D'  # Orange for family
        elif 'tranquil' in new_code:
            color = '#6B7280'  # Gray for quiet

        conn.execute("""
            INSERT INTO beach_characteristics (code, name, description, icon, color, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_code, name, description, icon, color, active))

        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        code_mapping[old_code] = new_id
        print(f"  Migrated preference: {old_code} -> {new_code} (id={new_id})")

    conn.commit()
    return code_mapping


def migrate_customer_preferences(conn, code_mapping):
    """Migrate beach_customer_preferences to beach_customer_characteristics."""
    cursor = conn.execute("""
        SELECT cp.customer_id, p.code
        FROM beach_customer_preferences cp
        JOIN beach_preferences p ON cp.preference_id = p.id
    """)
    records = cursor.fetchall()

    migrated = 0
    for customer_id, old_code in records:
        new_id = code_mapping.get(old_code)
        if new_id:
            conn.execute("""
                INSERT OR IGNORE INTO beach_customer_characteristics (customer_id, characteristic_id)
                VALUES (?, ?)
            """, (customer_id, new_id))
            migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} customer preferences")


def migrate_reservation_preferences(conn, code_mapping):
    """Migrate reservation preferences from CSV column to junction table."""
    cursor = conn.execute("""
        SELECT id, preferences FROM beach_reservations
        WHERE preferences IS NOT NULL AND preferences != ''
    """)
    reservations = cursor.fetchall()

    migrated = 0
    for res_id, prefs_csv in reservations:
        codes = [c.strip() for c in prefs_csv.split(',') if c.strip()]
        for code in codes:
            new_id = code_mapping.get(code)
            if new_id:
                conn.execute("""
                    INSERT OR IGNORE INTO beach_reservation_characteristics
                    (reservation_id, characteristic_id)
                    VALUES (?, ?)
                """, (res_id, new_id))
                migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} reservation preferences")


def migrate_furniture_features(conn):
    """Migrate furniture.features CSV to junction table."""
    cursor = conn.execute("""
        SELECT id, features FROM beach_furniture
        WHERE features IS NOT NULL AND features != ''
    """)
    furniture_rows = cursor.fetchall()

    migrated = 0
    for furn_id, features_csv in furniture_rows:
        codes = [c.strip() for c in features_csv.split(',') if c.strip()]
        for code in codes:
            # Look up characteristic by code
            char_cursor = conn.execute("""
                SELECT id FROM beach_characteristics WHERE code = ?
            """, (code,))
            char_row = char_cursor.fetchone()
            if char_row:
                conn.execute("""
                    INSERT OR IGNORE INTO beach_furniture_characteristics
                    (furniture_id, characteristic_id)
                    VALUES (?, ?)
                """, (furn_id, char_row[0]))
                migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} furniture features")


def run_migration():
    """Run the full migration."""
    print("=" * 60)
    print("MIGRATION: Preferences -> Caracteristicas")
    print("=" * 60)

    with get_db() as conn:
        # Check if migration needed
        if not check_tables_exist(conn):
            print("ERROR: beach_preferences table not found. Nothing to migrate.")
            return False

        if check_new_tables_exist(conn):
            # Check if already has data
            count = conn.execute("SELECT COUNT(*) FROM beach_characteristics").fetchone()[0]
            if count > 0:
                print(f"WARNING: beach_characteristics already has {count} records.")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Migration cancelled.")
                    return False

        # Step 1: Create new tables
        print("\n1. Creating new tables...")
        create_new_tables(conn)

        # Step 2: Migrate preferences
        print("\n2. Migrating preferences to caracteristicas...")
        code_mapping = migrate_preferences_to_characteristics(conn)

        # Step 3: Migrate customer preferences
        print("\n3. Migrating customer preferences...")
        migrate_customer_preferences(conn, code_mapping)

        # Step 4: Migrate reservation preferences
        print("\n4. Migrating reservation preferences...")
        migrate_reservation_preferences(conn, code_mapping)

        # Step 5: Migrate furniture features
        print("\n5. Migrating furniture features...")
        migrate_furniture_features(conn)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Verify data: SELECT * FROM beach_characteristics;")
        print("  2. Test the application")
        print("  3. After confirming success, run cleanup migration")

        return True


if __name__ == '__main__':
    run_migration()
