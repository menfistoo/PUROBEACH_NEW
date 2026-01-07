"""
Temporary Furniture Date Range Migration
Adds temp_start_date and temp_end_date columns to beach_furniture.

Migration adds:
- temp_start_date: DATE for start of validity range
- temp_end_date: DATE for end of validity range

This replaces the single valid_date column for temporary furniture,
allowing date ranges like the blocks feature.
"""

from database import get_db


def migrate_temp_furniture_date_range() -> bool:
    """
    Add date range columns for temporary furniture.

    Schema changes:
    - temp_start_date DATE
    - temp_end_date DATE

    Indexes:
    - idx_furniture_temp_dates (is_temporary, temp_start_date, temp_end_date)

    Data migration:
    - Existing valid_date values copied to both start and end dates

    Returns:
        bool: True if migration successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Check if columns already exist
            cursor.execute("PRAGMA table_info(beach_furniture)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'temp_start_date' in columns:
                print("[INFO] temp_start_date column already exists, skipping...")
                return True

            print("Adding temp_start_date column...")
            cursor.execute("""
                ALTER TABLE beach_furniture
                ADD COLUMN temp_start_date DATE
            """)

            print("Adding temp_end_date column...")
            cursor.execute("""
                ALTER TABLE beach_furniture
                ADD COLUMN temp_end_date DATE
            """)

            print("Migrating existing valid_date data...")
            # Copy valid_date to both start and end for existing temporary furniture
            cursor.execute("""
                UPDATE beach_furniture
                SET temp_start_date = valid_date,
                    temp_end_date = valid_date
                WHERE is_temporary = 1 AND valid_date IS NOT NULL
            """)
            migrated_count = cursor.rowcount
            print(f"  Migrated {migrated_count} existing temporary furniture items")

            print("Creating index...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_furniture_temp_dates
                ON beach_furniture(is_temporary, temp_start_date, temp_end_date)
                WHERE is_temporary = 1
            """)

            conn.commit()
            print("[OK] Temporary furniture date range columns added successfully")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Migration failed: {e}")
            raise


def run_migration():
    """Run the complete temporary furniture date range migration."""
    print("=" * 60)
    print("TEMPORARY FURNITURE DATE RANGE MIGRATION")
    print("=" * 60)

    print("\nAdding date range columns to beach_furniture...")
    if not migrate_temp_furniture_date_range():
        print("Migration failed")
        return False

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nNew columns added to beach_furniture:")
    print("  - temp_start_date (DATE)")
    print("  - temp_end_date (DATE)")
    print("\nIndex created:")
    print("  - idx_furniture_temp_dates")
    print("\nExisting temporary furniture migrated from valid_date")
    print("=" * 60)

    return True


def rollback_migration():
    """Rollback the temporary furniture date range migration."""
    print("=" * 60)
    print("ROLLING BACK TEMP FURNITURE DATE RANGE MIGRATION")
    print("=" * 60)

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            print("\nDropping index...")
            cursor.execute("DROP INDEX IF EXISTS idx_furniture_temp_dates")

            print("Clearing date range columns...")
            # SQLite doesn't support DROP COLUMN directly
            cursor.execute("""
                UPDATE beach_furniture
                SET temp_start_date = NULL, temp_end_date = NULL
            """)

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
    from app import create_app

    app = create_app()

    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
            rollback_migration()
        else:
            run_migration()
