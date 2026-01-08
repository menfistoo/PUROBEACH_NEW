# Waitlist Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a waiting list system where customers can register interest when the beach is full, with staff manually contacting them when spots open.

**Architecture:** New `beach_waitlist` table, model layer for CRUD, REST API endpoints, slide-out panel on the map with toolbar button + badge counter.

**Tech Stack:** Flask, SQLite, Jinja2 templates, vanilla JavaScript (ES6 module pattern)

**Design Document:** `docs/plans/2026-01-08-waitlist-design.md`

---

## Task 1: Database Migration

**Files:**
- Create: `database/migrations/waitlist.py`
- Modify: `database/migrations/__init__.py`

**Step 1: Create migration file**

Create `database/migrations/waitlist.py`:

```python
"""
Waitlist migrations.
Creates the beach_waitlist table for interest registration.
"""

from database.connection import get_db


def migrate_waitlist_table() -> bool:
    """
    Create the beach_waitlist table.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    # Check if table already exists
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_waitlist'
    ''')

    if cursor.fetchone():
        print("  beach_waitlist table already exists, skipping")
        return False

    print("Creating beach_waitlist table...")

    cursor.execute('''
        CREATE TABLE beach_waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES beach_customers(id) ON DELETE CASCADE,
            requested_date DATE NOT NULL,
            num_people INTEGER NOT NULL DEFAULT 1,
            preferred_zone_id INTEGER REFERENCES beach_zones(id),
            preferred_furniture_type_id INTEGER REFERENCES beach_furniture_types(id),
            time_preference TEXT CHECK(time_preference IN ('morning', 'afternoon', 'all_day')),
            reservation_type TEXT DEFAULT 'incluido' CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo')),
            package_id INTEGER REFERENCES beach_packages(id),
            notes TEXT,
            status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'contacted', 'converted', 'declined', 'no_answer', 'expired')),
            converted_reservation_id INTEGER REFERENCES beach_reservations(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        )
    ''')

    # Create indexes
    cursor.execute('''
        CREATE INDEX idx_waitlist_date_status
        ON beach_waitlist(requested_date, status)
    ''')

    cursor.execute('''
        CREATE INDEX idx_waitlist_customer
        ON beach_waitlist(customer_id)
    ''')

    db.commit()
    print("  beach_waitlist table created successfully")
    return True


def migrate_waitlist_permissions() -> bool:
    """
    Add waitlist permissions.

    Returns:
        bool: True if migration was applied, False if skipped
    """
    db = get_db()
    cursor = db.cursor()

    permissions = [
        ('beach.waitlist.view', 'Ver lista de espera', 'beach', 0),
        ('beach.waitlist.create', 'Agregar a lista de espera', 'beach', 0),
        ('beach.waitlist.manage', 'Gestionar lista de espera', 'beach', 0),
    ]

    added = 0
    for code, description, module, is_menu in permissions:
        cursor.execute('SELECT id FROM permissions WHERE code = ?', (code,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO permissions (code, description, module, is_menu_item)
                VALUES (?, ?, ?, ?)
            ''', (code, description, module, is_menu))
            added += 1

    if added > 0:
        # Grant to admin and manager roles
        cursor.execute('SELECT id FROM roles WHERE name IN ("admin", "manager")')
        role_ids = [row[0] for row in cursor.fetchall()]

        for role_id in role_ids:
            for code, _, _, _ in permissions:
                cursor.execute('SELECT id FROM permissions WHERE code = ?', (code,))
                perm = cursor.fetchone()
                if perm:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (?, ?)
                    ''', (role_id, perm[0]))

        db.commit()
        print(f"  Added {added} waitlist permissions")
        return True

    print("  Waitlist permissions already exist, skipping")
    return False
```

**Step 2: Register migration in __init__.py**

Add to `database/migrations/__init__.py` imports:

```python
from .waitlist import migrate_waitlist_table, migrate_waitlist_permissions
```

Add to MIGRATIONS list (at the end):

```python
    # Phase 7C: Waitlist
    ('waitlist_table', migrate_waitlist_table),
    ('waitlist_permissions', migrate_waitlist_permissions),
```

Add to __all__:

```python
    'migrate_waitlist_table',
    'migrate_waitlist_permissions',
```

**Step 3: Run migration to verify**

Run: `cd .worktrees/feature-waitlist && python -c "from database.migrations import run_all_migrations; run_all_migrations()"`

Expected: "beach_waitlist table created successfully" and "Added 3 waitlist permissions"

**Step 4: Commit**

```bash
git add database/migrations/waitlist.py database/migrations/__init__.py
git commit -m "feat(waitlist): add database migration for beach_waitlist table

- Create beach_waitlist table with all required columns
- Add indexes for date/status and customer lookups
- Add waitlist permissions (view, create, manage)
- Grant permissions to admin and manager roles

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Model Layer - Basic CRUD

**Files:**
- Create: `models/waitlist.py`
- Create: `tests/test_waitlist.py`

**Step 1: Write failing test for get_waitlist_count**

Create `tests/test_waitlist.py`:

```python
"""
Tests for waitlist model functions.
"""

import pytest
from datetime import date, timedelta


class TestWaitlistCount:
    """Tests for get_waitlist_count function."""

    def test_count_returns_zero_for_empty(self, app):
        """Count returns 0 when no entries exist."""
        from models.waitlist import get_waitlist_count

        with app.app_context():
            count = get_waitlist_count(date.today().isoformat())
            assert count == 0

    def test_count_only_waiting_status(self, app):
        """Count only includes entries with 'waiting' status."""
        from models.waitlist import get_waitlist_count, create_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            # Create test customer
            customer_id = create_customer(
                first_name='Test',
                last_name='Customer',
                customer_type='externo',
                phone='600123456'
            )

            today = date.today().isoformat()

            # Create entry (status defaults to 'waiting')
            create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 2
            }, created_by=1)

            count = get_waitlist_count(today)
            assert count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'models.waitlist'"

**Step 3: Write minimal model implementation**

Create `models/waitlist.py`:

```python
"""
Waitlist model.
CRUD operations for the beach waiting list.
"""

from database import get_db
from typing import Optional, List
from datetime import date


# =============================================================================
# STATUS CONSTANTS
# =============================================================================

WAITLIST_STATUSES = {
    'waiting': {'name': 'En espera', 'color': '#FEF3C7'},
    'contacted': {'name': 'Contactado', 'color': '#DBEAFE'},
    'converted': {'name': 'Convertido', 'color': '#D1FAE5'},
    'declined': {'name': 'Rechazado', 'color': '#FEE2E2'},
    'no_answer': {'name': 'Sin respuesta', 'color': '#F3F4F6'},
    'expired': {'name': 'Expirado', 'color': '#E5E7EB'},
}

TIME_PREFERENCES = {
    'morning': 'Mañana',
    'afternoon': 'Tarde',
    'all_day': 'Todo el día',
}


# =============================================================================
# COUNT & QUERIES
# =============================================================================

def get_waitlist_count(requested_date: str) -> int:
    """
    Get count of waiting entries for a specific date.
    Used for badge display.

    Args:
        requested_date: Date string (YYYY-MM-DD)

    Returns:
        int: Number of entries with status='waiting'
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_waitlist
            WHERE requested_date = ?
              AND status = 'waiting'
        ''', (requested_date,))
        return cursor.fetchone()[0]


# =============================================================================
# CREATE
# =============================================================================

def create_waitlist_entry(data: dict, created_by: int) -> int:
    """
    Create a new waitlist entry.

    Args:
        data: Entry data with keys:
            - customer_id (required)
            - requested_date (required)
            - num_people (required)
            - preferred_zone_id (optional)
            - preferred_furniture_type_id (optional)
            - time_preference (optional)
            - reservation_type (optional, default 'incluido')
            - package_id (optional)
            - notes (optional)
        created_by: User ID creating the entry

    Returns:
        int: New entry ID

    Raises:
        ValueError: If validation fails
    """
    # Validate required fields
    if not data.get('customer_id'):
        raise ValueError("Debe seleccionar un cliente")

    if not data.get('requested_date'):
        raise ValueError("La fecha es requerida")

    # Validate date is not in past
    req_date = date.fromisoformat(data['requested_date'])
    if req_date < date.today():
        raise ValueError("La fecha debe ser hoy o futura")

    num_people = data.get('num_people', 1)
    if not isinstance(num_people, int) or num_people < 1 or num_people > 20:
        raise ValueError("Número de personas debe ser entre 1 y 20")

    # Validate time_preference if provided
    time_pref = data.get('time_preference')
    if time_pref and time_pref not in TIME_PREFERENCES:
        raise ValueError("Preferencia de horario no válida")

    # Validate reservation_type
    res_type = data.get('reservation_type', 'incluido')
    if res_type not in ('incluido', 'paquete', 'consumo_minimo'):
        raise ValueError("Tipo de reserva no válido")

    # Validate package_id if type is 'paquete'
    if res_type == 'paquete' and not data.get('package_id'):
        raise ValueError("Debe seleccionar un paquete")

    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO beach_waitlist (
                customer_id, requested_date, num_people,
                preferred_zone_id, preferred_furniture_type_id,
                time_preference, reservation_type, package_id,
                notes, status, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'waiting', ?)
        ''', (
            data['customer_id'],
            data['requested_date'],
            num_people,
            data.get('preferred_zone_id'),
            data.get('preferred_furniture_type_id'),
            time_pref,
            res_type,
            data.get('package_id'),
            data.get('notes'),
            created_by
        ))
        conn.commit()
        return cursor.lastrowid
```

