#!/usr/bin/env python
"""
Fix state synchronization issues in the database.

Issue #6: Furniture shows as occupied when it should be free.
This script fixes existing records where current_state and state_id are out of sync.

Usage:
    python scripts/fix_state_sync.py [--dry-run]

Options:
    --dry-run    Show what would be fixed without making changes
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import get_db


def find_inconsistent_records(cursor):
    """Find records where current_state doesn't match state_id."""
    cursor.execute('''
        SELECT r.id, r.ticket_number, r.current_state, r.state_id,
               rs.name as state_name, rs.id as expected_state_id
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.current_state != rs.name
           OR (r.state_id IS NULL AND r.current_state IS NOT NULL)
        ORDER BY r.id
    ''')
    return cursor.fetchall()


def get_state_id_by_name(cursor, state_name):
    """Get state ID by name."""
    if not state_name:
        return None
    cursor.execute(
        'SELECT id FROM beach_reservation_states WHERE name = ?',
        (state_name,)
    )
    row = cursor.fetchone()
    return row['id'] if row else None


def fix_inconsistent_records(cursor, dry_run=False):
    """Fix records where state_id doesn't match current_state."""
    inconsistent = find_inconsistent_records(cursor)

    if not inconsistent:
        print("No inconsistent records found.")
        return 0

    print(f"Found {len(inconsistent)} inconsistent record(s):\n")

    fixed_count = 0
    for record in inconsistent:
        correct_state_id = get_state_id_by_name(cursor, record['current_state'])

        print(f"  Reservation #{record['id']} ({record['ticket_number'] or 'no ticket'}):")
        print(f"    current_state: '{record['current_state']}'")
        print(f"    state_id: {record['state_id']} -> should be {correct_state_id}")
        print(f"    (was pointing to: '{record['state_name']}')")

        if not dry_run and correct_state_id is not None:
            cursor.execute('''
                UPDATE beach_reservations
                SET state_id = ?
                WHERE id = ?
            ''', (correct_state_id, record['id']))
            fixed_count += 1
            print(f"    FIXED")
        elif dry_run:
            print(f"    (dry run - not fixed)")
        else:
            print(f"    SKIPPED - state '{record['current_state']}' not found")

        print()

    return fixed_count


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("State Synchronization Fix Script")
    print("=" * 60)
    print()

    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    app = create_app()

    with app.app_context():
        with get_db() as conn:
            cursor = conn.cursor()

            fixed = fix_inconsistent_records(cursor, dry_run=dry_run)

            if not dry_run and fixed > 0:
                conn.commit()
                print(f"\nFixed {fixed} record(s).")
            elif dry_run:
                print(f"\nWould fix {len(find_inconsistent_records(cursor))} record(s).")

            # Verify no more inconsistencies
            remaining = find_inconsistent_records(cursor)
            if remaining and not dry_run:
                print(f"\nWARNING: {len(remaining)} record(s) could not be fixed.")
            elif not remaining and not dry_run:
                print("\nAll records are now consistent.")

    print("\nDone.")


if __name__ == '__main__':
    main()
