# Simulation Bug Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two bugs found by the stress-test health check: furniture blocks that silently overlap active reservations (#45), and reservations that get committed to the DB without furniture when availability is rejected (#46).

**Architecture:** Bug #45 — add a conflict pre-check inside `create_furniture_block` using the same connection, before the INSERT. Bug #46 — refactor `check_furniture_availability_bulk` to accept an optional `conn` parameter so callers inside an active `BEGIN IMMEDIATE` transaction can pass their connection directly, preventing the nested `with get_db() as conn:` context-manager exit from prematurely committing the outer transaction.

**Tech Stack:** Python 3.11, SQLite 3 (WAL mode), Flask 3 (`flask.g` single-connection-per-context), pytest

---

## Background: Why Bug #46 Happens

`get_db()` always returns **the same** `g.db` connection within a Flask app context. Python's `sqlite3.Connection` context manager calls `conn.commit()` on a normal exit. So when `create_beach_reservation` holds an open `BEGIN IMMEDIATE` transaction and calls `check_furniture_availability_bulk`, which internally does `with get_db() as conn:` (same `g.db`), the inner `with` exit **commits the outer partial transaction** (reservation row, no furniture yet). If the availability check then finds the furniture is taken, the `conn.rollback()` is a **no-op** — the reservation is already in the DB without any furniture assignment.

The fix: always pass the outer `conn` into the availability check so no nested context manager fires.

---

## Task 1: Fix Bug #45 — Conflict check in `create_furniture_block`

**Files:**
- Modify: `models/furniture_block.py:59-67`
- Test: `tests/test_furniture_lock.py` (append new class)

**Step 1: Write the failing test**

Append this class to `tests/test_furniture_lock.py`:

```python
class TestCreateFurnitureBlockConflict:
    """Block creation must reject furniture that has active reservations in the date range."""

    def _create_furniture(self, conn, zone_id: int, number: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active) "
            "VALUES (?, ?, 'hamaca', 2, 1)",
            (number, zone_id)
        )
        return cursor.lastrowid

    def _create_customer(self, conn, email: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_customers "
            "(first_name, last_name, customer_type, email, phone, created_at) "
            "VALUES ('Block', 'Test', 'externo', ?, '600000001', datetime('now'))",
            (email,)
        )
        return cursor.lastrowid

    def _assign_furniture(self, conn, furniture_id: int, date: str) -> None:
        """Create a minimal Confirmada reservation with furniture on `date`."""
        cust_id = self._create_customer(conn, f'blk_{date}_{furniture_id}@test.com')
        cursor = conn.execute(
            "INSERT INTO beach_reservations "
            "(customer_id, ticket_number, reservation_date, start_date, end_date, "
            " num_people, current_state, current_states, state_id, "
            " reservation_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, 2, 'Confirmada', 'Confirmada', 1, 'normal', datetime('now'))",
            (cust_id, f'BLKTEST{furniture_id}{date.replace("-","")}',
             date, date, date)
        )
        res_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date) "
            "VALUES (?, ?, ?)",
            (res_id, furniture_id, date)
        )
        conn.commit()

    def test_raises_when_active_reservation_exists_in_range(self, app):
        """create_furniture_block must raise ValueError when furniture is already reserved."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKCONFLICT01')
            db.commit()

            # Create a Confirmada reservation for '2026-07-10'
            self._assign_furniture(db, furniture_id, '2026-07-10')

            # Block overlapping that date must raise
            with pytest.raises(ValueError, match="reservas activas"):
                create_furniture_block(
                    furniture_id=furniture_id,
                    start_date='2026-07-08',
                    end_date='2026-07-12',
                    block_type='maintenance',
                    created_by='test'
                )

    def test_succeeds_when_only_releasing_state_reservations_exist(self, app):
        """Block should be allowed when conflicting reservations are all Cancelada/No-Show/Liberada."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKNOCONFLICT01')
            cust_id = self._create_customer(db, 'blk_releasing@test.com')
            db.commit()

            # Create a Cancelada reservation on '2026-08-05'
            cursor.execute(
                "INSERT INTO beach_reservations "
                "(customer_id, ticket_number, reservation_date, start_date, end_date, "
                " num_people, current_state, current_states, state_id, "
                " reservation_type, created_at) "
                "VALUES (?, 'BLKREL01', '2026-08-05', '2026-08-05', '2026-08-05', "
                "        2, 'Cancelada', 'Cancelada', 1, 'normal', datetime('now'))",
                (cust_id,)
            )
            res_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date) "
                "VALUES (?, ?, '2026-08-05')",
                (res_id, furniture_id)
            )
            db.commit()

            # Block on the same range must succeed (Cancelada is a releasing state)
            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date='2026-08-01',
                end_date='2026-08-10',
                block_type='maintenance',
                created_by='test'
            )
            assert isinstance(block_id, int)
            assert block_id > 0

    def test_succeeds_when_no_reservations_in_range(self, app):
        """Block must succeed when no reservations exist in the date range."""
        from models.furniture_block import create_furniture_block

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._create_furniture(db, zone_id, 'BLKEMPTY01')
            db.commit()

            block_id = create_furniture_block(
                furniture_id=furniture_id,
                start_date='2026-09-01',
                end_date='2026-09-05',
                block_type='vip_hold',
                created_by='test'
            )
            assert isinstance(block_id, int)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_furniture_lock.py::TestCreateFurnitureBlockConflict -v
```

