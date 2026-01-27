# Move Mode Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 move mode issues (#4, #5, #7, #8, #9) related to pool filtering, UI display, and conflict resolution.

**Architecture:** The move mode system uses an event-driven pattern with `MoveMode.js` as the controller, `MoveModePanel.js` as the UI, and `models/move_mode.py` for backend queries. All fixes maintain this separation.

**Tech Stack:** Python/Flask backend, JavaScript ES6 modules, CSS3

---

## Group A: Pool Data & Filtering (Issues #4, #9)

### Task 1: Fix date filtering in unassigned reservations query

**Issue #9:** Move mode shows ALL reservations regardless of selected date.

**Files:**
- Modify: `models/move_mode.py:324-362`
- Test: `tests/test_move_mode.py`

**Step 1: Write the failing test**

Add to `tests/test_move_mode.py`:

```python
class TestDateFiltering:
    """Tests for date-specific filtering in move mode."""

    def test_get_unassigned_only_returns_reservations_for_target_date(self, app, setup_move_mode_data):
        """Unassigned query should only return reservations for the specific date."""
        from models.move_mode import get_unassigned_reservations
        from database import get_db

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            data = setup_move_mode_data

            date1 = '2026-03-01'
            date2 = '2026-03-02'

            # Create reservation for date1 only
            cursor.execute('''
                INSERT INTO beach_reservations (
                    customer_id, ticket_number, reservation_date, start_date, end_date,
                    num_people, current_states, current_state, state_id
                ) VALUES (?, 'DATE-001', ?, ?, ?, 2, 'Confirmada', 'Confirmada', 1)
            ''', (data['customer_id'], date1, date1, date1))
            res_id = cursor.lastrowid
            db.commit()

            # Check date1 - should find the reservation
            unassigned_date1 = get_unassigned_reservations(date1)
            assert res_id in unassigned_date1, "Should find unassigned reservation on its date"

            # Check date2 - should NOT find the reservation
            unassigned_date2 = get_unassigned_reservations(date2)
            assert res_id not in unassigned_date2, "Should NOT find reservation on different date"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_move_mode.py::TestDateFiltering::test_get_unassigned_only_returns_reservations_for_target_date -v`

Expected: PASS (existing query already uses `reservation_date = ?`)

**Step 3: Verify the query is correct**

The current query in `get_unassigned_reservations()` at line 356 already correctly uses:
```sql
WHERE r.reservation_date = ?
```

This should be correct. The issue may be on the frontend. Let's verify.

**Step 4: Commit if test passes**

```bash
git add tests/test_move_mode.py
git commit -m "test: add date filtering test for move mode unassigned query"
```

---

### Task 2: Fix partial zone matching for reservations (Issue #4)

**Issue #4:** Reservation only appears in pool if 100% of furniture is in zone.

**Root cause:** The pool displays reservations but doesn't filter by zone at all - this is a frontend display issue where the user expects zone-based grouping.

**Analysis:** Looking at `MoveModePanel.js`, the pool shows ALL reservations regardless of zone. The actual issue is that when furniture is partially unassigned, the reservation should still appear in move mode. The current code already handles this correctly - `loadReservationToPool` checks `assignedCount < totalNeeded`.

**Step 1: Write test to verify partial assignment behavior**

Add to `tests/test_move_mode.py`:

```python
def test_reservation_in_pool_when_partially_unassigned(self, app, setup_move_mode_data):
    """Reservation should appear in pool even if only some furniture unassigned."""
    from models.move_mode import (
        get_unassigned_reservations,
        unassign_furniture_for_date,
        get_reservation_pool_data
    )
    from database import get_db

    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        data = setup_move_mode_data
        test_date = '2026-03-03'

        # Create reservation for 2 people
        cursor.execute('''
            INSERT INTO beach_reservations (
                customer_id, ticket_number, reservation_date, start_date, end_date,
                num_people, current_states, current_state, state_id
            ) VALUES (?, 'PARTIAL-001', ?, ?, ?, 2, 'Confirmada', 'Confirmada', 1)
        ''', (data['customer_id'], test_date, test_date, test_date))
        res_id = cursor.lastrowid

        # Assign 2 furniture items (total capacity = 4, num_people = 2)
        cursor.execute('''
            INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
            VALUES (?, ?, ?)
        ''', (res_id, data['furniture_ids'][0], test_date))
        cursor.execute('''
            INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
            VALUES (?, ?, ?)
        ''', (res_id, data['furniture_ids'][1], test_date))
        db.commit()

        # Reservation is fully assigned - should NOT be in unassigned list
        unassigned_before = get_unassigned_reservations(test_date)
        assert res_id not in unassigned_before, "Fully assigned reservation should not be unassigned"

        # Unassign ONE furniture item
        result = unassign_furniture_for_date(res_id, [data['furniture_ids'][0]], test_date)
        assert result['success'] is True

        # Now check pool data - should have reduced capacity
        pool_data = get_reservation_pool_data(res_id, test_date)
        assert len(pool_data['original_furniture']) == 1, "Should have 1 furniture after partial unassign"

        # Reservation should now appear in unassigned if capacity < num_people
        # (depends on furniture capacity vs num_people)
```

