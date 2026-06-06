"""
Migrations: anchor sunbed reservations to the hotel reservation number.

The hotel PMS reservation number (e.g. "2026-01220-1", where the trailing "-N"
identifies the room within a multi-room booking) is a STABLE key for a room and
its guests — it does not change when the physical room number changes, and it
exists before a room is assigned (pre-arrival).

We add `booking_reference` to beach_customers and beach_reservations so a sunbed
reservation can be tied to that stable key. The current room / guest names are
then resolved live from hotel_guests by booking_reference, instead of relying on
a mutable, snapshotted room number.

Both migrations are additive (nullable column) and idempotent.
"""

from database.connection import get_db


def migrate_customers_booking_reference() -> bool:
    """Add booking_reference to beach_customers (+ conservative backfill)."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_customers)")
    cols = [row['name'] for row in cursor.fetchall()]
    if 'booking_reference' in cols:
        print("Migration already applied - beach_customers.booking_reference exists.")
        return False

    print("Applying customers_booking_reference migration...")
    try:
        db.execute('ALTER TABLE beach_customers ADD COLUMN booking_reference TEXT')
        print("  Added column: beach_customers.booking_reference")

        # Best-effort backfill: only when the customer's current room maps to
        # EXACTLY ONE active booking_reference in hotel_guests (no ambiguity).
        db.execute('''
            UPDATE beach_customers
            SET booking_reference = (
                SELECT MAX(hg.booking_reference)
                FROM hotel_guests hg
                WHERE hg.room_number = beach_customers.room_number
                  AND hg.booking_reference IS NOT NULL
                  AND hg.booking_reference != ''
                  AND hg.departure_date >= date('now')
                HAVING COUNT(DISTINCT hg.booking_reference) = 1
            )
            WHERE customer_type = 'interno'
              AND room_number IS NOT NULL
              AND room_number != ''
              AND (booking_reference IS NULL OR booking_reference = '')
        ''')
        print("  Backfilled customers.booking_reference for unambiguous room matches")

        db.commit()
        print("Migration customers_booking_reference applied successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_reservations_booking_reference() -> bool:
    """Add booking_reference to beach_reservations (+ conservative backfill)."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_reservations)")
    cols = [row['name'] for row in cursor.fetchall()]
    if 'booking_reference' in cols:
        print("Migration already applied - beach_reservations.booking_reference exists.")
        return False

    print("Applying reservations_booking_reference migration...")
    try:
        db.execute('ALTER TABLE beach_reservations ADD COLUMN booking_reference TEXT')
        print("  Added column: beach_reservations.booking_reference")

        # Backfill current/future reservations from their customer's booking_reference.
        # Past reservations are left untouched (historical accuracy).
        db.execute('''
            UPDATE beach_reservations
            SET booking_reference = (
                SELECT c.booking_reference
                FROM beach_customers c
                WHERE c.id = beach_reservations.customer_id
            )
            WHERE (booking_reference IS NULL OR booking_reference = '')
              AND end_date >= date('now')
        ''')
        print("  Backfilled reservations.booking_reference from customers")

        db.commit()
        print("Migration reservations_booking_reference applied successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
