# Reservation Characteristics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire characteristics to reservations so they save to the junction table, and show them in both the map panel and reservation edit page.

**Architecture:** The infrastructure already exists (models, junction table, admin config). We need to: (1) add `set_reservation_characteristics_by_codes()` calls in create/edit flows, (2) include reservation characteristics in the API response so the panel displays them, (3) update the save flow to write to the reservation junction table alongside the customer one.

**Tech Stack:** Flask/Python backend, vanilla JS panel (ES6 modules with mixin pattern)

---

### Task 1: Backend - Wire reservation characteristics into creation flow

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_create.py:269-326`

**Step 1: Add import**

At line 23, after the existing import of `set_customer_characteristics_by_codes`, add:

```python
from models.characteristic_assignments import set_customer_characteristics_by_codes, set_reservation_characteristics_by_codes
```

(Replace the existing single import with this combined one.)

**Step 2: Add junction table write after multi-day creation (line ~272)**

After `set_customer_characteristics_by_codes(customer_id, preferences)` on line 272, add:

```python
                        # Also save characteristics to each reservation
                        for res_id in result.get('reservation_ids', []):
                            set_reservation_characteristics_by_codes(res_id, preferences)
```

**Step 3: Add junction table write after single-day creation (line ~326)**

After `set_customer_characteristics_by_codes(customer_id, preferences)` on line 326, add:

```python
                    # Also save characteristics to the reservation
                    set_reservation_characteristics_by_codes(reservation_id, preferences)
```

**Step 4: Run tests**

Run: `python -m pytest tests/ -x -q`
Expected: All 300 tests pass (no test touches this code path with characteristics)

**Step 5: Commit**

```bash
git add blueprints/beach/routes/api/map_res_create.py
git commit -m "fix: save characteristics to reservation junction table on creation

Fixes #21"
```

---

### Task 2: Backend - Wire reservation characteristics into edit/save flow

**Files:**
- Modify: `blueprints/beach/routes/api/map_res_edit_fields.py:103-107`

**Step 1: Add import at top of file (after line 14)**

```python
from models.characteristic_assignments import set_reservation_characteristics_by_codes
```

**Step 2: Replace CSV-only handling with junction table write**

Replace lines 103-106:

```python
        # preferences should be comma-separated string or empty
        if 'preferences' in updates:
            if updates['preferences'] is None:
                updates['preferences'] = ''
```

With:

```python
        # preferences - sync to junction table
        if 'preferences' in updates:
            pref_value = updates['preferences']
            if pref_value is None:
                pref_value = ''
            updates['preferences'] = pref_value

            # Also update junction table
            pref_codes = [c.strip() for c in pref_value.split(',') if c.strip()] if pref_value else []
            set_reservation_characteristics_by_codes(reservation_id, pref_codes)
```

**Step 3: Run tests**

Run: `python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add blueprints/beach/routes/api/map_res_edit_fields.py
git commit -m "fix: sync characteristics to junction table on reservation edit

Fixes #21"
```

---

### Task 3: Backend - Include reservation characteristics in API response

**Files:**
- Find and modify: the API endpoint that returns reservation data for the panel (the one that `panel.open(reservationId)` calls)

**Step 1: Find the API endpoint**

Search for the route that returns reservation detail data for the panel. It will be something like `/map/reservations/<id>` GET. Check:
- `blueprints/beach/routes/api/map_reservations.py` or similar
- Look for the route that returns `reservation`, `customer`, `furniture` data as JSON

**Step 2: Add reservation characteristics to the response**

Import `get_reservation_characteristics` and add to the response:

```python
from models.characteristic_assignments import get_reservation_characteristics

# In the response building:
reservation_characteristics = get_reservation_characteristics(reservation_id)
```

Add `'reservation_characteristics': reservation_characteristics` to the JSON response alongside the existing `customer.preferences`.

**Step 3: Run tests**

Run: `python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add <modified file>
git commit -m "feat: include reservation characteristics in panel API response"
```

---

### Task 4: Frontend - Update save flow to also save reservation characteristics

**Files:**
- Modify: `static/js/map/reservation-panel-v2/save-mixin.js:449-481`

**Step 1: Add reservation characteristics save alongside customer save**

In `saveChanges()`, after the customer preferences save block (lines 450-481), add a parallel save for reservation characteristics:

```javascript
            // Save reservation characteristics to junction table
            if (preferencesChanged) {
                const resPrefResponse = await fetch(
                    `${this.options.apiBaseUrl}/map/reservations/${this.state.reservationId}/update`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.csrfToken
                        },
                        body: JSON.stringify({
                            preferences: selectedCodes.join(',')
                        })
                    }
                );
                // Error is already handled by the PATCH endpoint
            }
```

**Note:** This sends the preferences as CSV to the existing PATCH endpoint, which now (from Task 2) writes to the junction table too.

**Step 2: Verify manually**

1. Open map, click a reservation, enter edit mode
2. Toggle a preference
3. Click save
4. Verify the reservation's characteristics updated (check DB or re-open panel)

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/save-mixin.js
git commit -m "feat: save characteristics to reservation on panel save"
```

