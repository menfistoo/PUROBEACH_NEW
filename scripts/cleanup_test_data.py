"""
Script to clear all furniture, reservations, and customers from the database.
Preserves configuration data (zones, furniture types, reservation states, etc.)
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db


def cleanup_test_data():
    """Remove all furniture, reservations, and customers from the database."""
    db = get_db()

    # Disable foreign key checks temporarily for clean deletion
    db.execute('PRAGMA foreign_keys = OFF')

    try:
        # Order matters: delete child tables first, then parents

        # 1. Reservation-related tables (depend on reservations and customers)
        tables_to_clear = [
            # Reservation child tables
            'reservation_status_history',
            'beach_reservation_tags',
            'beach_reservation_daily_states',
            'beach_reservation_furniture',
            'beach_waitlist',
            'beach_reservations',

            # Customer child tables
            'beach_customer_tags',
            'beach_customer_preferences',
            'beach_customers',

            # Furniture child tables
            'beach_furniture_blocks',
            'beach_furniture_daily_positions',
            'beach_furniture',

            # Also clear hotel guests for fresh start
            'hotel_guests',
        ]

        counts = {}
        for table in tables_to_clear:
            # Get count before deleting
            result = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()
            count = result[0] if result else 0
            counts[table] = count

            # Delete all rows
            db.execute(f'DELETE FROM {table}')

        db.commit()

        # Re-enable foreign key checks
        db.execute('PRAGMA foreign_keys = ON')

        # Print summary
        print("\n" + "=" * 50)
        print("CLEANUP COMPLETE")
        print("=" * 50)

        total_deleted = 0
        for table, count in counts.items():
            if count > 0:
                print(f"  {table}: {count} rows deleted")
                total_deleted += count

        if total_deleted == 0:
            print("  (No data to delete - database was already empty)")
        else:
            print("-" * 50)
            print(f"  TOTAL: {total_deleted} rows deleted")

        print("\nPreserved configuration:")
        print("  - Zones (beach_zones)")
        print("  - Furniture types (beach_furniture_types)")
        print("  - Reservation states (beach_reservation_states)")
        print("  - Tags (beach_tags)")
        print("  - Preferences (beach_preferences)")
        print("  - Price catalog (beach_price_catalog)")
        print("  - Minimum consumption policies")
        print("  - Packages (beach_packages)")
        print("  - System config (beach_config)")
        print("  - Users, roles, permissions")
        print("=" * 50 + "\n")

        return True

    except Exception as e:
        db.rollback()
        db.execute('PRAGMA foreign_keys = ON')
        print(f"ERROR: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("BEACH CLUB TEST DATA CLEANUP")
    print("=" * 50)
    print("\nThis will DELETE all:")
    print("  - Furniture")
    print("  - Reservations")
    print("  - Customers")
    print("  - Hotel guests")
    print("\nConfiguration will be PRESERVED.")

    response = input("\nProceed? (yes/no): ").strip().lower()

    if response == 'yes':
        cleanup_test_data()
    else:
        print("Cancelled.")