Expected: FAIL — `create_furniture_block` does not raise, test `test_raises_when_active_reservation_exists_in_range` fails.

**Step 3: Implement the fix in `models/furniture_block.py`**

Replace the `with get_db() as conn:` block (lines 59-67) with:

```python
    with get_db() as conn:
        # Fetch releasing states directly on this connection (avoids nested context manager)
        releasing_rows = conn.execute(
            'SELECT name FROM beach_reservation_states WHERE is_availability_releasing = 1'
        ).fetchall()
        releasing_states = [row['name'] for row in releasing_rows]

        # Check for active reservations that would conflict with this block
        if releasing_states:
            placeholders = ','.join('?' * len(releasing_states))
            conflict_query = f'''
                SELECT r.ticket_number
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                WHERE rf.furniture_id = ?
                  AND rf.assignment_date BETWEEN ? AND ?
                  AND r.current_state NOT IN ({placeholders})
                LIMIT 5
            '''
            conflicts = conn.execute(
                conflict_query,
                [furniture_id, start_date, end_date] + releasing_states
            ).fetchall()
        else:
            conflicts = conn.execute('''
                SELECT r.ticket_number
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                WHERE rf.furniture_id = ?
                  AND rf.assignment_date BETWEEN ? AND ?
                LIMIT 5
            ''', (furniture_id, start_date, end_date)).fetchall()

        if conflicts:
            tickets = ', '.join(row['ticket_number'] for row in conflicts)
            raise ValueError(f"Mobiliario con reservas activas en estas fechas: {tickets}")

        cursor = conn.execute('''
            INSERT INTO beach_furniture_blocks
            (furniture_id, start_date, end_date, block_type, reason, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (furniture_id, start_date, end_date, block_type, reason, notes, created_by))

        conn.commit()
        return cursor.lastrowid
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_furniture_lock.py::TestCreateFurnitureBlockConflict -v
```

Expected: 3 PASS.

**Step 5: Run full test suite to check for regressions**

```bash
python -m pytest tests/ -x -q
```

Expected: All previously passing tests still pass.

**Step 6: Commit**

```bash
git add models/furniture_block.py tests/test_furniture_lock.py
git commit -m "fix: add active-reservation conflict check to create_furniture_block (closes #45)"
```

---

## Task 2: Refactor `check_furniture_availability_bulk` to accept optional `conn`

**Files:**
- Modify: `models/reservation_availability.py:16-118`
- Test: `tests/test_availability.py` (append new test)

**Step 1: Write the failing test**

Append to `tests/test_availability.py`:

```python
class TestCheckFurnitureAvailabilityBulkWithConn:
    """check_furniture_availability_bulk must work identically with and without conn param."""

    def test_accepts_conn_parameter_and_returns_same_result(self, app, setup_test_data):
        """Passing conn= should produce identical results to calling without conn."""
        from models.reservation_availability import check_furniture_availability_bulk

        furniture_id = setup_test_data['furniture_id_1']

        with app.app_context():
            # Without conn (standalone)
            result_standalone = check_furniture_availability_bulk(
                furniture_ids=[furniture_id],
                dates=['2099-01-15']
            )

            # With conn (simulating outer transaction)
            db = get_db()
            result_with_conn = check_furniture_availability_bulk(
                furniture_ids=[furniture_id],
                dates=['2099-01-15'],
                conn=db
            )

            assert result_standalone['all_available'] == result_with_conn['all_available']
            assert result_standalone['unavailable'] == result_with_conn['unavailable']

    def test_with_conn_detects_conflict_correctly(self, app, setup_test_data):
        """When called with conn=, conflicts are still detected correctly."""
        from models.reservation_availability import check_furniture_availability_bulk

        furniture_id = setup_test_data['furniture_id_1']
        reservation_date = setup_test_data['date_1']

        with app.app_context():
            db = get_db()
            result = check_furniture_availability_bulk(
                furniture_ids=[furniture_id],
                dates=[reservation_date],
                conn=db
            )
            # furniture_id_1 has a Confirmada reservation on date_1 (from setup_test_data)
            assert result['all_available'] is False
            assert len(result['unavailable']) == 1
            assert result['unavailable'][0]['furniture_id'] == furniture_id
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_availability.py::TestCheckFurnitureAvailabilityBulkWithConn -v
```

Expected: FAIL — `check_furniture_availability_bulk` does not accept `conn` parameter.

**Step 3: Refactor `models/reservation_availability.py`**

Replace the entire `check_furniture_availability_bulk` function (lines 16-118) with:

```python
def _check_availability_with_conn(
    conn,
    releasing_states: list,
    furniture_ids: list,
    dates: list,
    exclude_reservation_id: int = None
) -> dict:
    """
    Execute the availability query on an existing connection.
    Extracted to avoid code duplication and nested context manager issues.
    """
    cursor = conn.cursor()

    placeholders_furniture = ','.join('?' * len(furniture_ids))
    placeholders_dates = ','.join('?' * len(dates))

    query = f'''
        SELECT rf.furniture_id, rf.assignment_date, r.id as reservation_id,
               r.ticket_number, r.current_state,
               f.number as furniture_number,
               c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
               c.room_number
        FROM beach_reservation_furniture rf
        JOIN beach_reservations r ON rf.reservation_id = r.id
        JOIN beach_customers c ON r.customer_id = c.id
        JOIN beach_furniture f ON rf.furniture_id = f.id
        WHERE rf.furniture_id IN ({placeholders_furniture})
          AND rf.assignment_date IN ({placeholders_dates})
    '''
    params = list(furniture_ids) + list(dates)

    if releasing_states:
        placeholders_states = ','.join('?' * len(releasing_states))
        query += f' AND r.current_state NOT IN ({placeholders_states})'
        params.extend(releasing_states)

    if exclude_reservation_id:
        query += ' AND r.id != ?'
        params.append(exclude_reservation_id)

    cursor.execute(query, params)
    conflicts = cursor.fetchall()

    unavailable = []
    conflict_set = set()

    for row in conflicts:
        assignment_date = row['assignment_date']
        if hasattr(assignment_date, 'strftime'):
            assignment_date = assignment_date.strftime('%Y-%m-%d')
        unavailable.append({
            'furniture_id': row['furniture_id'],
            'furniture_number': row['furniture_number'],
            'date': assignment_date,
            'reservation_id': row['reservation_id'],
            'ticket_number': row['ticket_number'],
            'customer_name': row['customer_name'],
            'room_number': row['room_number']
        })
        conflict_set.add((row['furniture_id'], assignment_date))

    availability_matrix = {}
    for date in dates:
        availability_matrix[date] = {}
        for furn_id in furniture_ids:
            availability_matrix[date][furn_id] = (furn_id, date) not in conflict_set

    return {
        'all_available': len(unavailable) == 0,
        'unavailable': unavailable,
        'availability_matrix': availability_matrix
    }


def check_furniture_availability_bulk(
    furniture_ids: list,
    dates: list,
    exclude_reservation_id: int = None,
    conn=None
) -> dict:
    """
    Check availability of multiple furniture items for multiple dates.
    More efficient than calling check_furniture_availability() in a loop.

    Args:
        furniture_ids: List of furniture IDs to check
        dates: List of dates (YYYY-MM-DD strings)
        exclude_reservation_id: Reservation ID to exclude (for updates)
        conn: Optional existing db connection. When provided, uses it directly
              without opening a new context manager — prevents nested
              with-get_db() commits from prematurely committing an outer
              BEGIN IMMEDIATE transaction.

    Returns:
        dict: {
            'all_available': bool,
            'unavailable': [
                {'furniture_id': int, 'date': str, 'reservation_id': int,
                 'ticket_number': str, 'customer_name': str}
            ],
            'availability_matrix': {
                'YYYY-MM-DD': {furniture_id: bool, ...}
            }
        }
    """
    if not furniture_ids or not dates:
        return {
            'all_available': True,
            'unavailable': [],
            'availability_matrix': {}
        }

    if conn is not None:
        # Use provided connection — fetch releasing states on the same conn
        # to avoid any nested context manager that would commit the outer transaction.
        rows = conn.execute(
            'SELECT name FROM beach_reservation_states WHERE is_availability_releasing = 1'
        ).fetchall()
        releasing_states = [row['name'] for row in rows]
        return _check_availability_with_conn(
            conn, releasing_states, furniture_ids, dates, exclude_reservation_id
        )

    # Standalone call: safe to fetch releasing states separately, then open our own conn.
    releasing_states = get_active_releasing_states()
    with get_db() as inner_conn:
        return _check_availability_with_conn(
            inner_conn, releasing_states, furniture_ids, dates, exclude_reservation_id
        )
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_availability.py -v
```