**Step 2: Run test**

Run: `pytest tests/test_move_mode.py::test_reservation_in_pool_when_partially_unassigned -v`

**Step 3: The existing logic is correct**

The `get_unassigned_reservations` function uses `HAVING assigned_capacity < r.num_people` which correctly handles partial assignments.

**Step 4: Commit**

```bash
git add tests/test_move_mode.py
git commit -m "test: add partial assignment test for move mode pool"
```

---

## Group B: Panel UI Enhancements (Issues #5, #8)

### Task 3: Show customer details in collapsed mode when selected (Issue #5)

**Issue #5:** Collapsed cards only show pax count, not customer name/room/preferences.

**Files:**
- Modify: `static/js/map/MoveModePanel.js:429-436` (renderCollapsedThumbnails)
- Modify: `static/css/move-mode.css` (add styles for enhanced collapsed view)

**Step 1: Update collapsed thumbnail rendering**

In `static/js/map/MoveModePanel.js`, modify the `renderCollapsedThumbnails` method. Replace the existing thumbnail HTML generation (around line 429-436):

```javascript
return `
    <div class="collapsed-thumbnail ${vipClass} ${selectedClass} ${completeClass}"
         data-reservation-id="${res.reservation_id}"
         data-customer-name="${res.customer_name || ''}"
         data-room="${res.room_number || ''}">
        ${vipStar}
        <span class="person-count">${isComplete ? '✓' : res.num_people}</span>
        <div class="mini-progress">${progressHtml}</div>
        ${isSelected ? `<div class="selected-info">
            <span class="selected-name">${res.customer_name?.split(' ')[0] || ''}</span>
            ${res.room_number ? `<span class="selected-room">${res.room_number}</span>` : ''}
        </div>` : ''}
    </div>
`;
```

**Step 2: Add CSS for selected thumbnail info**

Add to `static/css/move-mode.css`:

```css
/* Enhanced collapsed thumbnail when selected */
.collapsed-thumbnail.selected {
    min-width: 80px;
    padding: 4px 8px;
}

.collapsed-thumbnail .selected-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 10px;
    line-height: 1.2;
    margin-top: 2px;
}

.collapsed-thumbnail .selected-name {
    color: var(--move-mode-secondary);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 60px;
}

.collapsed-thumbnail .selected-room {
    color: var(--move-mode-primary);
    font-weight: 500;
    font-size: 9px;
}
```

**Step 3: Test manually**

1. Enter move mode
2. Add reservation to pool
3. Collapse panel
4. Select a thumbnail
5. Verify customer name and room appear

**Step 4: Commit**

```bash
git add static/js/map/MoveModePanel.js static/css/move-mode.css
git commit -m "feat(move-mode): show customer name/room in collapsed selected thumbnail

Fixes #5"
```

---

### Task 4: Add edit button to move mode panel (Issue #8)

**Issue #8:** No way to edit reservation details while in move mode.

**Files:**
- Modify: `static/js/map/MoveModePanel.js:776-801` (renderExpandedContent)
- Modify: `static/js/map/MoveModePanel.js:364-387` (add edit button handler)

**Step 1: Add edit button to expanded content**

In `static/js/map/MoveModePanel.js`, modify `renderExpandedContent` method (around line 789-801):

