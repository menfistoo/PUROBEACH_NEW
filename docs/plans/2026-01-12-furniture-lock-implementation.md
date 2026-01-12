# Furniture Lock Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lock feature to prevent accidental furniture reassignment for guaranteed reservations.

**Architecture:** Add `is_furniture_locked` column to `beach_reservations` table. Lock check happens at API level before any unassign/reassign operation. UI shows lock toggle in reservation panel and lock indicators on furniture in move mode.

**Tech Stack:** Flask/Python backend, SQLite, JavaScript ES6+ frontend, CSS with design system variables.

**Design Document:** `docs/plans/2026-01-12-furniture-lock-design.md`

---

## Task 1: Database Schema Migration

**Files:**
- Create: `migrations/add_furniture_lock.sql`
- Modify: `database/schema.py:364-380`

**Step 1: Create migration file**

```sql
-- migrations/add_furniture_lock.sql
-- Add furniture lock column to beach_reservations table
-- Allows locking furniture assignments to prevent accidental changes

ALTER TABLE beach_reservations
ADD COLUMN is_furniture_locked INTEGER DEFAULT 0;
```

**Step 2: Update schema.py**

In `database/schema.py`, find the `beach_reservations` CREATE TABLE statement (around line 364-380) and add the column after `updated_at`:

```python
    db.execute('''
        CREATE TABLE beach_reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES beach_customers(id),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            num_people INTEGER NOT NULL DEFAULT 1,
            state_id INTEGER REFERENCES beach_reservation_states(id),
            preferences TEXT,
            notes TEXT,
            internal_notes TEXT,
            source TEXT DEFAULT 'direct',
            parent_reservation_id INTEGER REFERENCES beach_reservations(id),
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_furniture_locked INTEGER DEFAULT 0
        )
    ''')
```

**Step 3: Run migration on existing database**

Run: `sqlite3 instance/beach_club.db < migrations/add_furniture_lock.sql`

**Step 4: Verify migration**

Run: `sqlite3 instance/beach_club.db "PRAGMA table_info(beach_reservations);" | grep is_furniture_locked`
Expected: `16|is_furniture_locked|INTEGER|0||0` (column number may vary)

**Step 5: Commit**

```bash
git add migrations/add_furniture_lock.sql database/schema.py
git commit -m "feat(db): add is_furniture_locked column to beach_reservations

Allows locking furniture assignments to prevent accidental changes
in move mode or reassignment flows."
```

---

## Task 2: Backend Model - Lock Toggle Function

**Files:**
- Modify: `models/reservation_crud.py`
- Create: `tests/test_furniture_lock.py`

**Step 1: Write the failing test**

Create `tests/test_furniture_lock.py`:

```python
"""
Tests for furniture lock feature.
"""

import pytest
from database import get_db


class TestFurnitureLockToggle:
    """Tests for toggling furniture lock on reservations."""

    def test_toggle_lock_on(self, app):
        """Should set is_furniture_locked to 1."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                # Create test reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people)
                    SELECT c.id, s.id, date('now'), date('now'), 2
                    FROM beach_customers c, beach_reservation_states s
                    LIMIT 1
                """)
                reservation_id = cursor.lastrowid
                conn.commit()

            # Toggle lock ON
            result = toggle_furniture_lock(reservation_id, locked=True)

            assert result['success'] is True
            assert result['is_furniture_locked'] is True

            # Verify in database
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
                    (reservation_id,)
                )
                row = cursor.fetchone()
                assert row['is_furniture_locked'] == 1

    def test_toggle_lock_off(self, app):
        """Should set is_furniture_locked to 0."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                # Create locked reservation
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked)
                    SELECT c.id, s.id, date('now'), date('now'), 2, 1
                    FROM beach_customers c, beach_reservation_states s
                    LIMIT 1
                """)
                reservation_id = cursor.lastrowid
                conn.commit()

            # Toggle lock OFF
            result = toggle_furniture_lock(reservation_id, locked=False)

            assert result['success'] is True
            assert result['is_furniture_locked'] is False

    def test_toggle_lock_nonexistent_reservation(self, app):
        """Should return error for nonexistent reservation."""
        from models.reservation_crud import toggle_furniture_lock

        with app.app_context():
            result = toggle_furniture_lock(99999, locked=True)

            assert result['success'] is False
            assert 'error' in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_furniture_lock.py::TestFurnitureLockToggle::test_toggle_lock_on -v`
