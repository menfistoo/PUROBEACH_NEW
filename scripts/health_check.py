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


PERF_WARN_MS = 500
PERF_FAIL_MS = 2000


def check_performance(db_path: str) -> list:
    """
    Time 6 representative queries against the database.

    Each query uses a fresh connection to avoid caching effects.
    Returns list of issue dicts with timing information.
    """
    results = []
    today = datetime.now().strftime('%Y-%m-%d')
    month_start = datetime.now().strftime('%Y-%m-01')

    queries = [
        (
            'Availability check (furniture conflicts for a date)',
            '''
            SELECT rf.furniture_id, rf.assignment_date, r.id, r.current_state
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            WHERE rf.assignment_date = ? AND r.current_state NOT IN ('Cancelada','No-Show','Liberada')
            ''',
            (today,)
        ),
        (
            'Reservation list with customer join (last 30 days)',
            '''
            SELECT r.id, r.ticket_number, r.reservation_date, r.current_state,
                   c.first_name, c.last_name, c.customer_type
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE r.reservation_date >= ?
            ORDER BY r.reservation_date DESC
            ''',
            (month_start,)
        ),
        (
            'Map load (all active furniture with today assignments)',
            '''
            SELECT f.id, f.number, f.zone_id, f.position_x, f.position_y,
                   rf.reservation_id, r.current_state
            FROM beach_furniture f
            LEFT JOIN beach_reservation_furniture rf
                ON rf.furniture_id = f.id AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
                AND r.current_state NOT IN ('Cancelada','No-Show','Liberada')
            WHERE f.active = 1
            ''',
            (today,)
        ),
        (
            'Customer search (name LIKE)',
            '''
            SELECT id, first_name, last_name, customer_type, phone, room_number
            FROM beach_customers
            WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?
            LIMIT 50
            ''',
            ('%garcia%', '%garcia%', '%garcia%')
        ),
        (
            'Daily report aggregation (reservations by date)',
            '''
            SELECT reservation_date, current_state, COUNT(*) as count, SUM(paid) as paid_count
            FROM beach_reservations
            WHERE reservation_date BETWEEN ? AND ?
            GROUP BY reservation_date, current_state
            ORDER BY reservation_date
            ''',
            (month_start, today)
        ),
        (
            'Audit log recent entries',
            '''
            SELECT * FROM audit_log
            ORDER BY created_at DESC
            LIMIT 100
            ''',
            ()
        ),
    ]

    for label, query, params in queries:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        start = time.perf_counter()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000

            if elapsed_ms >= PERF_FAIL_MS:
                severity = 'fail'
            elif elapsed_ms >= PERF_WARN_MS:
                severity = 'warn'
            else:
                severity = 'ok'

            results.append(issue(
                category='Performance',
                check=label,
                severity=severity,
                count=len(rows),
                details=[f"{elapsed_ms:.1f}ms — {len(rows)} rows returned"]
            ))
        except Exception as e:
            results.append(issue(
                category='Performance',
                check=label,
                severity='fail',
                count=0,
                details=[f"Query error: {e}"]
            ))
        finally:
            conn.close()

    return results