**Step 4: Run test to verify it passes**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add models/waitlist.py tests/test_waitlist.py
git commit -m "feat(waitlist): add basic model with count and create functions

- Add WAITLIST_STATUSES and TIME_PREFERENCES constants
- Implement get_waitlist_count for badge display
- Implement create_waitlist_entry with validation
- Add tests for count functionality

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Model Layer - Read Operations

**Files:**
- Modify: `models/waitlist.py`
- Modify: `tests/test_waitlist.py`

**Step 1: Write failing test for get_waitlist_by_date**

Add to `tests/test_waitlist.py`:

```python
class TestWaitlistByDate:
    """Tests for get_waitlist_by_date function."""

    def test_returns_entries_for_date(self, app):
        """Returns all waiting entries for a specific date."""
        from models.waitlist import get_waitlist_by_date, create_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Test',
                last_name='User',
                customer_type='externo',
                phone='600111222'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 2,
                'notes': 'Test entry'
            }, created_by=1)

            entries = get_waitlist_by_date(today)

            assert len(entries) == 1
            assert entries[0]['id'] == entry_id
            assert entries[0]['customer_name'] is not None
            assert entries[0]['num_people'] == 2

    def test_excludes_non_waiting_status(self, app):
        """Does not return entries with non-waiting status."""
        from models.waitlist import get_waitlist_by_date, create_waitlist_entry, update_waitlist_status
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Another',
                last_name='User',
                customer_type='externo',
                phone='600333444'
            )

            today = date.today().isoformat()

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': today,
                'num_people': 3
            }, created_by=1)

            # Change status to contacted
            update_waitlist_status(entry_id, 'contacted')

            entries = get_waitlist_by_date(today)
            assert len(entries) == 0

            # But history should include it
            entries = get_waitlist_by_date(today, include_all=True)
            assert len(entries) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py::TestWaitlistByDate -v`

Expected: FAIL with "cannot import name 'get_waitlist_by_date'"

**Step 3: Implement get_waitlist_by_date and update_waitlist_status**

Add to `models/waitlist.py`:

```python
def get_waitlist_by_date(requested_date: str, include_all: bool = False) -> List[dict]:
    """
    Get waitlist entries for a specific date.

    Args:
        requested_date: Date string (YYYY-MM-DD)
        include_all: If True, include all statuses. If False, only 'waiting'.

    Returns:
        list: List of entry dicts with customer details
    """
    status_filter = "" if include_all else "AND w.status = 'waiting'"

    with get_db() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = conn.execute(f'''
            SELECT
                w.id,
                w.customer_id,
                w.requested_date,
                w.num_people,
                w.preferred_zone_id,
                w.preferred_furniture_type_id,
                w.time_preference,
                w.reservation_type,
                w.package_id,
                w.notes,
                w.status,
                w.converted_reservation_id,
                w.created_at,
                w.updated_at,
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.room_number,
                z.name as zone_name,
                ft.name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
            LEFT JOIN beach_zones z ON w.preferred_zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON w.preferred_furniture_type_id = ft.id
            LEFT JOIN beach_packages p ON w.package_id = p.id
            WHERE w.requested_date = ?
            {status_filter}
            ORDER BY w.created_at ASC
        ''', (requested_date,))
        return cursor.fetchall()


def get_waitlist_entry(entry_id: int) -> Optional[dict]:
    """
    Get a single waitlist entry by ID.

    Args:
        entry_id: Entry ID

    Returns:
        dict or None: Entry with customer details
    """
    with get_db() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = conn.execute('''
            SELECT
                w.*,
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.email,
                c.room_number,
                z.name as zone_name,
                ft.name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
            LEFT JOIN beach_zones z ON w.preferred_zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON w.preferred_furniture_type_id = ft.id
            LEFT JOIN beach_packages p ON w.package_id = p.id
            WHERE w.id = ?
        ''', (entry_id,))
        return cursor.fetchone()


# =============================================================================
# UPDATE
# =============================================================================

def update_waitlist_status(entry_id: int, status: str) -> bool:
    """
    Update the status of a waitlist entry.

    Args:
        entry_id: Entry ID
        status: New status

    Returns:
        bool: True if updated

    Raises:
        ValueError: If invalid status or transition
    """
    if status not in WAITLIST_STATUSES:
        raise ValueError(f"Estado no válido: {status}")

    # Get current entry
    entry = get_waitlist_entry(entry_id)
    if not entry:
        raise ValueError("Entrada no encontrada")

    # Check valid transitions
    current = entry['status']
    if current in ('converted', 'expired'):
        raise ValueError("No se puede modificar una entrada ya procesada")

    with get_db() as conn:
        conn.execute('''
            UPDATE beach_waitlist
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, entry_id))
        conn.commit()
        return True
```

**Step 4: Run tests to verify they pass**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py -v`

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add models/waitlist.py tests/test_waitlist.py
git commit -m "feat(waitlist): add read operations and status update

- Implement get_waitlist_by_date with customer join
- Implement get_waitlist_entry for single entry lookup
- Implement update_waitlist_status with transition validation
- Add tests for date filtering and status updates

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Model Layer - Convert and Expire

**Files:**
- Modify: `models/waitlist.py`
- Modify: `tests/test_waitlist.py`

**Step 1: Write failing tests**

Add to `tests/test_waitlist.py`:

```python
class TestWaitlistConvert:
    """Tests for convert_to_reservation function."""

    def test_convert_sets_status_and_reservation_id(self, app):
        """Convert marks entry as converted and links reservation."""
        from models.waitlist import create_waitlist_entry, convert_to_reservation, get_waitlist_entry
        from models.customer import create_customer

        with app.app_context():
            customer_id = create_customer(
                first_name='Convert',
                last_name='Test',
                customer_type='externo',
                phone='600555666'
            )

            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': date.today().isoformat(),
                'num_people': 2
            }, created_by=1)

            # Simulate reservation creation
            fake_reservation_id = 999

            convert_to_reservation(entry_id, fake_reservation_id)

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'converted'
            assert entry['converted_reservation_id'] == fake_reservation_id


