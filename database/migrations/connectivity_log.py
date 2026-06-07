"""
Connectivity event log migration.
Records client-side network drops (WiFi roaming gaps) reported by the browser,
so staff connection issues can be audited (when, who, which device, how long).
"""

from database.connection import get_db


def migrate_connectivity_events_table() -> bool:
    """
    Migration: Create beach_connectivity_events table.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_connectivity_events'
    """)
    if cursor.fetchone():
        print("Migration already applied - beach_connectivity_events table exists.")
        return False

    print("Applying connectivity_events_table migration...")

    try:
        db.execute('''
            CREATE TABLE beach_connectivity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                username TEXT,
                offline_at TEXT,
                online_at TEXT,
                duration_seconds INTEGER,
                page TEXT,
                user_agent TEXT,
                ip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  Created beach_connectivity_events table")

        db.execute('''
            CREATE INDEX idx_connectivity_created
            ON beach_connectivity_events(created_at DESC)
        ''')
        print("  Created index on created_at")

        db.commit()
        print("Migration connectivity_events_table applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