Expected: All tests pass, including the two new ones.

**Step 5: Run full test suite**

```bash
python -m pytest tests/ -x -q
```

Expected: All tests pass.

**Step 6: Commit**

```bash
git add models/reservation_availability.py tests/test_availability.py
git commit -m "refactor: add optional conn param to check_furniture_availability_bulk to prevent nested commit"
```

---

## Task 3: Pass `conn` from `create_beach_reservation`

**Files:**
- Modify: `models/reservation_crud.py` (the `check_furniture_availability_bulk` call at ~line 234)
- Test: `tests/test_reservation.py` (append new test)

**Step 1: Write the failing test**

The test must show the current bug: when furniture is unavailable, `create_beach_reservation` leaves an orphaned reservation in the DB. After the fix it must not.

Append to `tests/test_reservation.py`:

```python
class TestNoOrphanedReservationOnUnavailableFurniture:
    """create_beach_reservation must not leave a reservation in the DB if furniture is taken."""

    def _make_furniture(self, conn, zone_id: int, number: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active) "
            "VALUES (?, ?, 'hamaca', 2, 1)",
            (number, zone_id)
        )
        return cursor.lastrowid

    def _make_customer(self, conn, email: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_customers "
            "(first_name, last_name, customer_type, email, phone, created_at) "
            "VALUES ('Orphan', 'Test', 'externo', ?, '600111222', datetime('now'))",
            (email,)
        )
        return cursor.lastrowid

    def test_no_orphaned_reservation_when_furniture_unavailable(self, app):
        """Second reservation attempt on taken furniture must not commit a bare reservation."""
        from models.reservation_crud import create_beach_reservation

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._make_furniture(db, zone_id, 'ORPHANTEST01')
            cust1 = self._make_customer(db, 'orphan_cust1@test.com')
            cust2 = self._make_customer(db, 'orphan_cust2@test.com')
            db.commit()

            # First reservation takes the furniture — must succeed
            res_id_1, _ = create_beach_reservation(
                customer_id=cust1,
                reservation_date='2099-06-15',
                num_people=2,
                furniture_ids=[furniture_id],
                created_by='test'
            )
            assert res_id_1 is not None

            # Count total reservations now
            cursor.execute('SELECT COUNT(*) as cnt FROM beach_reservations')
            count_before = cursor.fetchone()['cnt']

            # Second reservation on the same furniture/date must raise
            with pytest.raises(ValueError):
                create_beach_reservation(
                    customer_id=cust2,
                    reservation_date='2099-06-15',
                    num_people=2,
                    furniture_ids=[furniture_id],
                    created_by='test'
                )

            # Must not have created any extra reservation (no orphan)
            cursor.execute('SELECT COUNT(*) as cnt FROM beach_reservations')
            count_after = cursor.fetchone()['cnt']
            assert count_after == count_before, (
                f"Orphaned reservation(s) left in DB: {count_after - count_before} extra"
            )
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest "tests/test_reservation.py::TestNoOrphanedReservationOnUnavailableFurniture" -v
```