class TestWaitlistExpire:
    """Tests for expire_old_entries function."""

    def test_expires_past_date_entries(self, app):
        """Entries with past dates are expired."""
        from models.waitlist import create_waitlist_entry, expire_old_entries, get_waitlist_entry
        from models.customer import create_customer
        from database import get_db

        with app.app_context():
            customer_id = create_customer(
                first_name='Expire',
                last_name='Test',
                customer_type='externo',
                phone='600777888'
            )

            # Create entry with future date first (to pass validation)
            entry_id = create_waitlist_entry({
                'customer_id': customer_id,
                'requested_date': date.today().isoformat(),
                'num_people': 1
            }, created_by=1)

            # Manually backdate it
            with get_db() as conn:
                yesterday = (date.today() - timedelta(days=1)).isoformat()
                conn.execute(
                    'UPDATE beach_waitlist SET requested_date = ? WHERE id = ?',
                    (yesterday, entry_id)
                )
                conn.commit()

            # Run expire
            expired_count = expire_old_entries()
            assert expired_count >= 1

            entry = get_waitlist_entry(entry_id)
            assert entry['status'] == 'expired'
```

**Step 2: Run tests to verify they fail**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py::TestWaitlistConvert -v`

Expected: FAIL with "cannot import name 'convert_to_reservation'"

**Step 3: Implement convert and expire functions**

Add to `models/waitlist.py`:

```python
def convert_to_reservation(entry_id: int, reservation_id: int) -> bool:
    """
    Mark entry as converted and link to reservation.

    Args:
        entry_id: Waitlist entry ID
        reservation_id: Created reservation ID

    Returns:
        bool: True if updated

    Raises:
        ValueError: If entry not found or already processed
    """
    entry = get_waitlist_entry(entry_id)
    if not entry:
        raise ValueError("Entrada no encontrada")

    if entry['status'] in ('converted', 'expired'):
        raise ValueError("No se puede convertir una entrada ya procesada")

    with get_db() as conn:
        conn.execute('''
            UPDATE beach_waitlist
            SET status = 'converted',
                converted_reservation_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (reservation_id, entry_id))
        conn.commit()
        return True


def expire_old_entries() -> int:
    """
    Expire all entries with past requested_date.
    Called on app startup and periodically.

    Returns:
        int: Number of entries expired
    """
    with get_db() as conn:
        cursor = conn.execute('''
            UPDATE beach_waitlist
            SET status = 'expired', updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('waiting', 'contacted', 'no_answer')
              AND requested_date < date('now')
        ''')
        conn.commit()
        return cursor.rowcount


def get_waitlist_history(
    requested_date: str = None,
    customer_id: int = None
) -> List[dict]:
    """
    Get non-waiting entries for reporting/history.

    Args:
        requested_date: Filter by date (optional)
        customer_id: Filter by customer (optional)

    Returns:
        list: List of entry dicts
    """
    filters = ["w.status != 'waiting'"]
    params = []

    if requested_date:
        filters.append("w.requested_date = ?")
        params.append(requested_date)

    if customer_id:
        filters.append("w.customer_id = ?")
        params.append(customer_id)

    where_clause = " AND ".join(filters)

    with get_db() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = conn.execute(f'''
            SELECT
                w.*,
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.room_number
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
            WHERE {where_clause}
            ORDER BY w.updated_at DESC
        ''', params)
        return cursor.fetchall()
```

**Step 4: Run all tests to verify they pass**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/test_waitlist.py -v`

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add models/waitlist.py tests/test_waitlist.py
git commit -m "feat(waitlist): add convert, expire, and history functions

- Implement convert_to_reservation with status validation
- Implement expire_old_entries for bulk expiration
- Implement get_waitlist_history for reporting
- Add tests for conversion and expiration flows

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: API Endpoints

**Files:**
- Create: `blueprints/beach/routes/api/waitlist.py`
- Modify: `blueprints/beach/routes/api/__init__.py`

**Step 1: Create API endpoints file**

Create `blueprints/beach/routes/api/waitlist.py`:

```python
"""
Waitlist API routes.
Endpoints for managing the beach waiting list.
"""

import logging
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date