Expected: FAIL with "cannot import name 'toggle_furniture_lock'"

**Step 3: Write minimal implementation**

Add to `models/reservation_crud.py` after the existing functions (around line 300+):

```python
# =============================================================================
# FURNITURE LOCK
# =============================================================================

def toggle_furniture_lock(reservation_id: int, locked: bool) -> dict:
    """
    Toggle the furniture lock status for a reservation.

    Args:
        reservation_id: The reservation ID
        locked: True to lock, False to unlock

    Returns:
        Dict with success status and new lock state
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check reservation exists
        cursor.execute(
            "SELECT id FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        if not cursor.fetchone():
            return {
                'success': False,
                'error': 'Reserva no encontrada'
            }

        # Update lock status
        cursor.execute(
            "UPDATE beach_reservations SET is_furniture_locked = ? WHERE id = ?",
            (1 if locked else 0, reservation_id)
        )
        conn.commit()

        return {
            'success': True,
            'is_furniture_locked': locked,
            'reservation_id': reservation_id
        }


def is_furniture_locked(reservation_id: int) -> bool:
    """
    Check if a reservation's furniture is locked.

    Args:
        reservation_id: The reservation ID

    Returns:
        True if locked, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        row = cursor.fetchone()
        return bool(row and row['is_furniture_locked'])
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_furniture_lock.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add models/reservation_crud.py tests/test_furniture_lock.py
git commit -m "feat(model): add toggle_furniture_lock and is_furniture_locked functions"
```

---

## Task 3: Backend Model - Lock Check in Move Mode

**Files:**
- Modify: `models/move_mode.py`
- Modify: `tests/test_furniture_lock.py`

**Step 1: Write the failing test**

Add to `tests/test_furniture_lock.py`:

```python
class TestMoveModeLockCheck:
    """Tests for lock checking in move mode operations."""

    def test_unassign_blocked_when_locked(self, app):
        """Should block unassign when reservation is locked."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                # Create locked reservation with furniture
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked)
                    SELECT c.id, s.id, date('now'), date('now'), 2, 1
                    FROM beach_customers c, beach_reservation_states s
                    LIMIT 1
                """)
                reservation_id = cursor.lastrowid

                # Assign furniture
                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()
                furniture_id = furniture['id']

                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, date('now'))
                """, (reservation_id, furniture_id))
                conn.commit()

                today = cursor.execute("SELECT date('now') as d").fetchone()['d']

            # Try to unassign - should be blocked
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=today
            )

            assert result['success'] is False
            assert result.get('error') == 'locked'

    def test_unassign_allowed_when_unlocked(self, app):
        """Should allow unassign when reservation is not locked."""
        from models.move_mode import unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                # Create unlocked reservation with furniture
                cursor.execute("""
                    INSERT INTO beach_reservations
                    (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked)
                    SELECT c.id, s.id, date('now'), date('now'), 2, 0
                    FROM beach_customers c, beach_reservation_states s
                    LIMIT 1
                """)
                reservation_id = cursor.lastrowid

                cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
                furniture = cursor.fetchone()
                furniture_id = furniture['id']

                cursor.execute("""
                    INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, date('now'))
                """, (reservation_id, furniture_id))
                conn.commit()

                today = cursor.execute("SELECT date('now') as d").fetchone()['d']

            # Unassign - should work
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=today
            )

            assert result['success'] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_furniture_lock.py::TestMoveModeLockCheck::test_unassign_blocked_when_locked -v`
Expected: FAIL (assertion error - currently returns success)

**Step 3: Modify unassign_furniture_for_date**

In `models/move_mode.py`, modify the `unassign_furniture_for_date` function to add lock check at the beginning:

