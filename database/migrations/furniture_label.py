"""
Furniture label migration.
Adds optional label column for decorative items display on the map.
"""

from database.connection import get_db


def migrate_furniture_label() -> bool:
    """
    Add label column to beach_furniture table.
    Optional display name for decorative items shown on the map.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(beach_furniture)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'label' in columns:
        print("  label column already exists in beach_furniture, skipping")
        return False

    print("Adding label column to beach_furniture table...")

    cursor.execute('''
        ALTER TABLE beach_furniture
        ADD COLUMN label TEXT DEFAULT NULL
    ''')

    db.commit()
    print("  label column added to beach_furniture table")
    return True
