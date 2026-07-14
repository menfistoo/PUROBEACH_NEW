"""
Room change history migration.
Persistent log of hotel room changes affecting beach customers, so staff can see
on the map/panel when a guest moved rooms (and audit the history per booking).
"""

from database.connection import get_db


def migrate_room_changes_table() -> bool:
    """
    Migration: Create beach_room_changes table.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_room_changes'
    """)
    if cursor.fetchone():
        print("Migration already applied - beach_room_changes table exists.")
        return False

    print("Applying room_changes_table migration...")

    try:
        db.execute('''
            CREATE TABLE beach_room_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
                booking_reference TEXT,
                old_room TEXT,
                new_room TEXT,
                source TEXT NOT NULL DEFAULT 'sync',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  Created beach_room_changes table")

        db.execute('''
            CREATE INDEX idx_room_changes_customer_date
            ON beach_room_changes(customer_id, changed_at DESC)
        ''')
        print("  Created index on customer_id + changed_at")

        db.commit()
        print("Migration room_changes_table applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