```python
def unassign_furniture_for_date(
    reservation_id: int,
    furniture_ids: List[int],
    assignment_date: str
) -> Dict[str, Any]:
    """
    Unassign furniture from a reservation for a specific date.

    Args:
        reservation_id: The reservation to modify
        furniture_ids: List of furniture IDs to unassign
        assignment_date: Date in YYYY-MM-DD format

    Returns:
        Dict with success status and unassigned furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if reservation is locked
        cursor.execute(
            "SELECT is_furniture_locked FROM beach_reservations WHERE id = ?",
            (reservation_id,)
        )
        row = cursor.fetchone()
        if row and row['is_furniture_locked']:
            return {
                'success': False,
                'error': 'locked',
                'message': 'El mobiliario de esta reserva esta bloqueado'
            }

        unassigned = []
        for furniture_id in furniture_ids:
            cursor.execute("""
                DELETE FROM beach_reservation_furniture
                WHERE reservation_id = ?
                AND furniture_id = ?
                AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.rowcount > 0:
                unassigned.append(furniture_id)

        conn.commit()

        return {
            'success': True,
            'unassigned_count': len(unassigned),
            'furniture_ids': unassigned,
            'reservation_id': reservation_id,
            'date': assignment_date
        }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_furniture_lock.py::TestMoveModeLockCheck -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add models/move_mode.py tests/test_furniture_lock.py
git commit -m "feat(move-mode): block unassign when reservation furniture is locked"
```

---

## Task 4: Backend API - Toggle Lock Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_edit.py`
- Modify: `tests/test_furniture_lock.py`

**Step 1: Write the failing test**

Add to `tests/test_furniture_lock.py`:

```python
class TestToggleLockAPI:
    """Tests for the toggle lock API endpoint."""

    def test_toggle_lock_endpoint(self, client, auth_headers):
        """Should toggle lock via API."""
        from database import get_db

        # Create test reservation
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO beach_reservations
                (customer_id, state_id, start_date, end_date, num_people)
                SELECT c.id, s.id, date('now'), date('now'), 2
                FROM beach_customers c, beach_reservation_states s
                LIMIT 1
            """)
            reservation_id = cursor.lastrowid
            conn.commit()

        # Toggle lock ON
        response = client.patch(
            f'/beach/api/map/reservations/{reservation_id}/toggle-lock',
            json={'locked': True},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['is_furniture_locked'] is True

    def test_toggle_lock_requires_auth(self, client):
        """Should require authentication."""
        response = client.patch(
            '/beach/api/map/reservations/1/toggle-lock',
            json={'locked': True}
        )
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_furniture_lock.py::TestToggleLockAPI::test_toggle_lock_endpoint -v`
Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Add the endpoint**

In `blueprints/beach/routes/api/map_res_edit.py`, add the route inside `register_routes` function:

```python
    @bp.route('/map/reservations/<int:reservation_id>/toggle-lock', methods=['PATCH'])
    @login_required
    @permission_required('beach.reservations.edit')
    def toggle_reservation_lock(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Toggle the furniture lock status for a reservation.

        Request body:
            locked: bool - True to lock, False to unlock

        Returns:
            JSON with success status and new lock state
        """
        data = request.get_json()

        if data is None or 'locked' not in data:
            return jsonify({
                'success': False,
                'error': 'Campo "locked" requerido'
            }), 400

        locked = bool(data['locked'])

        from models.reservation_crud import toggle_furniture_lock
        result = toggle_furniture_lock(reservation_id, locked)

        if not result['success']:
            return jsonify(result), 404

        return jsonify(result)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_furniture_lock.py::TestToggleLockAPI -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add blueprints/beach/routes/api/map_res_edit.py tests/test_furniture_lock.py
git commit -m "feat(api): add toggle-lock endpoint for reservation furniture"
```

---

## Task 5: Backend API - Lock Check in Reassign Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_edit.py`
- Modify: `tests/test_furniture_lock.py`

**Step 1: Write the failing test**

Add to `tests/test_furniture_lock.py`:

```python
class TestReassignLockCheck:
    """Tests for lock checking in reassign furniture endpoint."""

    def test_reassign_blocked_when_locked(self, client, auth_headers):
        """Should block reassign when reservation is locked."""
        from database import get_db

        with get_db() as conn:
            cursor = conn.cursor()
            # Create locked reservation
            cursor.execute("""
                INSERT INTO beach_reservations
                (customer_id, state_id, start_date, end_date, num_people, is_furniture_locked)
                SELECT c.id, s.id, date('now'), date('now'), 2, 1
                FROM beach_customers c, beach_reservation_states s
                LIMIT 1
            """)
            reservation_id = cursor.lastrowid

            cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
            furniture = cursor.fetchone()
            furniture_id = furniture['id']

            today = cursor.execute("SELECT date('now') as d").fetchone()['d']
            conn.commit()

        # Try to reassign
        response = client.post(
            f'/beach/api/map/reservations/{reservation_id}/reassign-furniture',
            json={'furniture_ids': [furniture_id], 'date': today},
            headers=auth_headers
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data['success'] is False
        assert data.get('error') == 'locked'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_furniture_lock.py::TestReassignLockCheck::test_reassign_blocked_when_locked -v`