from utils.decorators import permission_required
from models.waitlist import (
    get_waitlist_by_date,
    get_waitlist_count,
    get_waitlist_entry,
    create_waitlist_entry,
    update_waitlist_status,
    convert_to_reservation,
    get_waitlist_history,
    expire_old_entries,
    WAITLIST_STATUSES
)

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register waitlist routes on the blueprint."""

    @bp.route('/waitlist', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def list_waitlist():
        """
        Get waitlist entries for a date.

        Query params:
            date: Date (YYYY-MM-DD), defaults to today
            include_all: If 'true', include non-waiting entries

        Returns:
            JSON list of entries
        """
        requested_date = request.args.get('date', date.today().isoformat())
        include_all = request.args.get('include_all', '').lower() == 'true'

        try:
            entries = get_waitlist_by_date(requested_date, include_all=include_all)
            return jsonify({
                'success': True,
                'entries': entries,
                'count': len([e for e in entries if e['status'] == 'waiting'])
            })
        except Exception as e:
            logger.error(f"Error listing waitlist: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener lista'}), 500

    @bp.route('/waitlist/count', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def waitlist_count():
        """
        Get count of waiting entries for badge.

        Query params:
            date: Date (YYYY-MM-DD), defaults to today

        Returns:
            JSON with count
        """
        requested_date = request.args.get('date', date.today().isoformat())

        try:
            count = get_waitlist_count(requested_date)
            return jsonify({'success': True, 'count': count})
        except Exception as e:
            logger.error(f"Error getting waitlist count: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener conteo'}), 500

    @bp.route('/waitlist/<int:entry_id>', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def get_entry(entry_id):
        """Get single waitlist entry."""
        entry = get_waitlist_entry(entry_id)
        if not entry:
            return jsonify({'success': False, 'error': 'Entrada no encontrada'}), 404

        return jsonify({'success': True, 'entry': entry})

    @bp.route('/waitlist', methods=['POST'])
    @login_required
    @permission_required('beach.waitlist.create')
    def create_entry():
        """
        Create new waitlist entry.

        Request body:
            customer_id: Customer ID (required)
            requested_date: Date (required)
            num_people: Number of people (required)
            preferred_zone_id: Zone ID (optional)
            preferred_furniture_type_id: Furniture type ID (optional)
            time_preference: morning/afternoon/all_day (optional)
            reservation_type: incluido/paquete/consumo_minimo (optional)
            package_id: Package ID if type is paquete (optional)
            notes: Notes (optional)

        Returns:
            JSON with entry ID
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        try:
            entry_id = create_waitlist_entry(data, created_by=current_user.id)
            return jsonify({
                'success': True,
                'entry_id': entry_id,
                'message': 'Agregado a lista de espera'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error creating waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al crear entrada'}), 500

    @bp.route('/waitlist/<int:entry_id>', methods=['PUT'])
    @login_required
    @permission_required('beach.waitlist.manage')
    def update_entry(entry_id):
        """
        Update waitlist entry status.

        Request body:
            status: New status

        Returns:
            JSON with success
        """
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400

        try:
            update_waitlist_status(entry_id, data['status'])
            return jsonify({
                'success': True,
                'message': 'Estado actualizado'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error updating waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al actualizar'}), 500

    @bp.route('/waitlist/<int:entry_id>/convert', methods=['POST'])
    @login_required
    @permission_required('beach.waitlist.manage')
    def convert_entry(entry_id):
        """
        Mark entry as converted after reservation created.

        Request body:
            reservation_id: Created reservation ID

        Returns:
            JSON with success
        """
        data = request.get_json()

        if not data or 'reservation_id' not in data:
            return jsonify({'success': False, 'error': 'ID de reserva requerido'}), 400

        try:
            convert_to_reservation(entry_id, data['reservation_id'])
            return jsonify({
                'success': True,
                'message': 'Entrada convertida a reserva'
            })
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error converting waitlist entry: {e}")
            return jsonify({'success': False, 'error': 'Error al convertir'}), 500

    @bp.route('/waitlist/history', methods=['GET'])
    @login_required
    @permission_required('beach.waitlist.view')
    def waitlist_history():
        """
        Get waitlist history (non-waiting entries).

        Query params:
            date: Filter by date (optional)
            customer_id: Filter by customer (optional)

        Returns:
            JSON list of entries
        """
        requested_date = request.args.get('date')
        customer_id = request.args.get('customer_id', type=int)

        # Expire old entries before showing history
        expire_old_entries()

        try:
            entries = get_waitlist_history(
                requested_date=requested_date,
                customer_id=customer_id
            )
            return jsonify({'success': True, 'entries': entries})
        except Exception as e:
            logger.error(f"Error getting waitlist history: {e}")
            return jsonify({'success': False, 'error': 'Error al obtener historial'}), 500

    @bp.route('/waitlist/statuses', methods=['GET'])
    @login_required
    def get_statuses():
        """Get available waitlist statuses."""
        return jsonify({
            'success': True,
            'statuses': WAITLIST_STATUSES
        })
```

**Step 2: Register routes in __init__.py**

Add to `blueprints/beach/routes/api/__init__.py`:

After line 16, add:
```python
from blueprints.beach.routes.api import waitlist
```

After line 23, add:
```python
waitlist.register_routes(api_bp)
```

**Step 3: Run all tests to verify nothing broke**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/ -q --tb=short`

Expected: All tests pass

**Step 4: Commit**

```bash
git add blueprints/beach/routes/api/waitlist.py blueprints/beach/routes/api/__init__.py
git commit -m "feat(waitlist): add REST API endpoints

- GET /api/waitlist - list entries for date
- GET /api/waitlist/count - badge count
- GET /api/waitlist/<id> - single entry
- POST /api/waitlist - create entry
- PUT /api/waitlist/<id> - update status
- POST /api/waitlist/<id>/convert - convert to reservation
- GET /api/waitlist/history - history/reporting
- GET /api/waitlist/statuses - status definitions

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Panel Template

**Files:**
- Create: `templates/beach/_waitlist_panel.html`
- Create: `static/css/waitlist.css`

**Step 1: Create panel template**

Create `templates/beach/_waitlist_panel.html`:

```html
{#
    Waitlist Panel Partial
    Slide-out panel for managing the waiting list from the map
#}

<!-- Panel Backdrop -->
<div class="waitlist-panel-backdrop" id="waitlistPanelBackdrop"></div>

<!-- Waitlist Panel -->
<div class="waitlist-panel" id="waitlistPanel" role="dialog" aria-labelledby="waitlistPanelTitle" aria-modal="true">
    <!-- Header -->
    <div class="panel-header">
        <button type="button" class="panel-close-btn" id="waitlistPanelCloseBtn"
                aria-label="Cerrar panel" title="Cerrar">
            <i class="fas fa-chevron-right"></i>
        </button>
        <div class="panel-title">
            <span class="panel-ticket" id="waitlistPanelTitle">Lista de Espera</span>
            <span class="panel-date" id="waitlistPanelDate"></span>
        </div>
        <div style="width: 44px;"></div>
    </div>

    <!-- Tabs -->
    <div class="waitlist-tabs">
        <button type="button" class="waitlist-tab active" data-tab="pending" id="waitlistTabPending">
            Pendientes <span class="waitlist-tab-count" id="waitlistPendingCount">0</span>
        </button>
        <button type="button" class="waitlist-tab" data-tab="history" id="waitlistTabHistory">
            Historial
        </button>
    </div>

    <!-- Body (scrollable) -->
    <div class="panel-body">
        <!-- Pending Tab Content -->
        <div class="waitlist-tab-content active" id="waitlistPendingContent">
            <div class="waitlist-entries" id="waitlistPendingEntries">
                <!-- Entries populated by JavaScript -->
            </div>
            <div class="waitlist-empty" id="waitlistPendingEmpty" style="display: none;">
                <i class="fas fa-clock"></i>
                <p>No hay clientes en lista de espera</p>
            </div>
        </div>

        <!-- History Tab Content -->
        <div class="waitlist-tab-content" id="waitlistHistoryContent" style="display: none;">
            <div class="waitlist-entries" id="waitlistHistoryEntries">
                <!-- History populated by JavaScript -->
            </div>
            <div class="waitlist-empty" id="waitlistHistoryEmpty" style="display: none;">
                <i class="fas fa-history"></i>
                <p>No hay historial para esta fecha</p>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="panel-footer">
        <button type="button" class="btn btn-secondary w-100" id="waitlistAddBtn">
            <i class="fas fa-plus"></i> Añadir a Lista de Espera
        </button>
    </div>
</div>

<!-- Add Entry Modal -->
<div class="modal fade" id="waitlistAddModal" tabindex="-1" aria-labelledby="waitlistAddModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="waitlistAddModalLabel">
                    <i class="fas fa-clock"></i> Añadir a Lista de Espera
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
                <!-- Customer Section -->
                <div class="form-section">
                    <label class="form-section-title">
                        <i class="fas fa-user"></i> Cliente
                    </label>

                    <!-- Customer Type Toggle -->
                    <div class="customer-type-toggle mb-3">
                        <div class="btn-group w-100" role="group">
                            <input type="radio" class="btn-check" name="waitlistCustomerType" id="waitlistTypeInterno" value="interno">
                            <label class="btn btn-outline-primary" for="waitlistTypeInterno">
                                <i class="fas fa-hotel"></i> Interno
                            </label>
                            <input type="radio" class="btn-check" name="waitlistCustomerType" id="waitlistTypeExterno" value="externo" checked>
                            <label class="btn btn-outline-primary" for="waitlistTypeExterno">
                                <i class="fas fa-user"></i> Externo
                            </label>
                        </div>
                    </div>

                    <!-- Room Search (Interno) -->
                    <div class="waitlist-interno-search" id="waitlistInternoSearch" style="display: none;">
                        <div class="mb-3">
                            <label class="form-label">Número de Habitación</label>
                            <input type="text" class="form-control" id="waitlistRoomNumber"
                                   placeholder="Ej: 205" autocomplete="off">
                            <div class="room-search-results" id="waitlistRoomResults"></div>
                        </div>
                    </div>

                    <!-- Customer Search (Externo) -->
                    <div class="waitlist-externo-search" id="waitlistExternoSearch">
                        <div class="mb-3">
                            <label class="form-label">Buscar Cliente</label>
                            <input type="text" class="form-control" id="waitlistCustomerSearch"
                                   placeholder="Nombre o teléfono..." autocomplete="off">
                            <div class="customer-search-results" id="waitlistCustomerResults"></div>
                        </div>
                    </div>

                    <!-- Selected Customer Display -->
                    <div class="waitlist-customer-selected" id="waitlistCustomerSelected" style="display: none;">
                        <div class="selected-customer-card">
                            <span class="customer-name" id="waitlistSelectedName"></span>
                            <span class="customer-badge" id="waitlistSelectedBadge"></span>
                            <button type="button" class="btn btn-sm btn-link" id="waitlistClearCustomer">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>

                    <input type="hidden" id="waitlistCustomerId">
                </div>

                <!-- Details Section -->
                <div class="form-section">
                    <label class="form-section-title">
                        <i class="fas fa-info-circle"></i> Detalles
                    </label>

                    <div class="row">
                        <div class="col-6 mb-3">
                            <label class="form-label">Fecha</label>
                            <input type="date" class="form-control" id="waitlistDate">
                        </div>
                        <div class="col-6 mb-3">
                            <label class="form-label">Personas</label>
                            <input type="number" class="form-control" id="waitlistNumPeople"
                                   min="1" max="20" value="2">
                        </div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label">Horario Preferido</label>
                        <select class="form-select" id="waitlistTimePref">
                            <option value="">Sin preferencia</option>
                            <option value="morning">Mañana</option>
                            <option value="afternoon">Tarde</option>
                            <option value="all_day">Todo el día</option>
                        </select>
                    </div>
                </div>

                <!-- Preferences Section -->
                <div class="form-section">
                    <label class="form-section-title">
                        <i class="fas fa-sliders-h"></i> Preferencias
                    </label>

                    <div class="row">
                        <div class="col-6 mb-3">
                            <label class="form-label">Zona</label>
                            <select class="form-select" id="waitlistZone">
                                <option value="">Sin preferencia</option>
                                <!-- Populated by JavaScript -->
                            </select>
                        </div>
                        <div class="col-6 mb-3">
                            <label class="form-label">Tipo Mobiliario</label>
                            <select class="form-select" id="waitlistFurnitureType">
                                <option value="">Sin preferencia</option>
                                <!-- Populated by JavaScript -->
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Reservation Type Section -->
                <div class="form-section">
                    <label class="form-section-title">
                        <i class="fas fa-tag"></i> Tipo de Reserva
                    </label>

                    <div class="reservation-type-options">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="waitlistResType"
                                   id="waitlistResIncluido" value="incluido" checked>
                            <label class="form-check-label" for="waitlistResIncluido">
                                Incluido en Reserva
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="waitlistResType"
                                   id="waitlistResPaquete" value="paquete">
                            <label class="form-check-label" for="waitlistResPaquete">
                                Paquete
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="waitlistResType"
                                   id="waitlistResConsumo" value="consumo_minimo">
                            <label class="form-check-label" for="waitlistResConsumo">
                                Consumo Mínimo
                            </label>
                        </div>
                    </div>

                    <!-- Package Selector (shown when paquete selected) -->
                    <div class="waitlist-package-select mt-2" id="waitlistPackageSelect" style="display: none;">
                        <select class="form-select" id="waitlistPackageId">
                            <option value="">Seleccionar paquete...</option>
                            <!-- Populated by JavaScript -->
                        </select>
                    </div>
                </div>

                <!-- Notes Section -->
                <div class="form-section">
                    <label class="form-section-title">
                        <i class="fas fa-sticky-note"></i> Notas
                    </label>
                    <textarea class="form-control" id="waitlistNotes" rows="2"
                              placeholder="Notas adicionales..."></textarea>
                </div>

                <!-- Error Display -->
                <div class="alert alert-danger mt-3" id="waitlistAddError" style="display: none;"></div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary" id="waitlistSaveBtn">
                    <i class="fas fa-plus"></i> Añadir
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Status Change Dropdown Template (used by JS) -->
<template id="waitlistStatusDropdownTemplate">
    <div class="dropdown">
        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button"
                data-bs-toggle="dropdown" aria-expanded="false">
            Estado
        </button>
        <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="#" data-status="contacted">
                <i class="fas fa-phone"></i> Contactado
            </a></li>
            <li><a class="dropdown-item" href="#" data-status="declined">
                <i class="fas fa-times"></i> Rechazado
            </a></li>
            <li><a class="dropdown-item" href="#" data-status="no_answer">
                <i class="fas fa-phone-slash"></i> Sin Respuesta
            </a></li>
        </ul>
    </div>
</template>
```

**Step 2: Create CSS file**

Create `static/css/waitlist.css`:

```css
/**
 * Waitlist Panel Styles
 * Follows Beach Club Design System
 */

/* =============================================================================
   PANEL STRUCTURE
   ============================================================================= */

.waitlist-panel-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(26, 58, 92, 0.4);
    backdrop-filter: blur(2px);
    z-index: var(--z-modal-backdrop, 300);
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease, visibility 0.3s ease;
}

.waitlist-panel-backdrop.active {
    opacity: 1;
    visibility: visible;
}

.waitlist-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    max-width: 90vw;
    height: 100vh;
    background: #FFFFFF;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    z-index: var(--z-modal, 400);
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.3s ease;
}

.waitlist-panel.active {
    transform: translateX(0);
}

/* =============================================================================
   PANEL HEADER
   ============================================================================= */

.waitlist-panel .panel-header {
    background: linear-gradient(135deg, #1A3A5C 0%, #2A4A6C 100%);
    color: #FFFFFF;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}

.waitlist-panel .panel-close-btn {
    width: 36px;
    height: 36px;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.waitlist-panel .panel-close-btn:hover {
    background: rgba(255, 255, 255, 0.2);
}

.waitlist-panel .panel-title {
    text-align: center;
}

.waitlist-panel .panel-ticket {
    display: block;
    font-size: 18px;
    font-weight: 600;
}

.waitlist-panel .panel-date {
    display: block;
    font-size: 13px;
    opacity: 0.8;
    margin-top: 2px;
}

/* =============================================================================
   TABS
   ============================================================================= */

.waitlist-tabs {
    display: flex;
    border-bottom: 1px solid #E8E8E8;
    flex-shrink: 0;
}

.waitlist-tab {
    flex: 1;
    padding: 12px 16px;
    border: none;
    background: none;
    font-size: 14px;
    font-weight: 500;
    color: #6B7280;
    cursor: pointer;
    position: relative;
    transition: color 0.2s ease;
}

.waitlist-tab:hover {
    color: #1A3A5C;
}

.waitlist-tab.active {
    color: #D4AF37;
}

.waitlist-tab.active::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: #D4AF37;
}

.waitlist-tab-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    background: #D4AF37;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
    border-radius: 10px;
    margin-left: 6px;
}

.waitlist-tab:not(.active) .waitlist-tab-count {
    background: #E5E7EB;
    color: #6B7280;
}

/* =============================================================================
   PANEL BODY
   ============================================================================= */

.waitlist-panel .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.waitlist-tab-content {
    display: none;
}

.waitlist-tab-content.active {
    display: block;
}

/* =============================================================================
   ENTRY CARDS
   ============================================================================= */

.waitlist-entry-card {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    transition: box-shadow 0.2s ease;
}

.waitlist-entry-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.waitlist-entry-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}

.waitlist-entry-customer {
    font-size: 15px;
    font-weight: 600;
    color: #1A3A5C;
}

.waitlist-entry-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.waitlist-entry-badge.interno {
    background: #DBEAFE;
    color: #1E40AF;
}

.waitlist-entry-badge.externo {
    background: #FEF3C7;
    color: #92400E;
}

.waitlist-entry-details {
    font-size: 13px;
    color: #6B7280;
    margin-bottom: 8px;
}

.waitlist-entry-details i {
    width: 16px;
    color: #9CA3AF;
    margin-right: 4px;
}

.waitlist-entry-prefs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
}

.waitlist-entry-pref {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: #F3F4F6;
    border-radius: 4px;
    font-size: 12px;
    color: #4B5563;
}

.waitlist-entry-pref i {
    margin-right: 4px;
    font-size: 10px;
}

.waitlist-entry-time {
    font-size: 12px;
    color: #9CA3AF;
    margin-bottom: 12px;
}

.waitlist-entry-actions {
    display: flex;
    gap: 8px;
}

.waitlist-entry-actions .btn-convert {
    flex: 1;
}

/* Status badges for history */
.waitlist-status-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
}

.waitlist-status-badge.contacted {
    background: #DBEAFE;
    color: #1E40AF;
}

.waitlist-status-badge.converted {
    background: #D1FAE5;
    color: #065F46;
}

.waitlist-status-badge.declined {
    background: #FEE2E2;
    color: #991B1B;
}

.waitlist-status-badge.no_answer {
    background: #F3F4F6;
    color: #4B5563;
}

.waitlist-status-badge.expired {
    background: #E5E7EB;
    color: #6B7280;
}

/* =============================================================================
   EMPTY STATE
   ============================================================================= */

.waitlist-empty {
    text-align: center;
    padding: 40px 20px;
    color: #9CA3AF;
}

.waitlist-empty i {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
}

.waitlist-empty p {
    font-size: 14px;
    margin: 0;
}

/* =============================================================================
   PANEL FOOTER
   ============================================================================= */

.waitlist-panel .panel-footer {
    padding: 16px;
    border-top: 1px solid #E8E8E8;
    flex-shrink: 0;
}

/* =============================================================================
   ADD MODAL
   ============================================================================= */

#waitlistAddModal .modal-header {
    background: linear-gradient(135deg, #1A3A5C 0%, #2A4A6C 100%);
    color: #FFFFFF;
}

#waitlistAddModal .modal-title i {
    margin-right: 8px;
}

