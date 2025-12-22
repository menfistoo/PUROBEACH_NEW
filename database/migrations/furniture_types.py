"""
Furniture types migrations.
Enhancements to beach_furniture_types table.
"""

from database.connection import get_db


def migrate_furniture_types_v2() -> bool:
    """
    Migration: Enhance beach_furniture_types table with additional columns
    for status colors, numbering, features, zones, and display order.

    Safe to run multiple times - checks if columns already exist.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_furniture_types)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'status_colors' in existing_columns:
        print("Migration already applied - furniture_types_v2 columns exist.")
        return False

    print("Applying furniture_types_v2 migration...")

    try:
        columns_to_add = [
            ("ALTER TABLE beach_furniture_types ADD COLUMN status_colors TEXT DEFAULT '{\"available\":\"#D2B48C\",\"reserved\":\"#4CAF50\",\"occupied\":\"#F44336\",\"maintenance\":\"#9E9E9E\"}'", 'status_colors'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN number_start INTEGER DEFAULT 1', 'number_start'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN default_features TEXT', 'default_features'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN allowed_zones TEXT', 'allowed_zones'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN display_order INTEGER DEFAULT 0', 'display_order'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        db.execute('''
            UPDATE beach_furniture_types
            SET display_order = id
            WHERE display_order IS NULL OR display_order = 0
        ''')

        db.commit()
        print("Migration furniture_types_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
