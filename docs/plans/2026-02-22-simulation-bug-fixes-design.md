# Simulation Bug Fixes Design

**Date:** 2026-02-22
**Branch:** simulation/stress-test-2026-02
**Related Issues:** #45 (furniture block overlap), #46 (reservations without furniture)

---

## Bug #45 — Furniture blocks overlap active reservations

### Root Cause

`create_furniture_block()` in `models/furniture_block.py` inserts directly into
`beach_furniture_blocks` without first checking whether any active (non-releasing-state)
reservation already has the furniture assigned on any date within the requested range.

The simulation created block_id=22 on furniture_id=62 which overlapped with 5 existing
active reservations, surfaced as a FAIL by the health check.

### Fix: Pre-check conflict in `create_furniture_block`

Before the `INSERT INTO beach_furniture_blocks`, add a query using the same cursor/connection:

```sql
SELECT r.ticket_number, rf.assignment_date
FROM beach_reservation_furniture rf
JOIN beach_reservations r ON rf.reservation_id = r.id
WHERE rf.furniture_id = ?
  AND rf.assignment_date BETWEEN ? AND ?
  AND r.current_state NOT IN (<releasing_states>)
LIMIT 5
```

Releasing states are fetched via `get_active_releasing_states()` (same source of truth
as `check_furniture_availability_bulk`). If any conflicts are found, raise `ValueError`
with the conflicting ticket numbers.

**Files changed:** `models/furniture_block.py`

---

## Bug #46 — 537 reservations with no furniture assignment

### Root Cause

`get_db()` always returns the **same** `g.db` connection per Flask app context (stored in
`flask.g`). Inside `create_beach_reservation`, the code opens an explicit
`BEGIN IMMEDIATE` transaction, inserts the reservation row (uncommitted), then calls
`check_furniture_availability_bulk()`.

`check_furniture_availability_bulk` does `with get_db() as conn:` — the **same** `g.db`
connection. When that inner `with` block exits normally, Python's `sqlite3.Connection`
context manager protocol calls `conn.commit()`, **prematurely committing the partial outer
transaction** (reservation row exists, no furniture assigned yet).

When furniture is found to be unavailable, the subsequent `conn.rollback()` is a **no-op**
(the transaction is already committed), so the reservation stays in the DB without any
furniture assignment.

This was confirmed by querying the sim DB: all 537 orphaned reservations are in
`Confirmada` state and `created_by='simulation'`, matching exactly the code path where
the availability check raises `ValueError` after the premature commit.

### Fix: Pass outer connection to `check_furniture_availability_bulk`

**Step 1 — `models/reservation_availability.py`:**

Add optional `conn` parameter. Extract query logic into
`_check_availability_with_conn(conn, ...)`. When `conn` is provided, use it directly
(no context manager, no auto-commit). When `conn` is None, open normally via
`with get_db() as conn:`.

```python
def check_furniture_availability_bulk(
    furniture_ids, dates, exclude_reservation_id=None, conn=None
):
    if conn is not None:
        return _check_availability_with_conn(conn, furniture_ids, dates, exclude_reservation_id)
    with get_db() as conn:
        return _check_availability_with_conn(conn, furniture_ids, dates, exclude_reservation_id)
```

**Step 2 — `models/reservation_crud.py`:**

Inside `create_beach_reservation`, pass the outer `conn` to the availability check:

```python
availability = check_furniture_availability_bulk(
    furniture_ids=furniture_ids,
    dates=[reservation_date],
    exclude_reservation_id=None,
    conn=conn
)
```

**Step 3 — `models/reservation_multiday.py`:**

Inside `create_linked_multiday_reservations`, pass the outer `conn`:

```python
avail_result = check_furniture_availability_bulk(
    all_furniture_ids, dates, conn=conn
)
# and per-date variant:
avail_result = check_furniture_availability_bulk(
    date_furniture_ids, [date], conn=conn
)
```

**Files changed:** `models/reservation_availability.py`, `models/reservation_crud.py`,
`models/reservation_multiday.py`

---

## Testing Strategy

After each fix, re-run `python scripts/health_check.py --sim-db` and verify:
- Bug #45: "Furniture blocks overlapping active reservations" → OK (0 issues)
- Bug #46: "Active reservations with no furniture assignment" → OK (0 issues)

Unit tests should cover:
- `create_furniture_block` raises `ValueError` when active reservations exist in range
- `create_furniture_block` succeeds when only releasing-state reservations exist in range
- `create_beach_reservation` does NOT leave orphaned reservations when furniture is unavailable
- `check_furniture_availability_bulk` behaves identically with and without `conn` param