def print_summary(all_issues: list) -> None:
    """Print a colour-coded summary table to stdout."""
    c = SEVERITY_COLORS
    print()
    print('=' * 70)
    print('HEALTH CHECK RESULTS')
    print('=' * 70)

    categories = {}
    for iss in all_issues:
        categories.setdefault(iss['category'], []).append(iss)

    totals = {'ok': 0, 'warn': 0, 'fail': 0}

    for category, items in categories.items():
        print(f"\n  {category}")
        print('  ' + '-' * 60)
        for iss in items:
            sev = iss['severity']
            color = c.get(sev, '')
            icon = {'ok': '[OK]', 'warn': '[WARN]', 'fail': '[FAIL]'}.get(sev, '[?]')
            totals[sev] += 1
            # For performance checks, details already contain timing info — skip the count label
            if iss['category'] != 'Performance' and iss['count'] > 0:
                count_str = f"({iss['count']} issues)"
            else:
                count_str = ''
            print(f"  {color}{icon}{c['reset']} {iss['check']} {count_str}")
            # Always show details for performance checks (timing info), only for non-ok otherwise
            if iss['details'] and (iss['category'] == 'Performance' or sev != 'ok'):
                for detail in iss['details'][:3]:
                    print(f"       -> {detail}")

    print()
    print('=' * 70)
    print(
        f"  SUMMARY: "
        f"{c['ok']}[OK] {totals['ok']}{c['reset']}  "
        f"{c['warn']}[WARN] {totals['warn']}{c['reset']}  "
        f"{c['fail']}[FAIL] {totals['fail']}{c['reset']}"
    )
    print('=' * 70)


def write_report(all_issues: list, db_path: str) -> str:
    """
    Write a markdown report to docs/simulation-report-YYYY-MM-DD.md.

    Returns the path of the written report file.
    """
    report_date = datetime.now().strftime('%Y-%m-%d')
    report_path = REPORT_DIR / f'simulation-report-{report_date}.md'

    lines = [
        '# Simulation Health Check Report',
        '',
        f'**Date:** {report_date}',
        f'**Database:** `{db_path}`',
        f'**Run at:** {datetime.now().strftime("%H:%M:%S")}',
        '',
    ]

    categories = {}
    for iss in all_issues:
        categories.setdefault(iss['category'], []).append(iss)

    for category, items in categories.items():
        lines.append(f'## {category}')
        lines.append('')
        lines.append('| Check | Severity | Issues |')
        lines.append('|-------|----------|--------|')
        for iss in items:
            sev_icon = {'ok': 'OK', 'warn': 'WARN', 'fail': 'FAIL'}.get(iss['severity'], '?')
            lines.append(f"| {iss['check']} | {sev_icon} | {iss['count']} |")
        lines.append('')

        for iss in items:
            if iss['details'] and iss['severity'] != 'ok':
                lines.append(f"### {iss['check']}")
                lines.append('')
                for detail in iss['details']:
                    lines.append(f'- {detail}')
                lines.append('')

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return str(report_path)


def main():
    parser = argparse.ArgumentParser(
        description='Run health checks on beach club simulation database'
    )
    parser.add_argument('--sim-db', action='store_true',
                        help=f'Use simulation database: {SIM_DB_PATH}')
    parser.add_argument('--db-path', type=str, default=None,
                        help='Path to SQLite database file')
    parser.add_argument('--no-report', action='store_true',
                        help='Skip writing the markdown report file')

    args = parser.parse_args()

    if args.db_path:
        db_path = args.db_path
    elif args.sim_db:
        db_path = str(SIM_DB_PATH)
    else:
        print('Error: Specify --sim-db or --db-path <path>')
        sys.exit(1)

    if not os.path.exists(db_path):
        print(f'Error: Database not found: {db_path}')
        sys.exit(1)

    print(f'\nRunning health checks on: {db_path}')
    print(f'Database size: {os.path.getsize(db_path) / 1024 / 1024:.1f} MB')

    conn = get_connection(db_path)
    all_issues = []

    print('\n[1/3] Data integrity checks...')
    all_issues.extend(check_data_integrity(conn))

    print('[2/3] Business logic checks...')
    all_issues.extend(check_business_logic(conn))

    conn.close()

    print('[3/3] Performance checks...')
    all_issues.extend(check_performance(db_path))

    print_summary(all_issues)

    if not args.no_report:
        report_path = write_report(all_issues, db_path)
        print(f'\nFull report saved to: {report_path}')

    has_failures = any(iss['severity'] == 'fail' for iss in all_issues)
    sys.exit(1 if has_failures else 0)


if __name__ == '__main__':
    main()
