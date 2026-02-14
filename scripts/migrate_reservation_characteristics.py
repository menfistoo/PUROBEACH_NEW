"""
One-time migration: sync existing reservation preferences CSV
to the beach_reservation_characteristics junction table.
Idempotent - safe to run multiple times.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import get_db
from models.characteristic_assignments import (
    get_reservation_characteristic_ids,
    set_reservation_characteristics_by_codes
)


def migrate():
    app = create_app()
    with app.app_context():
        with get_db() as conn:
            cursor = conn.execute('''
                SELECT id, preferences
                FROM beach_reservations
                WHERE preferences IS NOT NULL AND preferences != ''
            ''')
            reservations = cursor.fetchall()

        migrated = 0
        skipped = 0

        for res in reservations:
            res_id = res['id']
            csv = res['preferences']

            # Skip if junction table already populated
            existing = get_reservation_characteristic_ids(res_id)
            if existing:
                skipped += 1
                continue

            # Parse CSV and sync
            codes = [c.strip() for c in csv.split(',') if c.strip()]
            if codes:
                set_reservation_characteristics_by_codes(res_id, codes)
                migrated += 1

        print(f'Migration complete: {migrated} migrated, {skipped} skipped (already had data)')


if __name__ == '__main__':
    migrate()