#waitlistAddModal .modal-footer {
    background: #FAFAFA;
    border-top: 1px solid #E8E8E8;
}

.form-section {
    margin-bottom: 20px;
}

.form-section-title {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #1A3A5C;
    margin-bottom: 12px;
}

.form-section-title i {
    margin-right: 6px;
    color: #D4AF37;
}

/* Customer Type Toggle */
.customer-type-toggle .btn-outline-primary {
    border-color: #E8E8E8;
    color: #6B7280;
}

.customer-type-toggle .btn-outline-primary:hover {
    background: #F5E6D3;
    border-color: #D4AF37;
    color: #1A3A5C;
}

.customer-type-toggle .btn-check:checked + .btn-outline-primary {
    background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
    border-color: #D4AF37;
    color: #FFFFFF;
}

/* Selected Customer Card */
.selected-customer-card {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: #F5E6D3;
    border-radius: 8px;
}

.selected-customer-card .customer-name {
    flex: 1;
    font-weight: 500;
    color: #1A3A5C;
}

.selected-customer-card .customer-badge {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
}

/* Reservation Type Options */
.reservation-type-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.reservation-type-options .form-check {
    padding: 10px 12px 10px 36px;
    background: #FAFAFA;
    border-radius: 8px;
    margin: 0;
}