Expected: FAIL — `count_after > count_before` (orphaned reservation exists).

**Step 3: Fix `models/reservation_crud.py`**

Find the call to `check_furniture_availability_bulk` inside `create_beach_reservation` (around line 234). Change it to pass `conn=conn`:

```python
            # Assign furniture (with availability check inside transaction lock)
            if furniture_ids:
                # Pass conn= so the check runs on the same connection/transaction.
                # Without this, the nested with-get_db() exit would prematurely commit
                # the outer BEGIN IMMEDIATE, leaving an orphaned reservation if furniture
                # turns out to be unavailable.
                availability = check_furniture_availability_bulk(
                    furniture_ids=furniture_ids,
                    dates=[reservation_date],
                    exclude_reservation_id=None,
                    conn=conn
                )
                if not availability.get('all_available'):
                    unavail_items = availability.get('unavailable', [])
                    conflict_ids = list(set(
                        item['furniture_id'] for item in unavail_items
                    ))
                    conn.rollback()
                    raise ValueError(f"Mobiliario no disponible: {conflict_ids}")

                for furniture_id in furniture_ids:
                    cursor.execute('''
                        INSERT INTO beach_reservation_furniture
                        (reservation_id, furniture_id, assignment_date)
                        VALUES (?, ?, ?)
                    ''', (reservation_id, furniture_id, reservation_date))
```

The only change is adding `conn=conn` to the `check_furniture_availability_bulk(...)` call. Everything else stays the same.

**Step 4: Run test to verify it passes**

```bash
python -m pytest "tests/test_reservation.py::TestNoOrphanedReservationOnUnavailableFurniture" -v
```

Expected: PASS.

**Step 5: Run full test suite**

```bash
python -m pytest tests/ -x -q
```

Expected: All tests pass.

**Step 6: Commit**

```bash
git add models/reservation_crud.py tests/test_reservation.py
git commit -m "fix: pass conn to check_furniture_availability_bulk in create_beach_reservation (closes #46)"
```

---

## Task 4: Pass `conn` from `create_linked_multiday_reservations`

**Files:**
- Modify: `models/reservation_multiday.py` (two calls to `check_furniture_availability_bulk` at ~lines 140 and 149)

The multiday function has the same nested-context-manager problem. Fix it by passing the outer `conn`.

**Step 1: Write the failing test**

Append to `tests/test_reservation.py`:

```python
class TestNoOrphanedMultidayReservationOnUnavailableFurniture:
    """create_linked_multiday_reservations must not leave orphans when furniture is taken."""

    def _make_furniture(self, conn, zone_id: int, number: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active) "
            "VALUES (?, ?, 'hamaca', 2, 1)",
            (number, zone_id)
        )
        return cursor.lastrowid

    def _make_customer(self, conn, email: str) -> int:
        cursor = conn.execute(
            "INSERT INTO beach_customers "
            "(first_name, last_name, customer_type, email, phone, created_at) "
            "VALUES ('Multi', 'Test', 'externo', ?, '600333444', datetime('now'))",
            (email,)
        )
        return cursor.lastrowid

    def test_no_orphaned_reservation_when_multiday_furniture_unavailable(self, app):
        """Multiday creation must roll back fully when any date's furniture is taken."""
        from models.reservation_crud import create_beach_reservation
        from models.reservation_multiday import create_linked_multiday_reservations

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT id FROM beach_zones LIMIT 1')
            zone_id = cursor.fetchone()['id']

            furniture_id = self._make_furniture(db, zone_id, 'MULTIORPHAN01')
            cust1 = self._make_customer(db, 'multi_cust1@test.com')
            cust2 = self._make_customer(db, 'multi_cust2@test.com')
            db.commit()

            # Block furniture on day 3 of the range with a single-day reservation
            create_beach_reservation(
                customer_id=cust1,
                reservation_date='2099-07-17',
                num_people=2,
                furniture_ids=[furniture_id],
                created_by='test'
            )

            cursor.execute('SELECT COUNT(*) as cnt FROM beach_reservations')
            count_before = cursor.fetchone()['cnt']

            # Multiday reservation spanning 2099-07-15 to 2099-07-19 must fail
            # because furniture is taken on 2099-07-17
            result = create_linked_multiday_reservations(
                customer_id=cust2,
                dates=['2099-07-15', '2099-07-16', '2099-07-17', '2099-07-18', '2099-07-19'],
                num_people=2,
                furniture_ids=[furniture_id],
                created_by='test',
                validate_availability=True,
                validate_duplicates=False
            )
            assert result['success'] is False

            # No orphaned reservations must exist
            cursor.execute('SELECT COUNT(*) as cnt FROM beach_reservations')
            count_after = cursor.fetchone()['cnt']
            assert count_after == count_before, (
                f"Orphaned multiday reservation(s) in DB: {count_after - count_before} extra"
            )
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest "tests/test_reservation.py::TestNoOrphanedMultidayReservationOnUnavailableFurniture" -v
```

