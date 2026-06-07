#!/usr/bin/env python3
"""
Backfill reservation anchors (booking_reference)
================================================
Fills the stable hotel reservation number (booking_reference) on current/future
interno sunbed reservations that are missing it, resolving each from the PMS
hotel_guests list by room + the stay covering the reservation date.

Safe to run anytime: only writes where the anchor is empty, never overwrites an
existing one, never touches past reservations, and is idempotent. The PMS import
runs this automatically; this script is for a one-time/manual run.

Usage:
    python scripts/backfill_anchors.py            # apply the backfill
    python scripts/backfill_anchors.py --dry-run  # report what WOULD change, write nothing
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description='Backfill reservation booking_reference anchors')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would change without writing')
    args = parser.parse_args()

    from app import create_app
    from database import get_db
    from models.hotel_guest import resolve_booking_reference, backfill_missing_anchors
    from utils.datetime_helpers import get_today

    app = create_app()
    with app.app_context():
        today = get_today().isoformat()

        if args.dry_run:
            # Read-only preview: count outcomes without writing.
            with get_db() as conn:
                rows = conn.execute('''
                    SELECT r.reservation_date, c.room_number,
                           TRIM(c.first_name || ' ' || COALESCE(c.last_name, '')) AS guest_name
                    FROM beach_reservations r
                    JOIN beach_customers c ON r.customer_id = c.id
                    WHERE c.customer_type = 'interno'
                      AND r.end_date >= ?
                      AND (r.booking_reference IS NULL OR r.booking_reference = '')
                ''', (today,)).fetchall()

                resolvable = ambiguous = no_pms = 0
                for row in rows:
                    ref = resolve_booking_reference(
                        row['room_number'], row['reservation_date'], row['guest_name'], conn=conn
                    )
                    if ref:
                        resolvable += 1
                    else:
                        has_pms = conn.execute('''
                            SELECT 1 FROM hotel_guests
                            WHERE room_number = ? AND arrival_date <= ? AND departure_date >= ?
                              AND booking_reference IS NOT NULL AND booking_reference != ''
                            LIMIT 1
                        ''', (row['room_number'], row['reservation_date'], row['reservation_date'])).fetchone()
                        if has_pms:
                            ambiguous += 1
                        else:
                            no_pms += 1

            print(f"[DRY-RUN] Reservas internas sin ancla (actuales/futuras): {len(rows)}")
            print(f"          Se anclarian: {resolvable}")
            print(f"          Ambiguas:     {ambiguous}")
            print(f"          Sin PMS:      {no_pms}")
            print("No se escribio nada (--dry-run).")
            return 0

        res = backfill_missing_anchors()
        print(f"Backfill completado:")
        print(f"  Ancladas:            {res['updated']}")
        print(f"  Ambiguas (omitidas): {res['ambiguous']}")
        print(f"  Sin PMS (omitidas):  {res['no_pms_record']}")
        print(f"  Escaneadas:          {res['scanned']}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