Expected: FAIL (returns 200 instead of 403)

**Step 3: Add lock check to reassign_furniture**

In `blueprints/beach/routes/api/map_res_edit.py`, modify `reassign_furniture` function. Add lock check after getting the reservation:

```python
        # Get existing reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        # Check if furniture is locked
        if reservation.get('is_furniture_locked'):
            return jsonify({
                'success': False,
                'error': 'locked',
                'message': 'El mobiliario de esta reserva esta bloqueado'
            }), 403
```

Also need to ensure `get_beach_reservation_by_id` returns `is_furniture_locked`. Check `models/reservation.py` and add the column to SELECT if needed.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_furniture_lock.py::TestReassignLockCheck -v`
Expected: 1 passed

**Step 5: Commit**

```bash
git add blueprints/beach/routes/api/map_res_edit.py
git commit -m "feat(api): block furniture reassignment when reservation is locked"
```

---

## Task 6: Backend - Include Lock Status in Reservation Details

**Files:**
- Modify: `models/reservation.py` (or `reservation_crud.py`)
- Modify: `blueprints/beach/routes/api/map_res_details.py`

**Step 1: Verify is_furniture_locked in get_beach_reservation_by_id**

Check `models/reservation.py` for `get_beach_reservation_by_id` function. Add `is_furniture_locked` to the SELECT statement if missing.

**Step 2: Verify is_furniture_locked in panel details endpoint**

In `blueprints/beach/routes/api/map_res_details.py`, ensure the `get_reservation_panel_details` endpoint returns `is_furniture_locked` in the reservation object.

**Step 3: Test manually or write integration test**

Run: `curl -s http://localhost:5000/beach/api/map/reservations/1/details | jq '.reservation.is_furniture_locked'`
Expected: `false` or `0`

**Step 4: Commit**

```bash
git add models/reservation.py blueprints/beach/routes/api/map_res_details.py
git commit -m "feat(api): include is_furniture_locked in reservation details response"
```

---

## Task 7: Frontend - CSS for Lock Button

**Files:**
- Modify: `static/css/reservation-panel.css`

**Step 1: Add CSS for lock toggle button**

Add to `static/css/reservation-panel.css`:

```css
/* =============================================================================
   FURNITURE LOCK TOGGLE
   ============================================================================= */

.furniture-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-2);
}

.btn-lock {
    background: transparent;
    border: none;
    padding: 4px 8px;
    border-radius: var(--border-radius-sm);
    color: var(--color-medium-gray);
    transition: all var(--transition-fast);
    cursor: pointer;
    font-size: 14px;
}

.btn-lock:hover {
    background: rgba(212, 175, 55, 0.1);
    color: var(--color-primary);
}

.btn-lock:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

.btn-lock.locked {
    color: var(--color-primary);
}

.btn-lock:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Disabled state for change furniture button when locked */
.furniture-change-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.furniture-change-btn:disabled:hover {
    background: var(--color-light-gray);
    transform: none;
}
```

**Step 2: Commit**

```bash
git add static/css/reservation-panel.css
git commit -m "feat(css): add styles for furniture lock toggle button"
```

---

## Task 8: Frontend - Lock Button in Panel Template

**Files:**
- Modify: `templates/beach/_reservation_panel.html`

**Step 1: Add lock button to furniture section**

In `templates/beach/_reservation_panel.html`, find the furniture section (around line 149-154) and wrap the title in a header div with the lock button:

```html
            <!-- Furniture Section -->
            <section class="panel-section furniture-section" id="furnitureSection">
                <div class="furniture-section-header">
                    <div class="panel-section-title">
                        <i class="fas fa-umbrella-beach"></i>
                        Mobiliario
                    </div>
                    <button type="button" class="btn-lock" id="toggleFurnitureLock"
                            aria-label="Bloquear mobiliario"
                            title="Bloquear mobiliario"
                            data-locked="false">
                        <i class="fas fa-lock-open"></i>
                    </button>
                </div>

                <!-- Normal View (hidden in reassignment mode) -->
                <div class="furniture-view-mode" id="furnitureViewMode">
```

