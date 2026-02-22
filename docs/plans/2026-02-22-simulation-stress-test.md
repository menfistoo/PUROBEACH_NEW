# Simulation Stress Test Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a branch with a stress-test simulation (80-100% occupancy for a full month) and an automated health-check script that detects data integrity, business logic, and performance flaws.

**Architecture:** Modify `scripts/simulate_month.py` with `--high-occupancy`, `--month`, and `--sim-db` flags; create a standalone `scripts/health_check.py` that queries the simulation DB directly via SQLite (no Flask needed) and writes a markdown report.

**Tech Stack:** Python 3.11+, SQLite3, existing Flask app context (simulation only), argparse, pathlib

---

## Task 1: Create Branch and Simulation Database

**Files:**
- Modify: `.gitignore`

**Step 1: Create the branch**

```bash
git checkout -b simulation/stress-test-2026-02
```

Expected: `Switched to a new branch 'simulation/stress-test-2026-02'`

**Step 2: Copy the production database**

```bash
cp instance/beach_club.db database/beach_club_sim.db
```

Expected: No output. Verify: `ls -lh database/beach_club_sim.db`

**Step 3: Add sim DB to .gitignore**

Open `.gitignore` and add at the bottom:

```
# Simulation database - never commit
database/beach_club_sim.db
```

**Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: add simulation branch setup and gitignore for sim db"
```

---

## Task 2: Add --sim-db, --high-occupancy, and --month Flags to simulate_month.py

**Files:**
- Modify: `scripts/simulate_month.py`

**Context:** The current script creates `app = create_app('development')` at module level (line 50). This must be moved inside `main()` so we can set `DATABASE_PATH` env var before Flask reads it. The `--high-occupancy` flag overrides `WEEKLY_OCCUPANCY` to flat `(80, 100)` on weekdays and `(95, 100)` on weekends.

**Step 1: Move app creation and add flag handling**

In `scripts/simulate_month.py`, make these changes:

a) **Remove** the module-level line (around line 50):
```python
# CREATE Flask app for context  ← DELETE THIS
app = create_app('development')  ← DELETE THIS
```

b) **Add** a constant for the sim DB path (after the imports block, before CONSTANTS):
```python
SIM_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'database', 'beach_club_sim.db'
)

HIGH_OCCUPANCY_WEEKDAY = (80, 100)
HIGH_OCCUPANCY_WEEKEND = (95, 100)
```

c) **Update** `get_occupancy_target()` to accept an override:
```python
def get_occupancy_target(week_number: int, high_occupancy: bool = False) -> tuple:
    """Get occupancy target range for a week."""
    if high_occupancy:
        return HIGH_OCCUPANCY_WEEKDAY
    return WEEKLY_OCCUPANCY.get(week_number, (50, 70))
```

d) **Update** the occupancy section inside `run_simulation()` — find where `min_occupancy, max_occupancy = get_occupancy_target(week_num)` is called and add `high_occupancy` param. Also update the weekend boost:

Find this block (around line 718-724):
```python
        min_occupancy, max_occupancy = get_occupancy_target(week_num)

        # Weekends have higher occupancy
        if is_weekend(current_date):
            occupancy = random.randint(min(95, max_occupancy), min(100, max_occupancy + 10))
        else:
            occupancy = random.randint(min_occupancy, max_occupancy)
```

Replace with:
```python
        if high_occupancy and is_weekend(current_date):
            min_occupancy, max_occupancy = HIGH_OCCUPANCY_WEEKEND
        else:
            min_occupancy, max_occupancy = get_occupancy_target(week_num, high_occupancy)

        occupancy = random.randint(min_occupancy, max_occupancy)
