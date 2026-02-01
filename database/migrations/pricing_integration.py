"""
Pricing Integration Migration
Adds package_id and payment_ticket_number to beach_reservations.

Migration adds:
- package_id: FK to beach_packages (for package-based pricing)
- payment_ticket_number: PMS/POS ticket (different from reservation ticket YYMMDDRR)

Also backfills existing data for consistency.
"""

from database import get_db


def migrate_add_pricing_fields() -> bool:
    """
    Add package_id and payment_ticket_number columns to beach_reservations.

    Schema changes:
    - package_id INTEGER (FK to beach_packages)
    - payment_ticket_number TEXT (PMS/POS ticket number)

    Indexes:
    - idx_reservations_package (package_id)
    - idx_reservations_payment_ticket (payment_ticket_number WHERE NOT NULL)

    Returns:
        bool: True if migration successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Check existing columns
            cursor.execute('PRAGMA table_info(beach_reservations)')
            existing_columns = {row[1] for row in cursor.fetchall()}

            if 'package_id' not in existing_columns:
                print("Adding package_id column...")
                cursor.execute("""
                    ALTER TABLE beach_reservations
                    ADD COLUMN package_id INTEGER REFERENCES beach_packages(id)
                """)
            else:
                print("package_id column already exists, skipping.")

            if 'payment_ticket_number' not in existing_columns:
                print("Adding payment_ticket_number column...")
                cursor.execute("""
                    ALTER TABLE beach_reservations
                    ADD COLUMN payment_ticket_number TEXT
                """)
            else:
                print("payment_ticket_number column already exists, skipping.")

            print("Creating indexes...")
            # Create index on package_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reservations_package
                ON beach_reservations(package_id)
            """)

            # Create partial index on payment_ticket_number (only for non-NULL values)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reservations_payment_ticket
                ON beach_reservations(payment_ticket_number)
                WHERE payment_ticket_number IS NOT NULL
            """)

            conn.commit()
            print("[OK] Pricing fields added successfully")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Migration failed: {e}")
            raise


def migrate_backfill_pricing_data() -> bool:
    """
    Backfill pricing data for existing reservations.

    Operations:
    1. Set final_price = price where final_price is NULL or 0

    2. package_id remains NULL (no existing package assignments)

    3. payment_ticket_number remains NULL (no historical tickets)

    Returns:
        bool: True if backfill successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            print("Backfilling final_price from price...")
            # Backfill final_price from price where missing
            cursor.execute("""
                UPDATE beach_reservations
                SET final_price = price
                WHERE (final_price IS NULL OR final_price = 0) AND price > 0
            """)
            rows_updated = cursor.rowcount
            print(f"  Updated {rows_updated} reservations")

            conn.commit()
            print("[OK] Data backfill completed successfully")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Backfill failed: {e}")
            raise


def run_migration():
    """Run the complete pricing integration migration."""
    print("="*60)
    print("PRICING INTEGRATION MIGRATION")
    print("="*60)

    # Step 1: Add columns and indexes
    print("\nStep 1: Adding pricing fields to beach_reservations...")
    if not migrate_add_pricing_fields():
        print("Migration failed at step 1")
        return False

    # Step 2: Backfill existing data
    print("\nStep 2: Backfilling existing reservation data...")
    if not migrate_backfill_pricing_data():
        print("Migration failed at step 2")
        return False

    print("\n" + "="*60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nNew fields added to beach_reservations:")
    print("  - package_id (INTEGER, FK to beach_packages)")
    print("  - payment_ticket_number (TEXT)")
    print("\nIndexes created:")
    print("  - idx_reservations_package")
    print("  - idx_reservations_payment_ticket")
    print("\nData backfilled:")
    print("  - Backfilled 'final_price' from 'price'")
    print("="*60)

    return True


def rollback_migration():
    """Rollback the pricing integration migration."""
    print("="*60)
    print("ROLLING BACK PRICING INTEGRATION MIGRATION")
    print("="*60)

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            print("\nDropping indexes...")
            cursor.execute("DROP INDEX IF EXISTS idx_reservations_payment_ticket")
            cursor.execute("DROP INDEX IF EXISTS idx_reservations_package")

            print("Removing payment_ticket_number column...")
            # SQLite doesn't support DROP COLUMN directly
            # We would need to recreate the table without these columns
            # For now, just set them to NULL
            cursor.execute("UPDATE beach_reservations SET payment_ticket_number = NULL")

            print("Removing package_id column...")
            cursor.execute("UPDATE beach_reservations SET package_id = NULL")

            conn.commit()
            print("\n[OK] Rollback completed (columns set to NULL)")
            print("Note: SQLite doesn't support DROP COLUMN, columns remain but are NULL")
            return True

        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] Rollback failed: {e}")
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        run_migration()