**Step 2: Commit**

```bash
git add templates/beach/_reservation_panel.html
git commit -m "feat(template): add lock toggle button to furniture section"
```

---

## Task 9: Frontend - Lock Toggle JavaScript

**Files:**
- Modify: `static/js/map/reservation-panel-v2/furniture-mixin.js`

**Step 1: Add lock toggle handler**

In `static/js/map/reservation-panel-v2/furniture-mixin.js`, add these methods to the FurnitureMixin class:

```javascript
    // =========================================================================
    // FURNITURE LOCK
    // =========================================================================

    /**
     * Initialize furniture lock toggle
     */
    initFurnitureLock() {
        this.lockBtn = document.getElementById('toggleFurnitureLock');
        if (this.lockBtn) {
            this.lockBtn.addEventListener('click', () => this.toggleFurnitureLock());
        }
    }

    /**
     * Render the lock button state
     * @param {boolean} isLocked - Whether furniture is locked
     */
    renderLockState(isLocked) {
        if (!this.lockBtn) return;

        const icon = this.lockBtn.querySelector('i');
        if (isLocked) {
            this.lockBtn.classList.add('locked');
            this.lockBtn.dataset.locked = 'true';
            this.lockBtn.title = 'Desbloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Desbloquear mobiliario');
            icon.classList.remove('fa-lock-open');
            icon.classList.add('fa-lock');
        } else {
            this.lockBtn.classList.remove('locked');
            this.lockBtn.dataset.locked = 'false';
            this.lockBtn.title = 'Bloquear mobiliario';
            this.lockBtn.setAttribute('aria-label', 'Bloquear mobiliario');
            icon.classList.remove('fa-lock');
            icon.classList.add('fa-lock-open');
        }

        // Disable change furniture buttons when locked
        const changeFurnitureBtn = document.getElementById('panelChangeFurnitureBtn');
        const moveModeBtn = document.getElementById('panelMoveModeBtn');

        if (changeFurnitureBtn) {
            changeFurnitureBtn.disabled = isLocked;
            changeFurnitureBtn.title = isLocked ? 'Mobiliario bloqueado' : 'Cambiar mobiliario';
        }
        if (moveModeBtn) {
            moveModeBtn.disabled = isLocked;
            moveModeBtn.title = isLocked ? 'Mobiliario bloqueado' : 'Modo Mover';
        }
    }

    /**
     * Toggle furniture lock via API
     */
    async toggleFurnitureLock() {
        const reservation = this.state.data?.reservation;
        if (!reservation) return;

        const currentLocked = this.lockBtn.dataset.locked === 'true';
        const newLocked = !currentLocked;

        // Disable button during request
        this.lockBtn.disabled = true;

        try {
            const response = await fetch(
                `/beach/api/map/reservations/${reservation.id}/toggle-lock`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ locked: newLocked })
                }
            );

            const result = await response.json();

            if (result.success) {
                this.renderLockState(result.is_furniture_locked);
                // Update local state
                if (this.state.data.reservation) {
                    this.state.data.reservation.is_furniture_locked = result.is_furniture_locked;
                }
                showToast(
                    result.is_furniture_locked
                        ? 'Mobiliario bloqueado'
                        : 'Mobiliario desbloqueado',
                    'success'
                );
            } else {
                showToast(result.error || 'Error al cambiar bloqueo', 'error');
            }
        } catch (error) {
            console.error('Error toggling lock:', error);
            showToast('Error al cambiar bloqueo', 'error');
        } finally {
            this.lockBtn.disabled = false;
        }
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
```

**Step 2: Call initFurnitureLock in initialization**

Find the panel initialization and add `this.initFurnitureLock()`.

**Step 3: Call renderLockState when loading reservation**

In the method that renders reservation data (e.g., `renderReservation` or `loadReservation`), add:

```javascript
this.renderLockState(reservation.is_furniture_locked || false);
```

**Step 4: Commit**

```bash
git add static/js/map/reservation-panel-v2/furniture-mixin.js
git commit -m "feat(js): add furniture lock toggle functionality to reservation panel"
```

---

## Task 10: Frontend - Move Mode Lock Indicator CSS

**Files:**
- Modify: `static/css/move-mode.css`

**Step 1: Add lock indicator styles**

Add to `static/css/move-mode.css`:

```css
/* =============================================================================
   LOCKED FURNITURE INDICATOR (Move Mode)
   ============================================================================= */

/* Lock indicator hidden by default */
.furniture .lock-indicator {
    display: none;
    pointer-events: none;
}

/* Show lock indicator only in move mode for locked furniture */
.move-mode-active .furniture.locked .lock-indicator {
    display: block;
}

/* Shake animation for blocked action */
@keyframes shake-lock {
    0%, 100% { transform: translateX(0); }
    20%, 60% { transform: translateX(-3px); }
    40%, 80% { transform: translateX(3px); }
}

.furniture.shake {
    animation: shake-lock 0.4s ease;
}
```

**Step 2: Commit**

```bash
git add static/css/move-mode.css
git commit -m "feat(css): add lock indicator and shake animation for move mode"
```

---

## Task 11: Frontend - Move Mode Lock Check in MoveMode.js

**Files:**
- Modify: `static/js/map/MoveMode.js`

**Step 1: Modify unassignFurniture to check lock status**

In `static/js/map/MoveMode.js`, modify the `unassignFurniture` method to handle lock errors:

```javascript
    async unassignFurniture(reservationId, furnitureIds, isCtrlClick = false, initialFurnitureOverride = null) {
        if (!this.active) {
            return { success: false, error: 'Move mode not active' };
        }

        try {
            const result = await this._callApi('unassign', reservationId, furnitureIds);

            if (result.success && result.unassigned_count > 0) {
                this.pushUndo({
                    type: 'unassign',
                    reservation_id: reservationId,
                    furniture_ids: result.furniture_ids,
                    date: this.currentDate
                });

                await this.loadReservationToPool(reservationId, initialFurnitureOverride);
                showToast(`${result.unassigned_count} mobiliario liberado`, 'success');
            } else if (result.error === 'locked') {
                // Furniture is locked - trigger shake animation
                this.emit('onLockBlocked', {
                    reservationId,
                    furnitureIds
                });
                return result;
            }

            return result;
        } catch (error) {
            console.error('Error unassigning furniture:', error);
            this.emit('onError', { type: 'unassign', error });
            showToast('Error al liberar mobiliario', 'error');
            return { success: false, error: error.message };
        }
    }
```

**Step 2: Add onLockBlocked callback**

In the constructor, add the new callback:

```javascript
        this.callbacks = {
            onActivate: [],
            onDeactivate: [],
            onPoolUpdate: [],
            onSelectionChange: [],
            onFurnitureHighlight: [],
            onUndo: [],
            onError: [],
            onLockBlocked: []  // NEW
        };
```

**Step 3: Commit**

```bash
git add static/js/map/MoveMode.js
git commit -m "feat(js): handle locked furniture in move mode with event emission"
```

---

## Task 12: Frontend - Map Integration for Lock Indicator

**Files:**
- Modify: `static/js/map/BeachMap.js` (or equivalent map controller)

**Step 1: Add lock indicator to furniture rendering**

When rendering furniture on the map, check for locked status and add indicator. Also handle the `onLockBlocked` event to trigger shake animation.

```javascript
// In the furniture click handler or move mode integration:
moveMode.on('onLockBlocked', ({ reservationId, furnitureIds }) => {
    furnitureIds.forEach(fid => {
        const element = document.querySelector(`[data-furniture-id="${fid}"]`);
        if (element) {
            element.classList.add('shake');
            setTimeout(() => element.classList.remove('shake'), 400);
        }
    });
});
```

**Step 2: Mark locked furniture with CSS class**

When loading map data, add `locked` class to furniture elements that belong to locked reservations:

```javascript
// When rendering furniture:
if (furnitureData.is_locked) {
    furnitureElement.classList.add('locked');
}
```

**Step 3: Add lock indicator SVG element**

For SVG-based furniture, add the lock indicator group:

```javascript
// When creating furniture SVG elements:
const lockIndicator = document.createElementNS('http://www.w3.org/2000/svg', 'g');
lockIndicator.classList.add('lock-indicator');
lockIndicator.innerHTML = `
    <circle r="10" fill="#1A3A5C" opacity="0.9"/>
    <text fill="#D4AF37" font-size="10" text-anchor="middle" dominant-baseline="central">&#xf023;</text>
`;
// Position at top-right of furniture
furnitureGroup.appendChild(lockIndicator);
```

**Step 4: Commit**