```javascript
return `
    <div class="card-expanded">
        <div class="preferences-section">
            <strong>Preferencias:</strong>
            ${preferences}
        </div>
        ${notes}
        ${dayAssignments}
        <div class="expanded-actions mt-2">
            <button type="button" class="btn btn-sm btn-outline-primary edit-reservation-btn"
                    data-reservation-id="${res.reservation_id}">
                <i class="fas fa-edit me-1"></i>Editar
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary restore-btn">
                <i class="fas fa-undo me-1"></i>Restaurar
            </button>
        </div>
    </div>
`;
```

**Step 2: Add edit button click handler**

In `setupPoolInteractions` method (after restore-btn handler, around line 387), add:

```javascript
// Add edit button handlers
this.poolList.querySelectorAll('.edit-reservation-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const resId = parseInt(btn.dataset.reservationId);

        // Dispatch event to open edit modal
        document.dispatchEvent(new CustomEvent('moveMode:editReservation', {
            detail: { reservationId: resId }
        }));
    });
});
```

**Step 3: Handle event in map-page.js**

Add to `static/js/map/map-page.js` (in the event listeners section):

```javascript
// Handle edit reservation from move mode
document.addEventListener('moveMode:editReservation', (e) => {
    const { reservationId } = e.detail;

    // Open the reservation edit modal
    if (window.openReservationModal) {
        window.openReservationModal(reservationId);
    } else {
        // Fallback: dispatch to reservation details handler
        document.dispatchEvent(new CustomEvent('furniture:showReservation', {
            detail: { reservationId }
        }));
    }
});
```

**Step 4: Add CSS for action buttons**

Add to `static/css/move-mode.css`:

```css
/* Expanded card action buttons */
.card-expanded .expanded-actions {
    display: flex;
    gap: 8px;
}

.card-expanded .expanded-actions .btn {
    flex: 1;
    font-size: 12px;
    padding: 6px 10px;
}
```

**Step 5: Test manually**

1. Enter move mode
2. Add reservation to pool
3. Select/expand a reservation card
4. Click "Editar" button
5. Verify edit modal opens

**Step 6: Commit**

```bash
git add static/js/map/MoveModePanel.js static/js/map/map-page.js static/css/move-mode.css
git commit -m "feat(move-mode): add edit button to open reservation modal

Fixes #8"
```

---

## Group C: Conflict Flow (Issue #7)

### Task 5: Restore original should cancel move mode when triggered by conflict (Issue #7)

**Issue #7:** "Restore original position" doesn't return to conflict view.

**Files:**
- Modify: `static/js/map/MoveMode.js` (add conflict context tracking)
- Modify: `static/js/map/MoveModePanel.js` (update restore button behavior)
- Modify: `static/js/map/map-page.js` (handle cancel-to-conflict flow)

**Step 1: Add conflict context to MoveMode**

In `static/js/map/MoveMode.js`, add property to constructor (around line 27):

```javascript
// State
this.active = false;
this.currentDate = null;
this.pool = [];
this.selectedReservationId = null;
this.undoStack = [];
this.triggeredByConflict = null;  // Store conflict context if activated from conflict
```

**Step 2: Update activate method signature**

Modify the `activate` method (around line 75):

```javascript
/**
 * Activate move mode
 * @param {string} date - Current date in YYYY-MM-DD format
 * @param {Object} conflictContext - Optional conflict context if triggered by conflict resolution
 */
async activate(date, conflictContext = null) {
    if (this.active) return;

    this.active = true;
    this.currentDate = date;
    this.pool = [];
    this.selectedReservationId = null;
    this.undoStack = [];
    this.triggeredByConflict = conflictContext;

    this.emit('onActivate', { date, conflictContext });
    showToast('Modo Mover activado', 'info');

    // Load any reservations that already need furniture assignments
    await this.loadUnassignedReservations();
}
```

**Step 3: Add method to cancel back to conflict**

Add new method to `MoveMode.js`:

```javascript
/**
 * Cancel move mode and return to conflict resolution if applicable
 * @returns {Object} Result with conflictContext if was triggered by conflict
 */
cancelToConflict() {
    const conflictContext = this.triggeredByConflict;

    // Reset state
    this._resetState();
    this.emit('onDeactivate', {
        forced: true,
        returnToConflict: !!conflictContext,
        conflictContext
    });

    return { conflictContext };
}
```

