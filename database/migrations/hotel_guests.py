"""
Hotel guests migrations.
Enhancements to hotel_guests table for multi-guest support.
"""

from database.connection import get_db


def migrate_hotel_guests_multi_guest() -> bool:
    """
    Migration: Support multiple guests per room.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'is_main_guest' in existing_columns:
        print("Migration already applied - is_main_guest column exists.")
        return False

    print("Applying hotel_guests_multi_guest migration...")

    try:
        db.execute('''
            CREATE TABLE hotel_guests_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT NOT NULL,
                guest_name TEXT NOT NULL,
                arrival_date DATE,
                departure_date DATE,
                num_adults INTEGER DEFAULT 1,
                num_children INTEGER DEFAULT 0,
                vip_code TEXT,
                guest_type TEXT,
                nationality TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                source_file TEXT,
                is_main_guest INTEGER DEFAULT 0,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(room_number, arrival_date, guest_name)
            )
        ''')
        print("  Created new table with is_main_guest column")

        db.execute('''
            INSERT INTO hotel_guests_new
            (id, room_number, guest_name, arrival_date, departure_date,
             num_adults, num_children, vip_code, guest_type, nationality,
             email, phone, notes, source_file, is_main_guest, imported_at, updated_at)
            SELECT
                id, room_number, guest_name, arrival_date, departure_date,
                num_adults, num_children, vip_code, guest_type, nationality,
                email, phone, notes, source_file, 1, imported_at, updated_at
            FROM hotel_guests
        ''')
        print("  Migrated existing data (marked as main guests)")

        db.execute('DROP TABLE hotel_guests')
        print("  Dropped old table")

        db.execute('ALTER TABLE hotel_guests_new RENAME TO hotel_guests')
        print("  Renamed new table to hotel_guests")

        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_room ON hotel_guests(room_number)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_dates ON hotel_guests(arrival_date, departure_date)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_active ON hotel_guests(departure_date)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_main ON hotel_guests(room_number, is_main_guest)')
        print("  Recreated indexes")

        db.commit()
        print("Migration hotel_guests_multi_guest applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_hotel_guests_booking_reference() -> bool:
    """
    Migration: Add booking_reference column to hotel_guests.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'booking_reference' in existing_columns:
        print("Migration already applied - booking_reference column exists.")
        return False

    print("Applying hotel_guests_booking_reference migration...")

    try:
        db.execute('ALTER TABLE hotel_guests ADD COLUMN booking_reference TEXT')
        print("  Added booking_reference column")

        db.commit()
        print("Migration hotel_guests_booking_reference applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
