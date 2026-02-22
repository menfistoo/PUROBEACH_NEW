#!/usr/bin/env python
"""
Beach Club Simulation Health Check.

Runs after simulate_month.py to detect potential flaws in:
- Data integrity (double bookings, orphaned records)
- Business logic (invalid states, pricing anomalies)
- Performance (slow queries)

Usage:
    python scripts/health_check.py --sim-db
    python scripts/health_check.py --db-path /path/to/beach_club.db
"""

import sqlite3
import time
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SIM_DB_PATH = PROJECT_ROOT / 'database' / 'beach_club_sim.db'
REPORT_DIR = PROJECT_ROOT / 'docs'

RELEASING_STATES = ('Cancelada', 'No-Show', 'Liberada')

SEVERITY_COLORS = {
    'ok': '\033[92m',    # Green
    'warn': '\033[93m',  # Yellow
    'fail': '\033[91m',  # Red
    'reset': '\033[0m'
}


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a read-only connection to the SQLite database."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def issue(category: str, check: str, severity: str, count: int, details: list) -> dict:
    """Create a standardized issue dict."""
    return {
        'category': category,
        'check': check,
        'severity': severity,
        'count': count,
        'details': details[:20]  # Cap at 20 examples
    }


def check_data_integrity(conn: sqlite3.Connection) -> list:
    """
    Check for data integrity issues.

    Returns list of issue dicts.
    """
    results = []
    cur = conn.cursor()

    # --- 1. Double bookings ---
    _placeholders = ','.join('?' * len(RELEASING_STATES))
    cur.execute(f'''
        SELECT rf.furniture_id, rf.assignment_date,
               COUNT(DISTINCT rf.reservation_id) as booking_count,
               GROUP_CONCAT(r.ticket_number, ', ') as tickets
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE r.current_state NOT IN ({_placeholders})
        GROUP BY rf.furniture_id, rf.assignment_date
        HAVING COUNT(DISTINCT rf.reservation_id) > 1
    ''', RELEASING_STATES)
    rows = cur.fetchall()
    results.append(issue(
        category='Data Integrity',
        check='Double bookings (same furniture, same date)',
        severity='fail' if rows else 'ok',
        count=len(rows),
        details=[
            f"furniture_id={r['furniture_id']} on {r['assignment_date']}: "
            f"{r['booking_count']} bookings ({r['tickets']})"
            for r in rows
        ]
    ))

    # --- 2. Orphaned furniture rows ---
    cur.execute('''
        SELECT rf.id, rf.reservation_id, rf.furniture_id, rf.assignment_date
        FROM beach_reservation_furniture rf
        LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE r.id IS NULL
    ''')
    rows = cur.fetchall()
    results.append(issue(
        category='Data Integrity',
        check='Orphaned beach_reservation_furniture rows (no parent reservation)',
        severity='fail' if rows else 'ok',
        count=len(rows),
        details=[
            f"rf.id={r['id']} references missing reservation_id={r['reservation_id']}"
            for r in rows
        ]
    ))

    # --- 3. Multi-day child orphans (parent deleted) ---
    cur.execute('''
        SELECT r.id, r.ticket_number, r.parent_reservation_id
        FROM beach_reservations r
        WHERE r.parent_reservation_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM beach_reservations p
              WHERE p.id = r.parent_reservation_id
          )
    ''')
    rows = cur.fetchall()
    results.append(issue(
        category='Data Integrity',
        check='Multi-day child reservations with missing parent',
        severity='fail' if rows else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} references missing parent_id={r['parent_reservation_id']}"
            for r in rows
        ]
    ))

    # --- 4. Reservations with no furniture assignment ---
    cur.execute(f'''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state
        FROM beach_reservations r
        WHERE r.current_state NOT IN ({_placeholders})
          AND r.reservation_type = 'normal'
          AND NOT EXISTS (
              SELECT 1 FROM beach_reservation_furniture rf
              WHERE rf.reservation_id = r.id
          )
    ''', RELEASING_STATES)
    rows = cur.fetchall()
    results.append(issue(
        category='Data Integrity',
        check='Active reservations with no furniture assignment',
        severity='warn' if rows else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} on {r['reservation_date']} ({r['current_state']})"
            for r in rows
        ]
    ))

    return results


