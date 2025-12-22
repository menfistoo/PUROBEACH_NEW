"""
Reservations migrations.
Enhancements to beach_reservations and reservation_status_history tables.
"""

from database.connection import get_db


def migrate_reservations_v2() -> bool:
    """
    Migration: Enhance beach_reservations table with SPEC columns for Phase 6.

    Adds columns for ticket numbering, multi-state management, pricing,
    PMS integration, and hotel stay dates.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_reservations)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'ticket_number' in existing_columns:
        print("Migration already applied - reservations_v2 columns exist.")
        return False

    print("Applying reservations_v2 migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE beach_reservations ADD COLUMN ticket_number TEXT', 'ticket_number'),
            ('ALTER TABLE beach_reservations ADD COLUMN reservation_date DATE', 'reservation_date'),
            ("ALTER TABLE beach_reservations ADD COLUMN time_slot TEXT DEFAULT 'all_day'", 'time_slot'),
            ("ALTER TABLE beach_reservations ADD COLUMN current_states TEXT DEFAULT ''", 'current_states'),
            ("ALTER TABLE beach_reservations ADD COLUMN current_state TEXT DEFAULT 'Confirmada'", 'current_state'),
            ("ALTER TABLE beach_reservations ADD COLUMN payment_status TEXT DEFAULT 'NO'", 'payment_status'),
            ('ALTER TABLE beach_reservations ADD COLUMN price REAL DEFAULT 0.0', 'price'),
            ('ALTER TABLE beach_reservations ADD COLUMN final_price REAL DEFAULT 0.0', 'final_price'),
            ('ALTER TABLE beach_reservations ADD COLUMN hamaca_included INTEGER DEFAULT 1', 'hamaca_included'),
            ('ALTER TABLE beach_reservations ADD COLUMN price_catalog_id INTEGER', 'price_catalog_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN paid INTEGER DEFAULT 0', 'paid'),
            ('ALTER TABLE beach_reservations ADD COLUMN charge_to_room INTEGER DEFAULT 0', 'charge_to_room'),
            ("ALTER TABLE beach_reservations ADD COLUMN charge_reference TEXT DEFAULT ''", 'charge_reference'),
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_amount REAL DEFAULT 0.0', 'minimum_consumption_amount'),
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_policy_id INTEGER', 'minimum_consumption_policy_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_to_pms INTEGER DEFAULT 0', 'consumption_charged_to_pms'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_at TIMESTAMP', 'consumption_charged_at'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_by TEXT', 'consumption_charged_by'),
            ('ALTER TABLE beach_reservations ADD COLUMN check_in_date DATE', 'check_in_date'),
            ('ALTER TABLE beach_reservations ADD COLUMN check_out_date DATE', 'check_out_date'),
            ("ALTER TABLE beach_reservations ADD COLUMN reservation_type TEXT DEFAULT 'normal'", 'reservation_type'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        db.execute('''
            UPDATE beach_reservations
            SET reservation_date = start_date
            WHERE reservation_date IS NULL
        ''')
        print("  Migrated start_date to reservation_date for existing records")

        db.execute('''
            UPDATE beach_reservations
            SET current_state = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = beach_reservations.state_id
            ),
            current_states = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = beach_reservations.state_id
            )
            WHERE state_id IS NOT NULL AND current_state = 'Confirmada'
        ''')
        print("  Migrated state_id to current_state/current_states")

        try:
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_ticket ON beach_reservations(ticket_number)')
            print("  Created index: idx_reservations_ticket")
        except Exception:
            pass

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_reservations_date ON beach_reservations(reservation_date)')
            print("  Created index: idx_reservations_date")
        except Exception:
            pass

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_reservations_consumption ON beach_reservations(consumption_charged_to_pms, minimum_consumption_amount)')
            print("  Created index: idx_reservations_consumption")
        except Exception:
            pass

        db.commit()
        print("Migration reservations_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_status_history_v2() -> bool:
    """
    Migration: Update reservation_status_history table for SPEC compatibility.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(reservation_status_history)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'status_type' in existing_columns:
        print("Migration already applied - status_history_v2 columns exist.")
        return False

    print("Applying status_history_v2 migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE reservation_status_history ADD COLUMN status_type TEXT', 'status_type'),
            ('ALTER TABLE reservation_status_history ADD COLUMN action TEXT', 'action'),
            ('ALTER TABLE reservation_status_history ADD COLUMN notes TEXT', 'notes'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        db.execute('''
            UPDATE reservation_status_history
            SET status_type = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = reservation_status_history.new_state_id
            ),
            action = 'added'
            WHERE status_type IS NULL AND new_state_id IS NOT NULL
        ''')
        print("  Migrated old records to new format")

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_status_history_reservation ON reservation_status_history(reservation_id, created_at)')
            print("  Created index: idx_status_history_reservation")
        except Exception:
            pass

        db.commit()
        print("Migration status_history_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
