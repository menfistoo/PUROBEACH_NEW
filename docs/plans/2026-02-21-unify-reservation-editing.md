# Unify Reservation Editing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate duplicated reservation editing code by making both views (list + map) use a single API endpoint and share JS logic.

**Architecture:** The map endpoint (`PATCH /beach/api/map/reservations/<id>/update`) is the more complete and validated one — it handles more fields, has proper validation, and syncs tags to customers. We'll make the quick-edit modal call this same endpoint, then retire the old quick-edit endpoint. The shared backend stays as-is; only the JS caller and the old route change.

**Tech Stack:** Flask (Python), JavaScript ES6+, Bootstrap 5

---

## Current Problem

Two separate API endpoints handle reservation updates:

| View | Endpoint | Handler File |
|------|----------|-------------|
| List (`/beach/reservations`) | `PATCH /beach/api/reservations/<id>` | `api/reservations.py:72-174` |
| Map (`/beach/map`) | `PATCH /beach/api/map/reservations/<id>/update` | `api/map_res_edit_fields.py:22-193` |

**Issues:**
1. Different validation logic (map has more, list has less)
2. List endpoint doesn't sync tags to customer (`sync_reservation_tags_to_customer`)
3. List endpoint handles state changes inline; map uses separate toggle endpoint
4. Different allowed fields (map supports pricing fields, list doesn't)
5. List does `location.reload()` after save; map does toast — neither notifies the other view

## Solution

1. **Quick-edit JS → call the map endpoint** (already more complete)
2. **Add state_id handling to the map endpoint** (so list modal's state chip works)
3. **Deprecate the old quick-edit endpoint** (redirect → new endpoint)
4. **Add audit logging to the map endpoint** (currently missing)

---

### Task 1: Add state_id Support to Map Update Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_edit_fields.py:22-193`

**Step 1: Read current code and understand the gap**

The map endpoint doesn't handle `state_id`. The list endpoint does (lines 111-133 of `api/reservations.py`). We need to port that logic.

**Step 2: Add state_id handling to `update_reservation_partial()`**

After the tag handling block (~line 161), add state handling. Insert before the `try: with get_db()` block:

```python
# Handle state change (state_id = ID of the new state)
if 'state_id' in data:
    from flask_login import current_user
    from models.reservation import get_reservation_with_details
    from models.reservation_state import add_reservation_state, remove_reservation_state

    state_id = data['state_id']
    try:
        state_id = int(state_id)
    except (ValueError, TypeError):
        return api_error('ID de estado no válido')

    with get_db() as conn:
        state = conn.execute(
            'SELECT name FROM beach_reservation_states WHERE id = ?',
            (state_id,)
        ).fetchone()
        if state:
            full_res = get_reservation_with_details(reservation_id)
            current_states = full_res.get('current_states', '') if full_res else ''
            current_state_list = [s.strip() for s in current_states.split(',') if s.strip()]
            changed_by = current_user.username if current_user else 'system'
            for existing_state in current_state_list:
                remove_reservation_state(reservation_id, existing_state, changed_by=changed_by)
            add_reservation_state(reservation_id, state['name'], changed_by=changed_by)
```

**Step 3: Run tests to verify nothing breaks**

Run: `python -m pytest tests/test_reservation.py -v`
Expected: All existing tests PASS (no test covers this endpoint yet)

**Step 4: Commit**

```bash
git add blueprints/beach/routes/api/map_res_edit_fields.py
git commit -m "feat: add state_id support to map reservation update endpoint"
```

---

### Task 2: Add Audit Logging to Map Update Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_edit_fields.py:22-193`

The map endpoint currently has NO audit logging. The list endpoint does (`log_update`). Add it.

**Step 1: Import audit function**

At top of file, add:
```python
from utils.audit import log_update
```

**Step 2: Capture before-state at the start of the handler**

After `reservation = get_beach_reservation_by_id(reservation_id)` (line 46), add:
```python
before_state = dict(reservation) if reservation else {}
```

**Step 3: Log after successful update**

After `conn.commit()` (line 183), add:
```python
# Audit log
after_reservation = get_beach_reservation_by_id(reservation_id)
after_state = dict(after_reservation) if after_reservation else {}
log_update('reservation', reservation_id, before=before_state, after=after_state)
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_reservation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add blueprints/beach/routes/api/map_res_edit_fields.py
git commit -m "feat: add audit logging to map reservation update endpoint"
```

---

### Task 3: Switch Quick-Edit JS to Use Map Endpoint

**Files:**
- Modify: `static/js/reservation-quick-edit.js` (line 292)

This is the key change. The quick-edit modal currently calls:
```
PATCH /beach/api/reservations/{id}
```

Change it to call:
```
PATCH /beach/api/map/reservations/{id}/update
```

**Step 1: Update the fetch URL in `saveQuickEdit()`**

In `static/js/reservation-quick-edit.js`, line 292, change:
```javascript
// OLD:
const response = await fetch(`/beach/api/reservations/${reservationId}`, {
// NEW:
const response = await fetch(`/beach/api/map/reservations/${reservationId}/update`, {
```

**Step 2: Verify the payload shape is compatible**

The map endpoint already handles all fields the quick-edit sends:
- `num_people` ✓ (validated 1-50)
- `paid` ✓ (coerced to 0/1)
- `observations` ✓ (mapped to `notes`)
- `payment_ticket_number` ✓ (empty → null)
- `payment_method` ✓ (validated enum)
- `preferences` ✓ (CSV → junction table)
- `tag_ids` ✓ (syncs to customer too — bonus!)
- `state_id` ✓ (added in Task 1)

No payload changes needed.

**Step 3: Manual test**

1. Open `/beach/reservations`
2. Click edit on any reservation
3. Change num_people, toggle paid, change state, add/remove tags
4. Save → verify changes persist
5. Open `/beach/map` → verify same reservation shows updated data

**Step 4: Commit**

```bash
git add static/js/reservation-quick-edit.js
git commit -m "refactor: quick-edit modal now uses unified map update endpoint"
```

---

### Task 4: Deprecate Old Quick-Edit PATCH Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/reservations.py` (lines 72-174)

Don't delete yet — redirect to maintain any other callers.

**Step 1: Replace the handler body with a proxy to the new endpoint**

Replace the entire `reservation_update()` function body (lines 75-174) with a redirect/proxy:

```python
@bp.route('/reservations/<int:reservation_id>', methods=['PATCH'])
@login_required
@permission_required('beach.reservations.edit')
def reservation_update(reservation_id):
    """Quick update reservation fields.

    DEPRECATED: This endpoint proxies to /map/reservations/<id>/update.
    All clients should migrate to the unified endpoint directly.
    """
    from flask import url_for
    import requests as _  # not needed, we just forward internally

    # Forward to the unified endpoint handler
    from blueprints.beach.routes.api.map_res_edit_fields import _update_reservation_partial_impl
    return _update_reservation_partial_impl(reservation_id)
```

**Alternative (simpler):** Since both handlers are in the same Flask app, just make the old route call the new handler's logic directly. But the cleanest approach is to simply **gut the old handler and have it call the map endpoint's function**.

Actually, the simplest approach: extract the map endpoint's core logic into a shared function, then both routes call it. But that's over-engineering for a deprecation.

**Recommended approach:** Just leave a comment marking it deprecated and log a warning. Since Task 3 already switched the JS, no client calls this anymore. We can remove it in a future cleanup.

```python
@bp.route('/reservations/<int:reservation_id>', methods=['PATCH'])
@login_required
@permission_required('beach.reservations.edit')
def reservation_update(reservation_id):
    """DEPRECATED: Use PATCH /map/reservations/<id>/update instead."""
    current_app.logger.warning(
        f'Deprecated endpoint called: PATCH /reservations/{reservation_id}. '
        'Migrate to /map/reservations/<id>/update'
    )
    # Keep working for backward compatibility but log warning
    # ... (keep existing code unchanged for safety)
```

**Step 2: Add deprecation warning log at the top of the handler**

Just add after line 76:
```python
current_app.logger.warning(
    f'DEPRECATED endpoint: PATCH /api/reservations/{reservation_id} — '
    'use PATCH /api/map/reservations/<id>/update instead'
)
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_reservation.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add blueprints/beach/routes/api/reservations.py
git commit -m "refactor: mark old quick-edit PATCH endpoint as deprecated"
```

---

### Task 5: Write Tests for the Unified Update Endpoint

**Files:**
- Modify: `tests/test_reservation.py`

**Step 1: Add test for PATCH update via unified endpoint**

```python
class TestReservationUnifiedUpdate:
    """Tests for the unified reservation update endpoint."""

    def test_update_num_people(self, auth_client, sample_reservation):
        """Update num_people via unified endpoint."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={'num_people': 3},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'num_people' in data.get('updated_fields', [])

    def test_update_validates_num_people_range(self, auth_client, sample_reservation):
        """Reject num_people outside 1-50."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={'num_people': 0},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_update_paid_and_payment(self, auth_client, sample_reservation):
        """Update payment fields together."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={
                'paid': 1,
                'payment_method': 'tarjeta',
                'payment_ticket_number': 'TKT-001'
            },
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_update_observations_maps_to_notes(self, auth_client, sample_reservation):
        """Frontend 'observations' field maps to DB 'notes'."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={'observations': 'Test notes'},
            content_type='application/json'
        )
        assert response.status_code == 200
        assert 'notes' in response.get_json().get('updated_fields', [])

    def test_update_state_id(self, auth_client, sample_reservation):
        """State change via state_id (from quick-edit modal)."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={'state_id': 2},  # Assuming state ID 2 exists
            content_type='application/json'
        )
        assert response.status_code == 200

    def test_update_rejects_invalid_payment_method(self, auth_client, sample_reservation):
        """Invalid payment method rejected."""
        response = auth_client.patch(
            f'/beach/api/map/reservations/{sample_reservation}/update',
            json={'payment_method': 'bitcoin'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_update_nonexistent_reservation(self, auth_client):
        """404 for nonexistent reservation."""
        response = auth_client.patch(
            '/beach/api/map/reservations/99999/update',
            json={'num_people': 2},
            content_type='application/json'
        )
        assert response.status_code == 404
```

**Step 2: Run tests**

Run: `python -m pytest tests/test_reservation.py::TestReservationUnifiedUpdate -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_reservation.py
git commit -m "test: add tests for unified reservation update endpoint"
```

---

### Task 6: Final Verification

**Step 1: Run full test suite**

Run: `python -m pytest -v`
Expected: All PASS

**Step 2: Manual integration test**

1. Start dev server: `python app.py`
2. Open `/beach/reservations` → edit reservation → save → verify data saved
3. Open `/beach/map` → check same reservation → data matches
4. Edit from map panel → save → go back to list → data matches
5. Check browser console for any JS errors
6. Check Flask logs for any deprecation warnings (should NOT appear since JS was updated)

**Step 3: Commit final state**

```bash
git add -A
git commit -m "feat: unified reservation editing - single endpoint for list and map views"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `blueprints/beach/routes/api/map_res_edit_fields.py` | Add `state_id` handling + audit logging |
| `static/js/reservation-quick-edit.js` | Change fetch URL (1 line) |
| `blueprints/beach/routes/api/reservations.py` | Add deprecation warning |
| `tests/test_reservation.py` | Add unified endpoint tests |

**Total LOC changed:** ~60 lines added, 1 line modified, 0 deleted.

**Risk:** Low. The map endpoint is already production-tested. We're routing more traffic to it and adding features it was missing (state_id, audit log).

## Future Cleanup (Not in This Plan)

- Remove deprecated `reservation_update()` endpoint entirely after confirming no other callers
- Consider extracting shared validation logic into `services/reservation_service.py`
- Add WebSocket or SSE for real-time cross-tab sync (overkill for now)