def check_business_logic(conn: sqlite3.Connection) -> list:
    """
    Check for business logic violations.

    Returns list of issue dicts.
    """
    results = []
    cur = conn.cursor()
    _placeholders = ','.join('?' * len(RELEASING_STATES))
    today = datetime.now().strftime('%Y-%m-%d')

    # --- 1. 'Sentada' state on past dates ---
    cur.execute('''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state
        FROM beach_reservations r
        WHERE r.current_state = 'Sentada'
          AND r.reservation_date < ?
    ''', (today,))
    rows = cur.fetchall()
    results.append(issue(
        category='Business Logic',
        check="'Sentada' state on past reservation dates",
        severity='warn' if rows else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} on {r['reservation_date']}"
            for r in rows
        ]
    ))

    # --- 2. externo customer charged to room ---
    cur.execute('''
        SELECT r.id, r.ticket_number, c.customer_type, r.charge_to_room, r.reservation_date
        FROM beach_reservations r
        JOIN beach_customers c ON r.customer_id = c.id
        WHERE c.customer_type = 'externo' AND r.charge_to_room = 1
    ''')
    rows = cur.fetchall()
    results.append(issue(
        category='Business Logic',
        check='External (externo) customer with charge_to_room=1',
        severity='fail' if rows else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} on {r['reservation_date']}"
            for r in rows
        ]
    ))

    # --- 3. paid=1 with no payment_method ---
    cur.execute('''
        SELECT id, ticket_number, reservation_date, paid, payment_method
        FROM beach_reservations
        WHERE paid = 1 AND (payment_method IS NULL OR payment_method = '')
    ''')
    rows = cur.fetchall()
    results.append(issue(
        category='Business Logic',
        check='paid=1 with no payment_method set',
        severity='warn' if rows else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} on {r['reservation_date']}"
            for r in rows
        ]
    ))

    # --- 4. Furniture blocks overlapping active reservations ---
    cur.execute(f'''
        SELECT fb.id as block_id, fb.furniture_id, fb.start_date, fb.end_date,
               fb.block_type, rf.reservation_id, r.ticket_number, rf.assignment_date
        FROM beach_furniture_blocks fb
        JOIN beach_reservation_furniture rf ON rf.furniture_id = fb.furniture_id
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE rf.assignment_date BETWEEN fb.start_date AND fb.end_date
          AND r.current_state NOT IN ({_placeholders})
    ''', RELEASING_STATES)
    rows = cur.fetchall()
    results.append(issue(
        category='Business Logic',
        check='Furniture blocks overlapping active reservations',
        severity='fail' if rows else 'ok',
        count=len(rows),
        details=[
            f"block_id={r['block_id']} ({r['block_type']}) on furniture_id={r['furniture_id']} "
            f"overlaps ticket={r['ticket_number']} on {r['assignment_date']}"
            for r in rows
        ]
    ))

    # --- 5. Future reservations with releasing state (informational) ---
    cur.execute(f'''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state
        FROM beach_reservations r
        WHERE r.reservation_date > ?
          AND r.current_state IN ({_placeholders})
    ''', (today,) + RELEASING_STATES)
    rows = cur.fetchall()
    results.append(issue(
        category='Business Logic',
        check='Future reservations with releasing state (informational)',
        severity='warn' if len(rows) > 10 else 'ok',
        count=len(rows),
        details=[
            f"ticket={r['ticket_number']} on {r['reservation_date']} ({r['current_state']})"
            for r in rows[:5]
        ]
    ))

    return results


def check_performance(db_path: str) -> list:
    """Performance checks — implemented in Task 5."""
    return []


def main():
    parser = argparse.ArgumentParser(
        description='Run health checks on beach club simulation database'
    )
    parser.add_argument('--sim-db', action='store_true',
                        help=f'Use simulation database: {SIM_DB_PATH}')
    parser.add_argument('--db-path', type=str, default=None,
                        help='Path to SQLite database file')
    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    elif args.sim_db:
        db_path = str(SIM_DB_PATH)
    else:
        print("Error: Specify --sim-db or --db-path <path>")
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    conn = get_connection(db_path)
    results = check_data_integrity(conn)
    results += check_business_logic(conn)
    conn.close()

    for r in results:
        icon = {'ok': '[OK]', 'warn': '[WARN]', 'fail': '[FAIL]'}.get(r['severity'], '[?]')
        print(f"{icon} {r['check']} ({r['count']} issues)")
        for d in r['details'][:3]:
            print(f"    -> {d}")


if __name__ == '__main__':
    main()
