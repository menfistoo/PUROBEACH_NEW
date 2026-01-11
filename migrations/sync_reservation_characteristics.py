"""
Migration: Sync existing reservation preferences to beach_reservation_characteristics junction table.

This migration populates the junction table for reservations that have preferences
in the preferences column but not in the junction table.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

from app import create_app
from database import get_db
from models.characteristic import get_characteristic_by_code


def migrate(app):
    """Sync preferences from beach_reservations to beach_reservation_characteristics."""

    with get_db() as conn:
        cursor = conn.cursor()

        # Get all reservations with preferences that might not be synced
        cursor.execute('''
            SELECT id, preferences
            FROM beach_reservations
            WHERE preferences IS NOT NULL AND preferences != ''
        ''')

        reservations = cursor.fetchall()
        synced = 0
        skipped = 0

        for res in reservations:
            res_id = res['id']
            preferences_csv = res['preferences']

            # Parse preference codes
            codes = [c.strip() for c in preferences_csv.split(',') if c.strip()]

            if not codes:
                skipped += 1
                continue

            # Check if already synced
            cursor.execute('''
                SELECT COUNT(*) as count FROM beach_reservation_characteristics
                WHERE reservation_id = ?
            ''', (res_id,))

            existing_count = cursor.fetchone()['count']

            if existing_count >= len(codes):
                # Already synced
                skipped += 1
                continue

            # Clear existing and re-sync
            cursor.execute('''
                DELETE FROM beach_reservation_characteristics
                WHERE reservation_id = ?
            ''', (res_id,))

            # Convert codes to IDs and insert
            for code in codes:
                char = get_characteristic_by_code(code)
                if char:
                    cursor.execute('''
                        INSERT INTO beach_reservation_characteristics
                        (reservation_id, characteristic_id)
                        VALUES (?, ?)
                    ''', (res_id, char['id']))

            synced += 1

        conn.commit()

        print(f"Migration complete:")
        print(f"  - Reservations synced: {synced}")
        print(f"  - Reservations skipped (already synced or empty): {skipped}")
        print(f"  - Total processed: {len(reservations)}")


if __name__ == '__main__':
    print("Syncing reservation preferences to junction table...")
    app = create_app()
    with app.app_context():
        migrate(app)
    print("Done!")
