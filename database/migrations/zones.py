"""
Zones migrations.
Enhancements to beach_zones table for map editor.
"""

from database.connection import get_db


def migrate_zone_canvas_properties() -> bool:
    """
    Migration: Add canvas properties to beach_zones for map editor.

    Adds columns for canvas dimensions and background color.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_zones)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'canvas_width' in existing_columns:
        print("Migration already applied - zone canvas properties exist.")
        return False

    print("Applying zone_canvas_properties migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE beach_zones ADD COLUMN canvas_width REAL DEFAULT 800', 'canvas_width'),
            ('ALTER TABLE beach_zones ADD COLUMN canvas_height REAL DEFAULT 400', 'canvas_height'),
            ("ALTER TABLE beach_zones ADD COLUMN background_color TEXT DEFAULT '#FAFAFA'", 'background_color'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        db.commit()
        print("Migration zone_canvas_properties applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