Expected: FAIL or ERROR (multiday raises instead of returning `{'success': False}` in some code paths — either way, orphaned reservations may exist).

**Step 3: Fix `models/reservation_multiday.py`**

Find the two `check_furniture_availability_bulk` calls inside the `BEGIN IMMEDIATE` block (~lines 140 and 149). Add `conn=conn` to both:

```python
            # Validate availability (inside transaction lock)
            if validate_availability:
                if furniture_by_date and furniture_ids is None:
                    for date, date_furniture_ids in furniture_by_date.items():
                        avail_result = check_furniture_availability_bulk(
                            date_furniture_ids, [date], conn=conn
                        )
                        if not avail_result['all_available']:
                            unavail = avail_result['unavailable'][0]
                            raise ValueError(
                                f"Mobiliario {unavail['furniture_id']} no disponible el {unavail['date']} "
                                f"(reserva {unavail['ticket_number']})"
                            )
                else:
                    avail_result = check_furniture_availability_bulk(
                        all_furniture_ids, dates, conn=conn
                    )
                    if not avail_result['all_available']:
                        unavail = avail_result['unavailable'][0]
                        raise ValueError(
                            f"Mobiliario {unavail['furniture_id']} no disponible el {unavail['date']} "
                            f"(reserva {unavail['ticket_number']})"
                        )
```

The only change is adding `conn=conn` to both calls. Everything else stays the same.

Also check how `create_linked_multiday_reservations` handles its exceptions — if it raises rather than returning `{'success': False}`, update the test to use `pytest.raises(ValueError)` and check the count similarly.

**Step 4: Run test to verify it passes**

```bash
python -m pytest "tests/test_reservation.py::TestNoOrphanedMultidayReservationOnUnavailableFurniture" -v
```

Expected: PASS (adjust test if multiday raises instead of returning success=False — see step 3 note).

**Step 5: Run full test suite**

```bash
python -m pytest tests/ -x -q
```

Expected: All tests pass.

**Step 6: Commit**

```bash
git add models/reservation_multiday.py tests/test_reservation.py
git commit -m "fix: pass conn to check_furniture_availability_bulk in create_linked_multiday_reservations"
```

---

## Task 5: Verify fixes with health check on sim DB

**Files:** None modified — verification only.

**Step 1: Re-run health check**

```bash
python scripts/health_check.py --sim-db
```

**Step 2: Confirm Bug #45 is resolved**

Expected output line:
```
[OK]  Furniture blocks overlapping active reservations
```
(Was: `[FAIL] Furniture blocks overlapping active reservations — 5 issues`)

Note: The sim DB already has the old block overlap — the fix prevents *future* blocks from conflicting. The existing overlap in the sim DB is historical data. If the health check still shows the old 5 issues, that is expected — they were created before the fix. Verify the fix works by checking the test suite instead.

**Step 3: Confirm Bug #46 is resolved**

Expected output line:
```
[OK]  Active reservations with no furniture assignment
```
(Was: `[WARN] Active reservations with no furniture assignment — 537 issues`)

Note: The sim DB retains the 537 existing orphaned reservations. The health check will still warn about them. To confirm the fix, run a quick targeted query on a fresh sim DB OR trust the unit tests from Task 3. Alternatively, reset the sim DB and re-run the simulation:

```bash
cp instance/beach_club.db database/beach_club_sim.db
python scripts/simulate_month.py --high-occupancy --month 2026-04 --sim-db
python scripts/health_check.py --sim-db
```

Expected: 0 missing-furniture reservations after a fresh simulation run.

**Step 4: Commit the updated report**

```bash
git add docs/simulation-report-*.md
git commit -m "docs: update health check report after bug fixes"
```
