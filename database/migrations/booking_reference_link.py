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
        # NOTE: no backfill. A room can be reused by many guests over time, so
        # backfilling by room alone over-assigns the current booking to historical
        # occupants. booking_reference is populated accurately going forward when a
        # reservation is linked to a hotel guest.
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
        # NOTE: no backfill (see customers migration). Populated accurately going
        # forward when a reservation is created/linked to a hotel guest.
        db.commit()
        print("Migration reservations_booking_reference applied successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
