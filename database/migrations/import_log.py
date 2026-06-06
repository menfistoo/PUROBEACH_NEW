"""
Import log migrations.
Tracks hotel guest import history with results and errors.
"""

from database.connection import get_db


def migrate_import_log_table() -> bool:
    """
    Migration: Create beach_import_log table to track import history.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_import_log'
    """)
    if cursor.fetchone():
        print("Migration already applied - beach_import_log table exists.")
        return False

    print("Applying import_log_table migration...")

    try:
        db.execute('''
            CREATE TABLE beach_import_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_type TEXT NOT NULL DEFAULT 'hotel_guests',
                source_file TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_by INTEGER REFERENCES users(id),
                total_records INTEGER DEFAULT 0,
                created_count INTEGER DEFAULT 0,
                updated_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                errors_json TEXT,
                room_changes_json TEXT
            )
        ''')
        print("  Created beach_import_log table")

        db.execute('''
            CREATE INDEX idx_import_log_type_date
            ON beach_import_log(import_type, imported_at DESC)
        ''')
        print("  Created index on import_type + imported_at")

        db.commit()
        print("Migration import_log_table applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