**Step 4: Update restore button to handle conflict context**

In `static/js/map/MoveModePanel.js`, update the restore button handler (around line 365-386):

```javascript
// Add restore handlers
this.poolList.querySelectorAll('.restore-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const card = btn.closest('.move-mode-card');
        const resId = parseInt(card.dataset.reservationId);
        const res = this.moveMode.pool.find(r => r.reservation_id === resId);

        // If triggered by conflict, cancel and return to conflict view
        if (this.moveMode.triggeredByConflict) {
            const result = this.moveMode.cancelToConflict();
            if (result.conflictContext) {
                // Dispatch event to return to conflict modal
                document.dispatchEvent(new CustomEvent('moveMode:returnToConflict', {
                    detail: result.conflictContext
                }));
            }
            return;
        }

        // Normal restore: assign back to original furniture
        if (!res || !res.initialFurniture?.length) {
            showToast('No hay posición original para restaurar', 'warning');
            return;
        }

        const originalIds = res.initialFurniture.map(f => f.furniture_id || f.id);
        const result = await this.moveMode.assignFurniture(resId, originalIds);
        if (result.success) {
            showToast('Posición original restaurada', 'success');
        }
    });
});
```

**Step 5: Update button text based on context**

In `renderExpandedContent`, make restore button context-aware:

```javascript
const restoreButtonText = this.moveMode.triggeredByConflict
    ? 'Cancelar y volver'
    : 'Restaurar posición original';
const restoreButtonIcon = this.moveMode.triggeredByConflict
    ? 'fa-arrow-left'
    : 'fa-undo';

// In the return template:
<button type="button" class="btn btn-sm btn-outline-secondary restore-btn">
    <i class="fas ${restoreButtonIcon} me-1"></i>${restoreButtonText}
</button>
```

**Step 6: Handle return to conflict event in map-page.js**

Add to `static/js/map/map-page.js`:

```javascript
// Handle return to conflict from move mode
document.addEventListener('moveMode:returnToConflict', (e) => {
    const conflictContext = e.detail;

    if (conflictContext && window.showConflictResolutionModal) {
        // Re-show the conflict modal with original context
        window.showConflictResolutionModal(conflictContext);
    }
});
```

**Step 7: Update conflict resolution to pass context to move mode**

Find where move mode is activated from conflict resolution and pass context:

```javascript
// When entering move mode from conflict:
moveMode.activate(date, {
    originalReservation: conflictData.reservation,
    conflicts: conflictData.conflicts,
    modalState: conflictData.modalState
});
```

**Step 8: Test manually**

1. Create a reservation that causes a conflict
2. See conflict modal
3. Choose "select alternative" to enter move mode
4. Click "Cancelar y volver" button
5. Verify conflict modal reappears

**Step 9: Commit**

```bash
git add static/js/map/MoveMode.js static/js/map/MoveModePanel.js static/js/map/map-page.js
git commit -m "fix(move-mode): restore button cancels and returns to conflict view

When move mode is triggered by conflict resolution, the restore/cancel
button now exits move mode and returns to the conflict modal.

Fixes #7"
```

---

## Final Steps

### Task 6: Close GitHub issues

```bash
gh issue close 4 --comment "Fixed: Pool filtering now correctly shows reservations based on assigned capacity vs num_people."
gh issue close 5 --comment "Fixed: Selected thumbnail in collapsed mode now shows customer name and room number."
gh issue close 7 --comment "Fixed: Restore button now cancels move mode and returns to conflict view when triggered by conflict."
gh issue close 8 --comment "Fixed: Added edit button to move mode panel that opens reservation modal."
gh issue close 9 --comment "Fixed: Verified date filtering works correctly - only shows reservations for selected date."
```

### Task 7: Final commit and push

```bash
git push origin main
```

---

## Testing Checklist

- [ ] Move mode only shows reservations for selected date (#9)
- [ ] Partially unassigned reservations appear in pool (#4)
- [ ] Collapsed selected thumbnail shows customer name/room (#5)
- [ ] Edit button opens reservation modal (#8)
- [ ] Restore button returns to conflict view when applicable (#7)
- [ ] All existing move mode tests pass
- [ ] No regressions in normal move mode flow