---

### Task 5: Frontend - Display reservation characteristics (not just customer)

**Files:**
- Modify: `static/js/map/reservation-panel-v2/preferences-mixin.js:45-72`

**Step 1: Update renderPreferencesSection to show reservation characteristics**

Currently it reads `customer.preferences`. Update to prefer `reservation_characteristics` from the API response (added in Task 3), falling back to customer preferences:

```javascript
    renderPreferencesSection(customer) {
        if (!this.preferencesChipsContainer) return;

        // Prefer reservation-specific characteristics over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const preferences = reservationChars.length > 0 ? reservationChars : (customer?.preferences || []);

        // ... rest stays the same
```

**Step 2: Update enterPreferencesEditMode to use reservation characteristics**

In `enterPreferencesEditMode()`, change line 91-92 to prefer reservation characteristics:

```javascript
        // Get current preferences - prefer reservation-specific over customer defaults
        const reservationChars = this.state.data?.reservation_characteristics || [];
        const customerPrefs = this.state.data?.customer?.preferences || [];
        const activePrefs = reservationChars.length > 0 ? reservationChars : customerPrefs;
        this.preferencesEditState.selectedCodes = activePrefs.map(p => p.code);
        this.preferencesEditState.originalCodes = [...this.preferencesEditState.selectedCodes];
```

**Step 3: Update section label**

In `templates/beach/_reservation_panel.html` line 111, change:

```html
                    Preferencias
```

To:

```html
                    Características
```

And line 124-127, change the sync note:

```html
                    <p class="preferences-sync-note">
                        <i class="fas fa-sync-alt"></i>
                        Los cambios se aplican a la reserva y al perfil del cliente
                    </p>
```

**Step 4: Commit**

```bash
git add static/js/map/reservation-panel-v2/preferences-mixin.js templates/beach/_reservation_panel.html
git commit -m "feat: display reservation characteristics in panel"
```

---

### Task 6: Data migration - Sync existing CSV preferences to junction table

**Files:**
- Create: `scripts/migrate_reservation_characteristics.py`

**Step 1: Write migration script**

```python
"""
One-time migration: sync existing reservation preferences CSV
to the beach_reservation_characteristics junction table.
Idempotent - safe to run multiple times.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import get_db
from models.characteristic_assignments import (
    get_reservation_characteristic_ids,
    set_reservation_characteristics_by_codes
)


def migrate():
    app = create_app()
    with app.app_context():
        with get_db() as conn:
            cursor = conn.execute('''
                SELECT id, preferences
                FROM beach_reservations
                WHERE preferences IS NOT NULL AND preferences != ''
            ''')
            reservations = cursor.fetchall()

        migrated = 0
        skipped = 0

        for res in reservations:
            res_id = res['id']
            csv = res['preferences']

            # Skip if junction table already populated
            existing = get_reservation_characteristic_ids(res_id)
            if existing:
                skipped += 1
                continue

            # Parse CSV and sync
            codes = [c.strip() for c in csv.split(',') if c.strip()]
            if codes:
                set_reservation_characteristics_by_codes(res_id, codes)
                migrated += 1

        print(f'Migration complete: {migrated} migrated, {skipped} skipped (already had data)')


if __name__ == '__main__':
    migrate()
```

**Step 2: Run migration**

Run: `python scripts/migrate_reservation_characteristics.py`
Expected: Shows count of migrated reservations

**Step 3: Commit**

```bash
git add scripts/migrate_reservation_characteristics.py
git commit -m "feat: add migration script for reservation characteristics"
```

---

### Task 7: Cleanup - Remove dead reservation form template code

**Files:**
- Check: `templates/beach/reservation_form.html` and `templates/beach/reservation_form_NEW.html`
- Check: `templates/beach/reservation_form/_step2_details.html`

**Step 1: Verify templates are not used by any route**

Search all blueprints for references to these templates. If confirmed unused (no route renders them), they are dead code from before the unified panel was built.

**Step 2: If confirmed dead, delete them**

```bash
rm templates/beach/reservation_form.html
rm templates/beach/reservation_form_NEW.html
rm -rf templates/beach/reservation_form/
```

**Step 3: Run tests to confirm nothing breaks**

Run: `python -m pytest tests/ -x -q`
Expected: All pass

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove dead reservation form templates

The reservation form templates are no longer used - all reservation
creation/editing goes through the unified panel (reservation_unified.html)."
```

---

### Task 8: Final verification

**Step 1: Manual end-to-end test**

1. Start server: `python app.py`
2. Create a reservation from the map with characteristics selected
3. Verify characteristics appear in the panel view mode
4. Open reservation from `/beach/reservations` list (unified page)
5. Enter edit mode, toggle characteristics, save
6. Re-open and verify changes persisted
7. Check the suggestion algorithm works (characteristics should influence furniture suggestions)

**Step 2: Run full test suite**

Run: `python -m pytest tests/ -x -q`
Expected: All 300 tests pass

**Step 3: Close the issue**

```bash
gh issue close 21
```
