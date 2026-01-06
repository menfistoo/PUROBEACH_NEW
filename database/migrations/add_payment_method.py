"""
Payment Method Migration
Adds payment_method column to beach_reservations.

Migration adds:
- payment_method: TEXT with values 'efectivo', 'tarjeta', 'cargo_habitacion'

Used together with existing payment_ticket_number for payment auditing.
"""

from database import get_db


def migrate_add_payment_method() -> bool:
    """
    Add payment_method column to beach_reservations.

    Schema changes:
    - payment_method TEXT (efectivo, tarjeta, cargo_habitacion)

    Indexes:
    - idx_reservations_payment_method (partial, WHERE NOT NULL)

    Returns:
        bool: True if migration successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Check if column already exists
            cursor.execute("PRAGMA table_info(beach_reservations)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'payment_method' in columns:
                print("[INFO] payment_method column already exists, skipping...")
                return True

            print("Adding payment_method column...")
            cursor.execute("""
                ALTER TABLE beach_reservations
                ADD COLUMN payment_method TEXT
            """)

            print("Creating index...")
            # Create partial index on payment_method (only for non-NULL values)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reservations_payment_method
                ON beach_reservations(payment_method)
                WHERE payment_method IS NOT NULL
            """)

            conn.commit()
            print("[OK] Payment method field added successfully")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Migration failed: {e}")
            raise


def run_migration():
    """Run the complete payment method migration."""
    print("="*60)
    print("PAYMENT METHOD MIGRATION")
    print("="*60)

    print("\nAdding payment_method to beach_reservations...")
    if not migrate_add_payment_method():
        print("Migration failed")
        return False

    print("\n" + "="*60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nNew field added to beach_reservations:")
    print("  - payment_method (TEXT: efectivo, tarjeta, cargo_habitacion)")
    print("\nIndex created:")
    print("  - idx_reservations_payment_method")
    print("="*60)

    return True


def rollback_migration():
    """Rollback the payment method migration."""
    print("="*60)
    print("ROLLING BACK PAYMENT METHOD MIGRATION")
    print("="*60)

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            print("\nDropping index...")
            cursor.execute("DROP INDEX IF EXISTS idx_reservations_payment_method")

            print("Clearing payment_method column...")
            # SQLite doesn't support DROP COLUMN directly
            cursor.execute("UPDATE beach_reservations SET payment_method = NULL")

            conn.commit()
            print("\n[OK] Rollback completed (column set to NULL)")
            print("Note: SQLite doesn't support DROP COLUMN, column remains but is NULL")
            return True

        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] Rollback failed: {e}")
            raise


if __name__ == "__main__":
    import sys
    from app import create_app

    app = create_app()

    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
            rollback_migration()
        else:
            run_migration()