.reservation-type-options .form-check:hover {
    background: #F5E6D3;
}

.reservation-type-options .form-check-input:checked ~ .form-check-label {
    font-weight: 500;
}

/* =============================================================================
   TOOLBAR BUTTON
   ============================================================================= */

.waitlist-toolbar-btn {
    position: relative;
}

.waitlist-toolbar-btn .waitlist-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    background: #D4AF37;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.waitlist-toolbar-btn .waitlist-badge:empty,
.waitlist-toolbar-btn .waitlist-badge[data-count="0"] {
    display: none;
}

/* =============================================================================
   RESPONSIVE
   ============================================================================= */

@media (max-width: 480px) {
    .waitlist-panel {
        width: 100%;
        max-width: none;
    }
}
```

**Step 3: Commit**

```bash
git add templates/beach/_waitlist_panel.html static/css/waitlist.css
git commit -m "feat(waitlist): add panel template and CSS styles

- Create slide-out panel with header, tabs, body, footer
- Create add entry modal with all form fields
- Add CSS following design system (colors, spacing, typography)
- Add responsive styles for mobile

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: JavaScript Module

**Files:**
- Create: `static/js/WaitlistManager.js`

**Step 1: Create JavaScript module**

Create `static/js/WaitlistManager.js`:

```javascript
/**
 * WaitlistManager.js
 * Manages the waitlist panel, entries, and interactions.
 */

export class WaitlistManager {
    constructor(options = {}) {
        this.currentDate = options.currentDate || new Date().toISOString().split('T')[0];
        this.onConvert = options.onConvert || null;

        // DOM elements
        this.panel = document.getElementById('waitlistPanel');
        this.backdrop = document.getElementById('waitlistPanelBackdrop');
        this.closeBtn = document.getElementById('waitlistPanelCloseBtn');
        this.dateDisplay = document.getElementById('waitlistPanelDate');
        this.pendingEntries = document.getElementById('waitlistPendingEntries');
        this.historyEntries = document.getElementById('waitlistHistoryEntries');
        this.pendingEmpty = document.getElementById('waitlistPendingEmpty');
        this.historyEmpty = document.getElementById('waitlistHistoryEmpty');
        this.pendingCount = document.getElementById('waitlistPendingCount');
        this.addBtn = document.getElementById('waitlistAddBtn');
        this.tabPending = document.getElementById('waitlistTabPending');
        this.tabHistory = document.getElementById('waitlistTabHistory');
        this.pendingContent = document.getElementById('waitlistPendingContent');
        this.historyContent = document.getElementById('waitlistHistoryContent');

        // Modal elements
        this.modal = document.getElementById('waitlistAddModal');
        this.saveBtn = document.getElementById('waitlistSaveBtn');
        this.errorDisplay = document.getElementById('waitlistAddError');

        // Bind methods
        this.open = this.open.bind(this);
        this.close = this.close.bind(this);
        this.refresh = this.refresh.bind(this);

        this._init();
    }

    _init() {
        // Panel open/close
        this.closeBtn?.addEventListener('click', this.close);
        this.backdrop?.addEventListener('click', this.close);

        // Tab switching
        this.tabPending?.addEventListener('click', () => this._switchTab('pending'));
        this.tabHistory?.addEventListener('click', () => this._switchTab('history'));

        // Add button
        this.addBtn?.addEventListener('click', () => this._openAddModal());

        // Save button
        this.saveBtn?.addEventListener('click', () => this._saveEntry());

        // Customer type toggle
        document.querySelectorAll('input[name="waitlistCustomerType"]').forEach(radio => {
            radio.addEventListener('change', (e) => this._toggleCustomerType(e.target.value));
        });

        // Reservation type toggle
        document.querySelectorAll('input[name="waitlistResType"]').forEach(radio => {
            radio.addEventListener('change', (e) => this._toggleResType(e.target.value));
        });

        // Clear customer
        document.getElementById('waitlistClearCustomer')?.addEventListener('click', () => {
            this._clearCustomer();
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.panel?.classList.contains('active')) {
                this.close();
            }
        });
    }

    setDate(date) {
        this.currentDate = date;
        if (this.panel?.classList.contains('active')) {
            this.refresh();
        }
    }

    async open() {
        this.panel?.classList.add('active');
        this.backdrop?.classList.add('active');
        this._updateDateDisplay();
        await this.refresh();
    }

    close() {
        this.panel?.classList.remove('active');
        this.backdrop?.classList.remove('active');
    }

    async refresh() {
        await Promise.all([
            this._loadPendingEntries(),
            this._loadHistoryEntries()
        ]);
    }

    async getCount() {
        try {
            const response = await fetch(`/beach/api/waitlist/count?date=${this.currentDate}`);
            const data = await response.json();
            return data.success ? data.count : 0;
        } catch (error) {
            console.error('Error getting waitlist count:', error);
            return 0;
        }
    }

    _updateDateDisplay() {
        if (this.dateDisplay) {
            const date = new Date(this.currentDate + 'T00:00:00');
            this.dateDisplay.textContent = date.toLocaleDateString('es-ES', {
                day: 'numeric',
                month: 'short',
                year: 'numeric'
            });
        }
    }

    async _loadPendingEntries() {
        try {
            const response = await fetch(`/beach/api/waitlist?date=${this.currentDate}`);
            const data = await response.json();

            if (data.success) {
                this._renderEntries(data.entries, this.pendingEntries, this.pendingEmpty, true);
                if (this.pendingCount) {
                    this.pendingCount.textContent = data.count;
                }
            }
        } catch (error) {
            console.error('Error loading pending entries:', error);
        }
    }

    async _loadHistoryEntries() {
        try {
            const response = await fetch(`/beach/api/waitlist/history?date=${this.currentDate}`);
            const data = await response.json();

            if (data.success) {
                this._renderEntries(data.entries, this.historyEntries, this.historyEmpty, false);
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    _renderEntries(entries, container, emptyEl, showActions) {
        if (!container) return;

        if (entries.length === 0) {
            container.innerHTML = '';
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        container.innerHTML = entries.map(entry => this._renderEntryCard(entry, showActions)).join('');

        // Bind actions
        container.querySelectorAll('.btn-convert').forEach(btn => {
            btn.addEventListener('click', () => this._handleConvert(parseInt(btn.dataset.entryId)));
        });

        container.querySelectorAll('[data-status]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const entryId = parseInt(link.closest('.waitlist-entry-card').dataset.entryId);
                this._handleStatusChange(entryId, link.dataset.status);
            });
        });
    }

    _renderEntryCard(entry, showActions) {
        const timePrefLabels = {
            morning: 'Mañana',
            afternoon: 'Tarde',
            all_day: 'Todo el día'
        };

        const statusLabels = {
            waiting: 'En espera',
            contacted: 'Contactado',
            converted: 'Convertido',
            declined: 'Rechazado',
            no_answer: 'Sin respuesta',
            expired: 'Expirado'
        };

        const timeAgo = this._formatTimeAgo(entry.created_at);

        let prefsHtml = '';
        if (entry.zone_name) {
            prefsHtml += `<span class="waitlist-entry-pref"><i class="fas fa-map-marker-alt"></i> ${entry.zone_name}</span>`;
        }
        if (entry.furniture_type_name) {
            prefsHtml += `<span class="waitlist-entry-pref"><i class="fas fa-umbrella-beach"></i> ${entry.furniture_type_name}</span>`;
        }
        if (entry.time_preference) {
            prefsHtml += `<span class="waitlist-entry-pref"><i class="fas fa-clock"></i> ${timePrefLabels[entry.time_preference]}</span>`;
        }
        if (entry.package_name) {
            prefsHtml += `<span class="waitlist-entry-pref"><i class="fas fa-box"></i> ${entry.package_name}</span>`;
        }

        let actionsHtml = '';
        if (showActions) {
            actionsHtml = `
                <div class="waitlist-entry-actions">
                    <button type="button" class="btn btn-sm btn-primary btn-convert" data-entry-id="${entry.id}">
                        <i class="fas fa-exchange-alt"></i> Convertir
                    </button>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button"
                                data-bs-toggle="dropdown" aria-expanded="false">
                            Estado
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" data-status="contacted">
                                <i class="fas fa-phone"></i> Contactado
                            </a></li>
                            <li><a class="dropdown-item" href="#" data-status="declined">
                                <i class="fas fa-times"></i> Rechazado
                            </a></li>
                            <li><a class="dropdown-item" href="#" data-status="no_answer">
                                <i class="fas fa-phone-slash"></i> Sin Respuesta
                            </a></li>
                        </ul>
                    </div>
                </div>
            `;
        } else {
            actionsHtml = `
                <div class="waitlist-entry-actions">
                    <span class="waitlist-status-badge ${entry.status}">${statusLabels[entry.status]}</span>
                </div>
            `;
        }

        return `
            <div class="waitlist-entry-card" data-entry-id="${entry.id}">
                <div class="waitlist-entry-header">
                    <span class="waitlist-entry-customer">${entry.customer_name}</span>
                    <span class="waitlist-entry-badge ${entry.customer_type}">
                        ${entry.customer_type === 'interno' ? 'Interno' : 'Externo'}
                    </span>
                </div>
                <div class="waitlist-entry-details">
                    ${entry.room_number ? `<i class="fas fa-door-open"></i> Hab. ${entry.room_number} · ` : ''}
                    <i class="fas fa-users"></i> ${entry.num_people} personas
                    ${entry.phone ? ` · <i class="fas fa-phone"></i> ${entry.phone}` : ''}
                </div>
                ${prefsHtml ? `<div class="waitlist-entry-prefs">${prefsHtml}</div>` : ''}
                <div class="waitlist-entry-time">
                    <i class="fas fa-clock"></i> ${timeAgo}
                </div>
                ${actionsHtml}
            </div>
        `;
    }

    _formatTimeAgo(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Ahora mismo';
        if (diffMins < 60) return `Hace ${diffMins} minuto${diffMins !== 1 ? 's' : ''}`;
        if (diffHours < 24) return `Hace ${diffHours} hora${diffHours !== 1 ? 's' : ''}`;
        return `Hace ${diffDays} día${diffDays !== 1 ? 's' : ''}`;
    }

    _switchTab(tab) {
        if (tab === 'pending') {
            this.tabPending?.classList.add('active');
            this.tabHistory?.classList.remove('active');
            this.pendingContent?.classList.add('active');
            this.historyContent?.classList.remove('active');
            if (this.historyContent) this.historyContent.style.display = 'none';
            if (this.pendingContent) this.pendingContent.style.display = 'block';
        } else {
            this.tabHistory?.classList.add('active');
            this.tabPending?.classList.remove('active');
            this.historyContent?.classList.add('active');
            this.pendingContent?.classList.remove('active');
            if (this.pendingContent) this.pendingContent.style.display = 'none';
            if (this.historyContent) this.historyContent.style.display = 'block';
        }
    }

    _openAddModal() {
        // Reset form
        document.getElementById('waitlistCustomerId').value = '';
        document.getElementById('waitlistDate').value = this.currentDate;
        document.getElementById('waitlistNumPeople').value = 2;
        document.getElementById('waitlistTimePref').value = '';
        document.getElementById('waitlistNotes').value = '';
        document.getElementById('waitlistTypeExterno').checked = true;
        document.getElementById('waitlistResIncluido').checked = true;

        this._toggleCustomerType('externo');
        this._toggleResType('incluido');
        this._clearCustomer();
        this._hideError();

        // Show modal
        const modal = bootstrap.Modal.getOrCreateInstance(this.modal);
        modal.show();
    }

    _toggleCustomerType(type) {
        const internoSearch = document.getElementById('waitlistInternoSearch');
        const externoSearch = document.getElementById('waitlistExternoSearch');

        if (type === 'interno') {
            internoSearch.style.display = 'block';
            externoSearch.style.display = 'none';
        } else {
            internoSearch.style.display = 'none';
            externoSearch.style.display = 'block';
        }

        this._clearCustomer();
    }

    _toggleResType(type) {
        const packageSelect = document.getElementById('waitlistPackageSelect');
        packageSelect.style.display = type === 'paquete' ? 'block' : 'none';
    }

    _clearCustomer() {
        document.getElementById('waitlistCustomerId').value = '';
        document.getElementById('waitlistCustomerSelected').style.display = 'none';
        document.getElementById('waitlistRoomNumber').value = '';
        document.getElementById('waitlistCustomerSearch').value = '';
    }

    _showError(message) {
        if (this.errorDisplay) {
            this.errorDisplay.textContent = message;
            this.errorDisplay.style.display = 'block';
        }
    }

    _hideError() {
        if (this.errorDisplay) {
            this.errorDisplay.style.display = 'none';
        }
    }

    async _saveEntry() {
        const customerId = document.getElementById('waitlistCustomerId').value;
        if (!customerId) {
            this._showError('Debe seleccionar un cliente');
            return;
        }

        const resType = document.querySelector('input[name="waitlistResType"]:checked')?.value;
        const packageId = document.getElementById('waitlistPackageId')?.value;

        if (resType === 'paquete' && !packageId) {
            this._showError('Debe seleccionar un paquete');
            return;
        }

        const data = {
            customer_id: parseInt(customerId),
            requested_date: document.getElementById('waitlistDate').value,
            num_people: parseInt(document.getElementById('waitlistNumPeople').value),
            time_preference: document.getElementById('waitlistTimePref').value || null,
            preferred_zone_id: document.getElementById('waitlistZone')?.value || null,
            preferred_furniture_type_id: document.getElementById('waitlistFurnitureType')?.value || null,
            reservation_type: resType,
            package_id: packageId ? parseInt(packageId) : null,
            notes: document.getElementById('waitlistNotes').value || null
        };

        try {
            this.saveBtn.disabled = true;

            const response = await fetch('/beach/api/waitlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                bootstrap.Modal.getInstance(this.modal)?.hide();
                await this.refresh();
                this._dispatchCountUpdate();
            } else {
                this._showError(result.error || 'Error al guardar');
            }
        } catch (error) {
            console.error('Error saving entry:', error);
            this._showError('Error de conexión');
        } finally {
            this.saveBtn.disabled = false;
        }
    }

    async _handleStatusChange(entryId, status) {
        try {
            const response = await fetch(`/beach/api/waitlist/${entryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify({ status })
            });

            const result = await response.json();

            if (result.success) {
                await this.refresh();
                this._dispatchCountUpdate();
            } else {
                console.error('Error updating status:', result.error);
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }

    async _handleConvert(entryId) {
        // Get entry data for pre-filling
        try {
            const response = await fetch(`/beach/api/waitlist/${entryId}`);
            const data = await response.json();

            if (data.success && this.onConvert) {
                this.close();
                this.onConvert(data.entry);
            }
        } catch (error) {
            console.error('Error getting entry for conversion:', error);
        }
    }

    _dispatchCountUpdate() {
        // Dispatch event so map can update badge
        window.dispatchEvent(new CustomEvent('waitlistCountUpdated', {
            detail: { date: this.currentDate }
        }));
    }
}
```

**Step 2: Commit**

```bash
git add static/js/WaitlistManager.js
git commit -m "feat(waitlist): add JavaScript module for panel management