```

e) **Update** `run_simulation()` signature to accept `high_occupancy`:
```python
def run_simulation(start_date: datetime, dry_run: bool = False, high_occupancy: bool = False) -> dict:
```

And update the header print and the occupancy loop to pass it through.

f) **Update** `main()`:
```python
def main():
    parser = argparse.ArgumentParser(
        description='Generate one month of beach club simulation data'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be created without making changes')
    parser.add_argument('--start-date', type=str, default=None,
                        help='Start date for simulation (YYYY-MM-DD). Default: today')
    parser.add_argument('--month', type=str, default=None,
                        help='Month for simulation (YYYY-MM). Alternative to --start-date')
    parser.add_argument('--high-occupancy', action='store_true',
                        help='Force 80-100%% occupancy every day (stress test mode)')
    parser.add_argument('--sim-db', action='store_true',
                        help=f'Use simulation database: {SIM_DB_PATH}')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show debug output including skipped reservations')

    args = parser.parse_args()

    # Set simulation database BEFORE creating Flask app
    if args.sim_db:
        if not os.path.exists(SIM_DB_PATH):
            print(f"Error: Simulation database not found at {SIM_DB_PATH}")
            print("Run: cp instance/beach_club.db database/beach_club_sim.db")
            sys.exit(1)
        os.environ['DATABASE_PATH'] = SIM_DB_PATH
        print(f"Using simulation database: {SIM_DB_PATH}")

    # Create Flask app AFTER setting DATABASE_PATH
    from app import create_app
    app = create_app('development')

    if args.verbose:
        logging.getLogger(__name__).setLevel(logging.DEBUG)

    # Parse start date
    if args.month:
        try:
            start_date = datetime.strptime(args.month, '%Y-%m')
        except ValueError:
            print(f"Error: Invalid month format '{args.month}'. Use YYYY-MM")
            sys.exit(1)
    elif args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    with app.app_context():
        try:
            results = run_simulation(
                start_date,
                dry_run=args.dry_run,
                high_occupancy=args.high_occupancy
            )
            sys.exit(0)
        except Exception as e:
            print(f"\nError during simulation: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
```

g) **Remove** the module-level `from app import create_app` line (it will be imported inside `main()`).

**Step 2: Test the flag parsing with dry-run**

```bash
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db --dry-run
```

Expected output includes:
```
Using simulation database: .../database/beach_club_sim.db
...
Mode: DRY RUN (preview only)
...
Week 1 complete: ... reservations, ~90% target occupancy
Week 2 complete: ... reservations, ~90% target occupancy
```

All weeks should show ~90% target (not decreasing). If any week shows <80%, the override is broken.

**Step 3: Commit**

```bash
git add scripts/simulate_month.py
git commit -m "feat: add --high-occupancy, --month, --sim-db flags to simulate_month.py"
```

---

## Task 3: Create health_check.py — Data Integrity Checks

**Files:**
- Create: `scripts/health_check.py`

**Context:** This script connects directly to SQLite (no Flask). It returns issues as a list of dicts with keys: `category`, `check`, `severity` (`ok`/`warn`/`fail`), `count`, `details` (list of strings).

**Step 1: Create the file skeleton**

```python
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
    """Open a read-only-style connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
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
```

**Step 2: Add data integrity checks**

```python
def check_data_integrity(conn: sqlite3.Connection) -> list:
    """
    Check for data integrity issues.

    Returns list of issue dicts.
    """
    results = []
    cur = conn.cursor()

    # --- 1. Double bookings ---
    cur.execute('''
        SELECT rf.furniture_id, rf.assignment_date,
               COUNT(DISTINCT rf.reservation_id) as booking_count,
               GROUP_CONCAT(r.ticket_number, ', ') as tickets
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE r.current_state NOT IN (?, ?, ?)
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
    cur.execute('''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state
        FROM beach_reservations r
        WHERE r.current_state NOT IN (?, ?, ?)
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
```

**Step 3: Run dry-check to verify queries compile**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('database/beach_club_sim.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM beach_reservations')
print('Reservations:', cur.fetchone()[0])
conn.close()
"
```

Expected: Prints the count of reservations in the sim DB.

**Step 4: Commit**

```bash
git add scripts/health_check.py
git commit -m "feat: add health_check.py with data integrity checks"
```

---

## Task 4: Add Business Logic Checks to health_check.py

**Files:**
- Modify: `scripts/health_check.py`

**Step 1: Add the business logic check function**

```python
def check_business_logic(conn: sqlite3.Connection) -> list:
    """
    Check for business logic violations.

    Returns list of issue dicts.
    """
    results = []
    cur = conn.cursor()

    # --- 1. 'Sentada' state on past dates ---
    today = datetime.now().strftime('%Y-%m-%d')
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
    cur.execute('''
        SELECT fb.id as block_id, fb.furniture_id, fb.start_date, fb.end_date,
               fb.block_type, rf.reservation_id, r.ticket_number, rf.assignment_date
        FROM beach_furniture_blocks fb
        JOIN beach_reservation_furniture rf ON rf.furniture_id = fb.furniture_id
        JOIN beach_reservations r ON rf.reservation_id = r.id
        WHERE rf.assignment_date BETWEEN fb.start_date AND fb.end_date
          AND r.current_state NOT IN (?, ?, ?)
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

    # --- 5. Future reservations with releasing state ---
    cur.execute('''
        SELECT r.id, r.ticket_number, r.reservation_date, r.current_state
        FROM beach_reservations r
        WHERE r.reservation_date > ?
          AND r.current_state IN (?, ?, ?)
    ''', (today,) + RELEASING_STATES)
    rows = cur.fetchall()
    # Warn only - cancelled future reservations can exist legitimately
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
```

**Step 2: Verify the new function runs without errors**

```bash
python -c "
import sqlite3, sys, os
sys.path.insert(0, '.')
conn = sqlite3.connect('database/beach_club_sim.db')
conn.row_factory = sqlite3.Row
# Quick smoke test - just check the tables exist
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name LIKE \"beach_%\"')
tables = [r[0] for r in cur.fetchall()]
print('Tables found:', len(tables))
conn.close()
"
```

Expected: Tables found: 15+ (varies by setup)

**Step 3: Commit**

```bash
git add scripts/health_check.py
git commit -m "feat: add business logic checks to health_check.py"
```

---

## Task 5: Add Performance Checks, Report Output, and CLI to health_check.py

**Files:**
- Modify: `scripts/health_check.py`

**Step 1: Add performance check function**

```python
PERF_WARN_MS = 500
PERF_FAIL_MS = 2000


def check_performance(db_path: str) -> list:
    """
    Time 6 representative queries. Returns list of issue dicts.
    Each query gets its own fresh connection to avoid caching effects.
    """
    results = []
    today = datetime.now().strftime('%Y-%m-%d')
    month_ago = datetime.now().strftime('%Y-%m-01')

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
            (month_ago,)
        ),
        (
            'Map load (all active furniture with today assignments)',
            '''
            SELECT f.id, f.number, f.zone_id, f.position_x, f.position_y,
                   rf.reservation_id, r.current_state
            FROM beach_furniture f
            LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
                AND r.current_state NOT IN ('Cancelada','No-Show','Liberada')
            WHERE f.is_active = 1
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
            (month_ago, today)
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
        conn = sqlite3.connect(db_path)
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
```

**Step 2: Add report output functions and main()**

```python
def print_summary(all_issues: list) -> None:
    """Print a colour-coded summary table to stdout."""
    c = SEVERITY_COLORS
    print()
    print("=" * 70)
    print("HEALTH CHECK RESULTS")
    print("=" * 70)

    categories = {}
    for iss in all_issues:
        categories.setdefault(iss['category'], []).append(iss)

    totals = {'ok': 0, 'warn': 0, 'fail': 0}

    for category, items in categories.items():
        print(f"\n  {category}")
        print("  " + "-" * 60)
        for iss in items:
            sev = iss['severity']
            color = c.get(sev, '')
            icon = {'ok': '✓', 'warn': '⚠', 'fail': '✗'}.get(sev, '?')
            totals[sev] += 1
            count_str = f"({iss['count']} issues)" if iss['count'] > 0 else ""
            print(f"  {color}{icon}{c['reset']} {iss['check']} {count_str}")
            if iss['details'] and sev != 'ok':
                for detail in iss['details'][:3]:
                    print(f"       → {detail}")

    print()
    print("=" * 70)
    ok_c = c['ok'] if totals['ok'] > 0 else ''
    warn_c = c['warn'] if totals['warn'] > 0 else ''
    fail_c = c['fail'] if totals['fail'] > 0 else ''
    print(
        f"  SUMMARY: "
        f"{ok_c}✓ {totals['ok']} OK{c['reset']}  "
        f"{warn_c}⚠ {totals['warn']} WARN{c['reset']}  "
        f"{fail_c}✗ {totals['fail']} FAIL{c['reset']}"
    )
    print("=" * 70)


def write_report(all_issues: list, db_path: str) -> str:
    """Write a markdown report to docs/simulation-report-YYYY-MM-DD.md."""
    report_date = datetime.now().strftime('%Y-%m-%d')
    report_path = REPORT_DIR / f'simulation-report-{report_date}.md'

    lines = [
        f"# Simulation Health Check Report",
        f"",
        f"**Date:** {report_date}",
        f"**Database:** `{db_path}`",
        f"**Run at:** {datetime.now().strftime('%H:%M:%S')}",
        f"",
    ]

    categories = {}
    for iss in all_issues:
        categories.setdefault(iss['category'], []).append(iss)

    for category, items in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Check | Severity | Issues |")
        lines.append("|-------|----------|--------|")
        for iss in items:
            sev_icon = {'ok': '✅', 'warn': '⚠️', 'fail': '❌'}.get(iss['severity'], '?')
            lines.append(f"| {iss['check']} | {sev_icon} {iss['severity'].upper()} | {iss['count']} |")
        lines.append("")

        for iss in items:
            if iss['details'] and iss['severity'] != 'ok':
                lines.append(f"### {iss['check']}")
                lines.append("")
                for detail in iss['details']:
                    lines.append(f"- {detail}")
                lines.append("")

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

    # Resolve database path
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

    print(f"\nRunning health checks on: {db_path}")
    print(f"Database size: {os.path.getsize(db_path) / 1024 / 1024:.1f} MB")

    conn = get_connection(db_path)
    all_issues = []

    print("\n[1/3] Data integrity checks...")
    all_issues.extend(check_data_integrity(conn))

    print("[2/3] Business logic checks...")
    all_issues.extend(check_business_logic(conn))

    conn.close()

    print("[3/3] Performance checks...")
    all_issues.extend(check_performance(db_path))

    print_summary(all_issues)

    if not args.no_report:
        report_path = write_report(all_issues, db_path)
        print(f"\nFull report saved to: {report_path}")

    # Exit with error code if any failures
    has_failures = any(iss['severity'] == 'fail' for iss in all_issues)
    sys.exit(1 if has_failures else 0)


if __name__ == '__main__':
    main()
```

**Step 3: Test health_check runs against sim DB**

```bash
python scripts/health_check.py --sim-db --no-report
```

Expected: Completes without Python errors. If the sim DB has no data yet, all integrity checks should show `✓ 0 issues`. If it shows `Error: Database not found`, re-run Task 1 Step 2.

**Step 4: Commit**

```bash
git add scripts/health_check.py
git commit -m "feat: add performance checks, report output, and CLI to health_check.py"
```

---

## Task 6: Run the Simulation

**Files:** None (data operation only)

**Step 1: Preview with dry-run first**

```bash
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db --dry-run
```

Expected: Shows planned customers, furniture, reservations per week — all weeks at ~90% target. No DB changes made.

**Step 2: Run the full simulation**

```bash
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db
```

Expected (approximate):
```
SIMULATION COMPLETE
  Customers created: 100
  Reservations created: 800-1200 (depends on furniture count)
  Temporary furniture: 2-3
  Furniture blocks: 1-2
  Days processed: 31
```

If it errors mid-run, re-run with `--verbose` to see which reservations are being skipped and why.

**Step 3: Verify data was inserted**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('database/beach_club_sim.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM beach_reservations')
print('Reservations:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM beach_customers')
print('Customers:', cur.fetchone()[0])
cur.execute('SELECT current_state, COUNT(*) FROM beach_reservations GROUP BY current_state')
for row in cur.fetchall(): print(f'  {row[0]}: {row[1]}')
conn.close()
"
```

Expected: 800+ reservations, 100+ customers (or merged with existing), state breakdown visible.

---

## Task 7: Run Health Check and Review Results

**Files:** None (analysis only)

**Step 1: Run the health check**

```bash
python scripts/health_check.py --sim-db
```

Expected: Produces a summary table and saves `docs/simulation-report-YYYY-MM-DD.md`.

**Step 2: Review the report**

```bash
cat docs/simulation-report-$(date +%Y-%m-%d).md
```

Look for:
- **❌ FAIL items** — these are real bugs that need GitHub Issues
- **⚠️ WARN items** — review individually; may be expected or may be worth fixing
- **Performance items** — any query >500ms under this small dataset is a red flag

**Step 3: Create GitHub Issues for any failures found**

For each FAIL item:
```bash
gh issue create \
  -t "bug: [description from health check]" \
  -b "Found during stress test simulation (simulation/stress-test-2026-02 branch). Details: [paste relevant lines from report]" \
  -l "bug,priority:high"
```

**Step 4: Commit the report**

```bash
git add docs/simulation-report-*.md
git commit -m "docs: add simulation health check report for 2026-03"
```

---

## Execution Summary

```bash
# Full workflow (copy-paste ready)
git checkout -b simulation/stress-test-2026-02
cp instance/beach_club.db database/beach_club_sim.db
echo "database/beach_club_sim.db" >> .gitignore

python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db --dry-run
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db
python scripts/health_check.py --sim-db
```