```bash
git add static/js/map/BeachMap.js
git commit -m "feat(js): add lock indicator and shake animation to map furniture"
```

---

## Task 13: Integration Testing

**Files:**
- Modify: `tests/test_furniture_lock.py`

**Step 1: Add integration test for full flow**

```python
class TestFurnitureLockIntegration:
    """Integration tests for the complete lock flow."""

    def test_lock_prevents_move_mode_unassign(self, client, auth_headers):
        """Full flow: lock reservation, attempt unassign via move mode API."""
        from database import get_db

        with get_db() as conn:
            cursor = conn.cursor()
            # Create reservation with furniture
            cursor.execute("""
                INSERT INTO beach_reservations
                (customer_id, state_id, start_date, end_date, num_people)
                SELECT c.id, s.id, date('now'), date('now'), 2
                FROM beach_customers c, beach_reservation_states s
                LIMIT 1
            """)
            reservation_id = cursor.lastrowid

            cursor.execute("SELECT id FROM beach_furniture WHERE active = 1 LIMIT 1")
            furniture = cursor.fetchone()
            furniture_id = furniture['id']

            cursor.execute("""
                INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, date('now'))
            """, (reservation_id, furniture_id))

            today = cursor.execute("SELECT date('now') as d").fetchone()['d']
            conn.commit()

        # Step 1: Lock the reservation
        response = client.patch(
            f'/beach/api/map/reservations/{reservation_id}/toggle-lock',
            json={'locked': True},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.get_json()['is_furniture_locked'] is True

        # Step 2: Try to unassign via move mode - should fail
        response = client.post(
            '/beach/api/move-mode/unassign',
            json={
                'reservation_id': reservation_id,
                'furniture_ids': [furniture_id],
                'date': today
            },
            headers=auth_headers
        )
        assert response.status_code == 200  # API returns 200 with error
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'locked'

        # Step 3: Unlock the reservation
        response = client.patch(
            f'/beach/api/map/reservations/{reservation_id}/toggle-lock',
            json={'locked': False},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Step 4: Now unassign should work
        response = client.post(
            '/beach/api/move-mode/unassign',
            json={
                'reservation_id': reservation_id,
                'furniture_ids': [furniture_id],
                'date': today
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
```

**Step 2: Run all tests**

Run: `pytest tests/test_furniture_lock.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/test_furniture_lock.py
git commit -m "test: add integration tests for furniture lock feature"
```

---

## Task 14: Final Verification & Cleanup

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All 191+ tests pass

**Step 2: Manual testing checklist**

- [ ] Create reservation, toggle lock on/off via panel
- [ ] Locked reservation shows gold lock icon
- [ ] Unlocked reservation shows gray open lock icon
- [ ] Change furniture button disabled when locked
- [ ] Move mode button disabled when locked
- [ ] In move mode, locked furniture shows lock indicator
- [ ] Clicking locked furniture in move mode triggers shake
- [ ] Unlocking allows normal reassignment

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete furniture lock feature implementation

- Add is_furniture_locked column to beach_reservations
- Add toggle_furniture_lock and is_furniture_locked model functions
- Block unassign/reassign when furniture is locked
- Add lock toggle button to reservation panel
- Show lock indicator on furniture in move mode
- Add shake animation when attempting to move locked furniture
- Include comprehensive tests

Closes #XXX"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Database migration | `migrations/`, `database/schema.py` |
| 2 | Lock toggle model | `models/reservation_crud.py`, tests |
| 3 | Lock check in move mode | `models/move_mode.py`, tests |
| 4 | Toggle lock API endpoint | `blueprints/.../map_res_edit.py`, tests |
| 5 | Lock check in reassign | `blueprints/.../map_res_edit.py`, tests |
| 6 | Include lock in details | `models/reservation.py`, API |
| 7 | Lock button CSS | `static/css/reservation-panel.css` |
| 8 | Lock button template | `templates/beach/_reservation_panel.html` |
| 9 | Lock toggle JavaScript | `static/js/.../furniture-mixin.js` |
| 10 | Move mode lock CSS | `static/css/move-mode.css` |
| 11 | Move mode lock JS | `static/js/map/MoveMode.js` |
| 12 | Map lock indicator | `static/js/map/BeachMap.js` |
| 13 | Integration tests | `tests/test_furniture_lock.py` |
| 14 | Final verification | All files |