- Create WaitlistManager class with ES6 module pattern
- Implement panel open/close with keyboard support
- Implement tab switching (pending/history)
- Implement entry rendering with action buttons
- Implement add entry modal with validation
- Implement status change and convert handlers
- Add count update event dispatch for badge sync

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Map Integration

**Files:**
- Modify: `templates/beach/map.html` (add toolbar button + include panel)
- Modify: `static/js/MapManager.js` or equivalent (integrate WaitlistManager)

**Step 1: Add toolbar button and panel include to map template**

Find the map toolbar section in `templates/beach/map.html` and add after existing buttons:

```html
<!-- Waitlist Button -->
<button type="button" class="map-control-btn waitlist-toolbar-btn" id="waitlistToolbarBtn"
        title="Lista de Espera" aria-label="Abrir lista de espera">
    <i class="fas fa-clock"></i>
    <span class="waitlist-badge" id="waitlistToolbarBadge" data-count="0"></span>
</button>
```

Before closing `</body>`, add:

```html
<!-- Waitlist Panel -->
{% include 'beach/_waitlist_panel.html' %}

<!-- Waitlist CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/waitlist.css') }}">
```

**Step 2: Initialize WaitlistManager in map JavaScript**

In the map's JavaScript initialization, add:

```javascript
import { WaitlistManager } from './WaitlistManager.js';

// Initialize waitlist manager
const waitlistManager = new WaitlistManager({
    currentDate: currentMapDate,
    onConvert: (entry) => {
        // Open new reservation panel with pre-filled data
        openNewReservationPanel({
            customerId: entry.customer_id,
            customerName: entry.customer_name,
            customerType: entry.customer_type,
            numPeople: entry.num_people,
            preferredZoneId: entry.preferred_zone_id,
            preferredFurnitureTypeId: entry.preferred_furniture_type_id,
            reservationType: entry.reservation_type,
            packageId: entry.package_id,
            notes: entry.notes,
            waitlistEntryId: entry.id  // For linking after creation
        });
    }
});

// Toolbar button click
document.getElementById('waitlistToolbarBtn')?.addEventListener('click', () => {
    waitlistManager.open();
});

// Update waitlist badge when date changes
function updateWaitlistBadge() {
    waitlistManager.setDate(currentMapDate);
    waitlistManager.getCount().then(count => {
        const badge = document.getElementById('waitlistToolbarBadge');
        if (badge) {
            badge.textContent = count;
            badge.dataset.count = count;
        }
    });
}

// Call on date change
// (integrate with existing date navigation)

// Listen for count updates
window.addEventListener('waitlistCountUpdated', () => {
    updateWaitlistBadge();
});
```

**Step 3: Run all tests**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/ -q --tb=short`

Expected: All tests pass

**Step 4: Commit**

```bash
git add templates/beach/map.html static/js/MapManager.js
git commit -m "feat(waitlist): integrate waitlist into map toolbar

- Add waitlist button to map toolbar with badge
- Include waitlist panel template
- Initialize WaitlistManager with date sync
- Wire up convert callback to pre-fill reservation panel
- Add badge update on date change and count events

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Convert Flow Integration

**Files:**
- Modify: `static/js/NewReservationPanel.js` or equivalent

**Step 1: Add waitlist entry ID tracking**

Add hidden field to track waitlist entry being converted:

```javascript
// In reservation panel, add property
this.waitlistEntryId = null;

// Method to set from waitlist
setFromWaitlist(data) {
    this.waitlistEntryId = data.waitlistEntryId;

    // Pre-fill customer
    this.setCustomer(data.customerId, data.customerName, data.customerType);

    // Pre-fill num people
    document.getElementById('newPanelNumPeople').value = data.numPeople;

    // Pre-fill preferences (zone, furniture type selections)
    if (data.preferredZoneId) {
        // Set zone filter if applicable
    }
    if (data.preferredFurnitureTypeId) {
        // Filter furniture by type if applicable
    }

    // Pre-fill reservation type
    if (data.reservationType) {
        document.querySelector(`input[name="resType"][value="${data.reservationType}"]`)?.click();
    }

    // Pre-fill notes
    if (data.notes) {
        document.getElementById('newPanelObservations').value = data.notes;
    }
}
```

**Step 2: After successful reservation creation, mark waitlist converted**

In reservation creation success handler:

```javascript
// After reservation created successfully
if (this.waitlistEntryId) {
    fetch(`/beach/api/waitlist/${this.waitlistEntryId}/convert`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
        },
        body: JSON.stringify({ reservation_id: newReservationId })
    }).then(() => {
        this.waitlistEntryId = null;
        window.dispatchEvent(new CustomEvent('waitlistCountUpdated'));
    });
}
```

**Step 3: Commit**

```bash
git add static/js/NewReservationPanel.js
git commit -m "feat(waitlist): integrate convert flow with reservation panel

- Add waitlistEntryId tracking to reservation panel
- Add setFromWaitlist method for pre-filling
- Mark waitlist entry as converted after reservation success
- Dispatch count update event after conversion

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Auto-Expire on Startup

**Files:**
- Modify: `app.py` or `blueprints/beach/__init__.py`

**Step 1: Call expire on app startup**

In app initialization (after database init):

```python
# In app.py or blueprint init
from models.waitlist import expire_old_entries

# After init_db() or in before_first_request
def expire_waitlist_entries():
    """Expire old waitlist entries on startup."""
    try:
        count = expire_old_entries()
        if count > 0:
            print(f"  Expired {count} old waitlist entries")
    except Exception as e:
        print(f"  Warning: Could not expire waitlist entries: {e}")

# Call during initialization
expire_waitlist_entries()
```

**Step 2: Run all tests**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/ -q --tb=short`

Expected: All tests pass

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat(waitlist): add auto-expire on app startup

- Call expire_old_entries during app initialization
- Log count of expired entries

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Final Testing and Cleanup

**Files:**
- Run all tests
- Manual testing checklist

**Step 1: Run full test suite**

Run: `cd .worktrees/feature-waitlist && python -m pytest tests/ -v`

Expected: All tests pass

**Step 2: Manual testing checklist**

- [ ] Open map, see waitlist button in toolbar
- [ ] Click button, panel opens
- [ ] Badge shows 0 when no entries
- [ ] Click "Añadir", modal opens
- [ ] Select interno customer via room lookup
- [ ] Select externo customer via search
- [ ] Fill all fields, save entry
- [ ] Badge increments, entry appears in panel
- [ ] Change status via dropdown
- [ ] Entry moves to history tab
- [ ] Click convert, reservation panel opens pre-filled
- [ ] Complete reservation, waitlist entry marked converted
- [ ] Change date, badge updates
- [ ] Panel shows entries for selected date only

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(waitlist): complete implementation

Phase 7a Live Map Enhancement - Waiting List feature complete:
- Database migration with indexes
- Model layer with full CRUD + validation
- REST API with all endpoints
- Slide-out panel with tabs (pending/history)
- Add entry modal with customer search
- Status management (contacted/declined/no_answer)
- Convert to reservation flow
- Auto-expire past entries
- Badge counter on toolbar

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Database migration | `database/migrations/waitlist.py`, `__init__.py` |
| 2 | Model - Basic CRUD | `models/waitlist.py`, `tests/test_waitlist.py` |
| 3 | Model - Read operations | `models/waitlist.py`, `tests/test_waitlist.py` |
| 4 | Model - Convert/Expire | `models/waitlist.py`, `tests/test_waitlist.py` |
| 5 | API endpoints | `blueprints/beach/routes/api/waitlist.py` |
| 6 | Panel template + CSS | `templates/beach/_waitlist_panel.html`, `static/css/waitlist.css` |
| 7 | JavaScript module | `static/js/WaitlistManager.js` |
| 8 | Map integration | `templates/beach/map.html`, map JS |
| 9 | Convert flow | `static/js/NewReservationPanel.js` |
| 10 | Auto-expire | `app.py` |
| 11 | Final testing | All files |

**Total estimated tasks:** 11 (with ~50 bite-sized steps)
