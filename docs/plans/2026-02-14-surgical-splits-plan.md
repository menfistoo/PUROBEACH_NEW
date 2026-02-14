# Surgical Splits: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split monolithic JS files, split large Python models, and consolidate V1/V2 panels into a maintainable, scalable foundation before production launch (March 2026).

**Architecture:** Targeted splits of 4 critical JS monoliths using MapPageContext shared object, light-touch Python model splits with re-export pattern, and V1→V2 panel consolidation via creation mixins. Same concatenation-based bundling — no build tool changes.

**Tech Stack:** JavaScript ES6 (non-module, bundled via cat/sed), Python 3.11+/Flask, SQLite

**Design doc:** `docs/plans/2026-02-14-surgical-splits-design.md`

---

## Phase 1: map-page.js Split (8 Modules)

**Current:** `static/js/map/map-page.js` — 2,368 lines, 23+ features in one `DOMContentLoaded` handler
**Target:** 8 focused modules in `static/js/map/map-page/` + bundle replaces monolith

### Task 1: Create map-page directory and MapPageContext

**Files:**
- Create: `static/js/map/map-page/map-init.js`

**Step 1: Create the directory and first module**

Create `static/js/map/map-page/map-init.js` with the map initialization code. This module:
- Defines the `MapPageContext` object (`ctx`)
- Instantiates `BeachMap`
- Sets `window.beachMap`
- Re-applies zone view on render

Extract from `map-page.js` lines 1-25 (CSRF token, date, zone, map instantiation) and lines 2358-2365 (onRender zone re-apply):

```javascript
/**
 * Map Page Init Module
 * Creates MapPageContext and instantiates BeachMap
 */

// MapPageContext — shared by all map-page modules
const ctx = {
    map: null,
    csrfToken: null,
    currentDate: null,
    currentZoneId: null,
    moveMode: null,
    moveModePanel: null,
    blockManager: null,
    searchManager: null,
    reservationPanel: null,
    newReservationPanel: null,
    waitlistManager: null
};

function initMapPage() {
    // Extract from map-page.js lines 14-25
    ctx.csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const currentDateInput = document.getElementById('current-date');
    ctx.currentDate = currentDateInput?.value || new Date().toISOString().split('T')[0];

    const zoneSelect = document.getElementById('zone-select');
    ctx.currentZoneId = zoneSelect?.value || null;

    // Instantiate map (from line 14)
    ctx.map = new BeachMap('map-container', { /* existing options from map-page.js line 14 */ });
    window.beachMap = ctx.map;
}
```

**Step 2: Verify file was created**

Run: `wc -l static/js/map/map-page/map-init.js`
Expected: ~50-80 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-init.js
git commit -m "refactor: create map-init.js with MapPageContext (Phase 1.1)"
```

---

### Task 2: Extract map-managers.js

**Files:**
- Create: `static/js/map/map-page/map-managers.js`

**Step 1: Create managers module**

Extract from `map-page.js`:
- Lines 27-61: BlockManager setup + event wiring
- Lines 63-98: TempFurnitureManager setup + events
- Lines 295-371: WaitlistManager setup + badge + events

All managers store their instances on `ctx` (e.g., `ctx.blockManager`, `ctx.waitlistManager`).

```javascript
/**
 * Map Page Managers Module
 * BlockManager, TempFurnitureManager, WaitlistManager setup
 */

function initMapManagers(ctx) {
    // BlockManager (lines 27-61)
    ctx.blockManager = new BlockManager(/* ... */);
    // ... event wiring ...

    // TempFurnitureManager (lines 63-98)
    // ... setup ...

    // WaitlistManager (lines 295-371)
    ctx.waitlistManager = new WaitlistManager(/* ... */);
    // ... badge update, events ...
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-managers.js`
Expected: ~150-180 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-managers.js
git commit -m "refactor: extract map-managers.js — BlockManager, WaitlistManager (Phase 1.2)"
```

---

### Task 3: Extract map-move-mode.js

**Files:**
- Create: `static/js/map/map-page/map-move-mode.js`

**Step 1: Create move mode module**

Extract from `map-page.js` lines 100-294:
- MoveMode instantiation + `window.moveMode`
- MoveModePanel instantiation
- Global move mode badge update
- Onboarding overlay handler
- MoveMode event listeners (onActivate, onDeactivate, onPoolUpdate, etc.)

```javascript
/**
 * Map Page Move Mode Module
 * MoveMode + MoveModePanel init, global badge, onboarding
 */

function initMapMoveMode(ctx) {
    // MoveMode (lines 100-294)
    ctx.moveMode = new MoveMode(/* ... */);
    window.moveMode = ctx.moveMode;
    ctx.moveModePanel = new MoveModePanel('move-mode-panel-container', ctx.moveMode);
    // ... event listeners, badge, onboarding ...
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-move-mode.js`
Expected: ~180-200 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-move-mode.js
git commit -m "refactor: extract map-move-mode.js — MoveMode + panel init (Phase 1.3)"
```

---

### Task 4: Extract map-search.js

**Files:**
- Create: `static/js/map/map-page/map-search.js`

**Step 1: Create search module**

Extract from `map-page.js` lines 373-480:
- SearchManager instantiation
- Filter dropdown population (time slot, furniture type)
- Ctrl+F keyboard shortcut override
- Search event handlers

```javascript
/**
 * Map Page Search Module
 * SearchManager init, filter dropdowns, Ctrl+F shortcut
 */

function initMapSearch(ctx) {
    ctx.searchManager = new SearchManager(/* ... */);
    // ... filter dropdowns, Ctrl+F ...
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-search.js`
Expected: ~100-120 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-search.js
git commit -m "refactor: extract map-search.js — SearchManager + filters (Phase 1.4)"
```

---

### Task 5: Extract map-panels.js

**Files:**
- Create: `static/js/map/map-page/map-panels.js`

**Step 1: Create panels module**

Extract from `map-page.js` lines 483-616:
- ReservationPanel (V2) instantiation (lines 483-513)
- NewReservationPanel (V1) instantiation (lines 515-616)
- `openReservationPanel()` function
- `openNewReservationPanel()` function
- AddMoreFurniture mode handling

```javascript
/**
 * Map Page Panels Module
 * ReservationPanel + NewReservationPanel init, addMoreFurniture
 */

function initMapPanels(ctx) {
    ctx.reservationPanel = new ReservationPanel(/* ... */);
    ctx.newReservationPanel = new NewReservationPanel(/* ... */);
    // ... helper functions ...
}
```

Note: `openReservationPanel` and `openNewReservationPanel` are called from other modules (map-interaction, map-conflicts). They should be attached to `ctx` or defined in a scope accessible to the DOMContentLoaded closure.

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-panels.js`
Expected: ~150-200 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-panels.js
git commit -m "refactor: extract map-panels.js — V1+V2 panel init (Phase 1.5)"
```

---

### Task 6: Extract map-conflicts.js

**Files:**
- Create: `static/js/map/map-page/map-conflicts.js`

**Step 1: Create conflicts module**

Extract from `map-page.js` lines 618-1169:
- Conflict resolution context and state (lines 618-650)
- `handleConflictsResponse()` (lines 650-750)
- `selectAlternativeFurniture()` (lines 750-830)
- Conflict instruction rendering (lines 830-900)
- Selection bar update for conflict mode (lines 900-950)
- Conflict completion handler (lines 950-1010)
- Quick swap (lines 1010-1169): modal, destination mode, `performQuickSwap()`, `showQuickSwapModal()`

This is the largest single module (~550 lines) because conflict resolution and quick swap are tightly coupled. Both share `conflictResolutionContext` and `quickSwapContext` state.

```javascript
/**
 * Map Page Conflicts Module
 * Conflict resolution + quick swap (tightly coupled, kept together)
 */

function initMapConflicts(ctx) {
    let conflictResolutionContext = null;
    let quickSwapContext = null;
    // ... all conflict + quick swap functions ...
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-conflicts.js`
Expected: ~400-550 lines (acceptable — tightly coupled domain)

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-conflicts.js
git commit -m "refactor: extract map-conflicts.js — conflict resolution + quick swap (Phase 1.6)"
```

---

### Task 7: Extract map-navigation.js

**Files:**
- Create: `static/js/map/map-page/map-navigation.js`

**Step 1: Create navigation module**

Extract from `map-page.js`:
- Lines 1171-1245: Touch handler for long-press context menu
- Lines 1247-1329: Date navigation (prev/next day, date picker)
- Lines 1331-1404: Zone selector (populate, apply view, filter)
- Lines 1406-1442: Stats display (`updateStats()`)
- Lines 1444-1507: Canvas info bar
- Lines 1509-1519: Zoom controls (+/- buttons)
- Lines 1521-1594: Save/restore view state (localStorage)
- Lines 1596-1736: Map editor navigation (Shift+wheel zoom, space+drag pan)

```javascript
/**
 * Map Page Navigation Module
 * Date nav, zone selector, zoom/pan, save/restore view, canvas info
 */

function initMapNavigation(ctx) {
    // Date navigation (lines 1247-1329)
    // Zone selector (lines 1331-1404)
    // Stats (lines 1406-1442)
    // Canvas info (lines 1444-1507)
    // Zoom controls (lines 1509-1519)
    // Save/restore view (lines 1521-1594)
    // Editor nav (lines 1596-1736)
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-navigation.js`
Expected: ~350-400 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-navigation.js
git commit -m "refactor: extract map-navigation.js — date/zone/zoom/pan (Phase 1.7)"
```

---

### Task 8: Extract map-interaction.js

**Files:**
- Create: `static/js/map/map-page/map-interaction.js`

**Step 1: Create interaction module**

Extract from `map-page.js`:
- Lines 1738-1846: Keyboard shortcuts (Escape, Ctrl+Z, R, etc.)
- Lines 1848-1859: Refresh + auto-refresh interval
- Lines 1861-1876: Pinch zoom (touch events)
- Lines 1878-1952: Selection bar (`updateSelectionBar()`, `updateSelectionActions()`)
- Lines 1954-2021: Selection action buttons (Reservar, Ver Reserva, mixed)
- Lines 2023-2143: `onFurnitureClick` callback (move mode, quick swap, conflict, normal mode)
- Lines 2145-2172: Clear selection + block selection buttons
- Lines 2174-2347: Context menu (show, position, action handler)
- Lines 2349-2356: Escape key handler

```javascript
/**
 * Map Page Interaction Module
 * Keyboard shortcuts, selection bar, furniture click handler, context menu, touch
 */

function initMapInteraction(ctx) {
    // Selection bar (lines 1878-2021)
    // onFurnitureClick (lines 2023-2143)
    // Context menu (lines 2174-2347)
    // Keyboard shortcuts (lines 1738-1846)
    // Auto-refresh (lines 1848-1859)
    // Pinch zoom (lines 1861-1876)
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/map-page/map-interaction.js`
Expected: ~400-500 lines

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-interaction.js
git commit -m "refactor: extract map-interaction.js — clicks, keys, context menu (Phase 1.8)"
```

---

### Task 9: Build map-page-bundle.js and wire up

**Files:**
- Create: `static/js/map-page-bundle.js`
- Modify: `templates/beach/map.html:598`

**Step 1: Build the bundle**

Concatenate all 8 modules in dependency order, stripping imports/exports:

```bash
# Create bundle from 8 source files
echo "// =============================================================================" > static/js/map-page-bundle.js
echo "// MAP PAGE BUNDLE - Split from monolithic map-page.js" >> static/js/map-page-bundle.js
echo "// Source files in static/js/map/map-page/ for maintainability" >> static/js/map-page-bundle.js
echo "// =============================================================================" >> static/js/map-page-bundle.js
echo "" >> static/js/map-page-bundle.js

for file in map-init.js map-managers.js map-move-mode.js map-search.js \
            map-panels.js map-conflicts.js map-navigation.js map-interaction.js; do
    echo "" >> static/js/map-page-bundle.js
    echo "// --- $file ---" >> static/js/map-page-bundle.js
    sed -E '/^import /d; s/^export //' "static/js/map/map-page/$file" >> static/js/map-page-bundle.js
done
```

Wrap everything in a `DOMContentLoaded` handler:

```javascript
document.addEventListener('DOMContentLoaded', () => {
    initMapPage();       // map-init.js
    initMapManagers(ctx);  // map-managers.js
    initMapMoveMode(ctx);  // map-move-mode.js
    initMapSearch(ctx);    // map-search.js
    initMapPanels(ctx);    // map-panels.js
    initMapConflicts(ctx); // map-conflicts.js
    initMapNavigation(ctx);// map-navigation.js
    initMapInteraction(ctx);// map-interaction.js
});
```

**Step 2: Update map.html**

In `templates/beach/map.html` line 598, replace:
```html
<script src="{{ url_for('static', filename='js/map/map-page.js') }}"></script>
```
with:
```html
<script src="{{ url_for('static', filename='js/map-page-bundle.js') }}"></script>
```

**Step 3: Test in browser**

- Load `/beach/map`
- Verify map renders correctly
- Test: date navigation, zone selector, selection bar, reservation panel open, context menu
- Check browser console for errors
- Test keyboard shortcuts (Ctrl+F, Escape, R)

**Step 4: Commit**

```bash
git add static/js/map-page-bundle.js templates/beach/map.html
git commit -m "refactor: build map-page-bundle.js, replace monolithic map-page.js (Phase 1.9)"
```

---

### Task 10: Keep original map-page.js for reference, verify no regressions

**Files:**
- Rename: `static/js/map/map-page.js` → `static/js/map/map-page.js.bak` (temporary)

**Step 1: Rename original to .bak**

```bash
mv static/js/map/map-page.js static/js/map/map-page.js.bak
```

**Step 2: Full regression test**

Test ALL map functionality:
1. Map loads without console errors
2. Date navigation (prev/next/picker)
3. Zone selector filters correctly
4. Click furniture → selection bar appears
5. Click occupied furniture → reservation panel opens
6. Ctrl+F → search opens
7. Context menu on right-click
8. Move mode activates/deactivates
9. New reservation flow
10. Conflict resolution (if testable)

**Step 3: If all tests pass, delete .bak**

```bash
rm static/js/map/map-page.js.bak
git add -A
git commit -m "refactor: remove original map-page.js after successful split (Phase 1.10)"
```

**If issues found:** Restore from .bak, fix the modules, rebuild bundle.

---

## Phase 2: MoveModePanel Split (3 Files)

**Current:** `static/js/map/MoveModePanel.js` — 961 lines
**Target:** 3 files in `static/js/map/move-mode-panel/`

### Task 11: Extract MoveModePanelRenderer.js

**Files:**
- Create: `static/js/map/move-mode-panel/MoveModePanelRenderer.js`

**Step 1: Identify rendering methods in MoveModePanel.js**

Look for these methods (approximate locations — verify by reading the file):
- `renderPoolItem()` — renders a single pool item card
- `renderPoolList()` — renders the full pool list
- `renderCollapsedThumbnails()` — renders collapsed state thumbnails
- Badge/count HTML generation
- Capacity display rendering
- Legend rendering

Extract all rendering-related methods into `MoveModePanelRenderer`:

```javascript
/**
 * MoveModePanel Renderer
 * Handles all HTML rendering for pool items, list, badges, capacity
 */
class MoveModePanelRenderer {
    constructor(panel) {
        this.panel = panel;
    }

    renderPoolItem(item) { /* ... */ }
    renderPoolList(items) { /* ... */ }
    renderCollapsedThumbnails(items) { /* ... */ }
    renderLegend(preferences) { /* ... */ }
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/move-mode-panel/MoveModePanelRenderer.js`
Expected: ~300-350 lines

**Step 3: Commit**

```bash
git add static/js/map/move-mode-panel/MoveModePanelRenderer.js
git commit -m "refactor: extract MoveModePanelRenderer.js (Phase 2.1)"
```

---

### Task 12: Extract MoveModePanelFilters.js

**Files:**
- Create: `static/js/map/move-mode-panel/MoveModePanelFilters.js`

**Step 1: Identify filter methods**

Look for:
- `applyFilters()` — filter pool items by type/VIP/preferences
- Filter state management (`this.filters = { type, vip, hasPreferences }`)
- Filter UI event handlers (filter buttons, checkboxes)
- Search input handling (if any)

```javascript
/**
 * MoveModePanel Filters
 * Filter state, applyFilters(), type/VIP/preference filter UI
 */
class MoveModePanelFilters {
    constructor(panel) {
        this.panel = panel;
        this.filters = { type: 'all', vip: false, hasPreferences: false };
    }

    applyFilters(items) { /* ... */ }
    setupFilterListeners() { /* ... */ }
}
```

**Step 2: Verify**

Run: `wc -l static/js/map/move-mode-panel/MoveModePanelFilters.js`
Expected: ~150-200 lines

**Step 3: Commit**

```bash
git add static/js/map/move-mode-panel/MoveModePanelFilters.js
git commit -m "refactor: extract MoveModePanelFilters.js (Phase 2.2)"
```

---

### Task 13: Refactor MoveModePanel.js to use renderer + filters

**Files:**
- Modify: `static/js/map/MoveModePanel.js`
- Create: `static/js/map/move-mode-panel/MoveModePanel.js` (refactored core)

**Step 1: Refactor core class**

The core MoveModePanel now delegates to renderer and filters:

```javascript
class MoveModePanel {
    constructor(containerId, moveMode) {
        this.renderer = new MoveModePanelRenderer(this);
        this.filters = new MoveModePanelFilters(this);
        // ... rest of constructor (DOM setup, event listeners) ...
    }

    // Core methods: open, close, collapse, pool state, API calls
    // Delegates rendering to this.renderer
    // Delegates filtering to this.filters
}
```

**Step 2: Verify core is ~400 lines**

Run: `wc -l static/js/map/move-mode-panel/MoveModePanel.js`
Expected: ~350-400 lines

**Step 3: Commit**

```bash
git add static/js/map/move-mode-panel/MoveModePanel.js
git commit -m "refactor: slim MoveModePanel.js core, delegate to renderer+filters (Phase 2.3)"
```

---

### Task 14: Update map-core-bundle.js with split MoveModePanel

**Files:**
- Modify: `static/js/map-core-bundle.js`

**Step 1: Rebuild map-core-bundle.js**

Replace the single MoveModePanel section in the bundle with the 3 new files (in order: Renderer, Filters, Core):

1. Find the `// --- MoveModePanel.js ---` section in `map-core-bundle.js`
2. Replace it with the 3 files concatenated (stripped of imports/exports)

**Step 2: Test in browser**

- Load `/beach/map`
- Activate move mode
- Verify panel opens, pool renders, filters work
- Test collapse/expand
- Test undo

**Step 3: Commit**

```bash
git add static/js/map-core-bundle.js
git commit -m "refactor: rebuild map-core-bundle.js with split MoveModePanel (Phase 2.4)"
```

---

## Phase 3: Python Model Splits

### Task 15: Split reservation_multiday.py

**Files:**
- Create: `models/reservation_multiday_create.py`
- Create: `models/reservation_multiday_manage.py`
- Create: `models/reservation_multiday_queries.py`
- Modify: `models/reservation_multiday.py` (re-exports only)

**Current structure:** `models/reservation_multiday.py` — 665 lines with:
- `create_linked_multiday_reservations()` (~320 lines) — creation
- `update_multiday_reservations()` (~100 lines) — updates
- `cancel_multiday_reservations()` (~100 lines) — cancellation
- `get_multiday_summary()`, `is_parent_reservation()`, `get_child_reservations()` (~100 lines) — queries

**Step 1: Create reservation_multiday_create.py**

Move `create_linked_multiday_reservations()` and any helper functions it uses exclusively.

```python
"""
Multi-day reservation creation.
Extracted from reservation_multiday.py for maintainability.
"""
from database import get_db
from .reservation_crud import (
    generate_reservation_number,
    generate_child_reservation_number,
    sync_preferences_to_customer
)
# ... other imports used by create function ...

def create_linked_multiday_reservations(...):
    # Full function body from original
    pass
```

**Step 2: Create reservation_multiday_manage.py**

Move `update_multiday_reservations()` and `cancel_multiday_reservations()`.

**Step 3: Create reservation_multiday_queries.py**

Move `get_multiday_summary()`, `is_parent_reservation()`, `get_child_reservations()`.

**Step 4: Update reservation_multiday.py as re-export hub**

```python
"""
Multi-day (linked) reservation management.
Re-exports for backward compatibility.
"""
from .reservation_multiday_create import create_linked_multiday_reservations
from .reservation_multiday_manage import update_multiday_reservations, cancel_multiday_reservations
from .reservation_multiday_queries import get_multiday_summary, is_parent_reservation, get_child_reservations
```

**Step 5: Run tests**

```bash
python -m pytest tests/ -x -q
```

Expected: All tests pass (no behavior change, just re-organization)

**Step 6: Commit**

```bash
git add models/reservation_multiday*.py
git commit -m "refactor: split reservation_multiday.py into 4 focused modules (Phase 3.1)"
```

---

### Task 16: Extract reservation_ticket.py from reservation_crud.py

**Files:**
- Create: `models/reservation_ticket.py`
- Modify: `models/reservation_crud.py`

**Step 1: Create reservation_ticket.py**

Extract `generate_reservation_number()` (lines 26-80) and `generate_child_reservation_number()` from `reservation_crud.py`:

```python
"""
Reservation ticket number generation.
Extracted from reservation_crud.py.
"""
from database import get_db
from datetime import datetime

def generate_reservation_number(reservation_date: str = None, cursor=None, max_retries: int = 5) -> str:
    # Full function body
    pass

def generate_child_reservation_number(parent_number: str, child_index: int) -> str:
    # Full function body
    pass
```

**Step 2: Update reservation_crud.py**

Replace the extracted functions with an import:

```python
# At top of reservation_crud.py, add:
from .reservation_ticket import generate_reservation_number, generate_child_reservation_number
```

Remove the function bodies from `reservation_crud.py`.

**Step 3: Run tests**

```bash
python -m pytest tests/ -x -q
```

Expected: All tests pass

**Step 4: Verify line count**

```bash
wc -l models/reservation_crud.py models/reservation_ticket.py
```

Expected: `reservation_crud.py` ~560 lines, `reservation_ticket.py` ~80 lines

**Step 5: Commit**

```bash
git add models/reservation_ticket.py models/reservation_crud.py
git commit -m "refactor: extract reservation_ticket.py from reservation_crud.py (Phase 3.2)"
```

---

## Phase 4: V1 → V2 Panel Consolidation

**Current:** V1 (6 files, 2,730 lines) + V2 (13 files, 4,145 lines) = 2 architectures
**Target:** V2 only (13 + 5 new mixins, ~5,525 lines) = 1 unified architecture, -1,240 lines net

### Task 17: Create creation-mode-mixin.js

**Files:**
- Create: `static/js/map/reservation-panel-v2/creation-mode-mixin.js`

**Step 1: Write the mixin**

Core creation mode support — determines whether panel is in 'view', 'edit', or 'create' mode:

```javascript
/**
 * Creation Mode Mixin
 * Core creation mode support for ReservationPanel
 */
import { showToast } from './utils.js';

export const CreationModeMixin = (Base) => class extends Base {
    /**
     * Open panel for creating a new reservation
     * @param {number[]} furnitureIds - Selected furniture IDs from map
     * @param {string} date - Reservation date (YYYY-MM-DD)
     * @param {Object} [waitlistEntry] - Optional waitlist entry for conversion
     */
    openForCreation(furnitureIds, date, waitlistEntry = null) {
        this.initCreationState(furnitureIds, date);
        if (waitlistEntry) {
            this.prefillFromWaitlist(waitlistEntry);
        }
        this.showCreationUI();
        this.open();
    }

    initCreationState(furnitureIds, date) {
        this.state.mode = 'create';
        this.state.reservationId = null;
        this.state.data = null;
        this.state.creationData = {
            furnitureIds,
            date,
            customerId: null,
            customerSource: null,
            numPeople: 1,
            timeSlot: 'all_day',
            notes: '',
            tagIds: [],
            preferenceIds: [],
            packageId: null,
            priceOverride: null,
            waitlistId: null
        };
    }

    resetCreationForm() { /* Reset all creation fields */ }
    isCreationMode() { return this.state.mode === 'create'; }

    showCreationUI() {
        // Show creation-specific sections, hide view/edit sections
    }

    hideCreationUI() {
        // Hide creation sections, restore view/edit sections
    }

    prefillFromWaitlist(entry) {
        // Populate creation data from waitlist entry
    }
};
```

**Step 2: Verify**

Run: `wc -l static/js/map/reservation-panel-v2/creation-mode-mixin.js`
Expected: ~150 lines

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/creation-mode-mixin.js
git commit -m "feat: add creation-mode-mixin.js — core creation mode for V2 panel (Phase 4.1)"
```

---

### Task 18: Create creation-customer-mixin.js

**Files:**
- Create: `static/js/map/reservation-panel-v2/creation-customer-mixin.js`

**Step 1: Write the mixin**

Port customer selection and inline creation from V1's `customer-handler.js` (652 lines). Adapt to V2 mixin pattern:

```javascript
/**
 * Creation Customer Mixin
 * Customer search, inline creation, hotel guest lookup for new reservations
 */
import { escapeHtml, showToast } from './utils.js';

export const CreationCustomerMixin = (Base) => class extends Base {
    initCreationCustomerSearch() { }
    showCreateCustomerForm() { }
    async saveNewCustomer() { }
    async handleHotelGuestSelect(guestId) { }
    async convertGuestToCustomer(guestId) { }
    async fetchRoomGuests(roomNumber) { }
    populateFromCustomer(customer) { }
};
```

Port logic from `reservation-panel/customer-handler.js` — the V1 customer handler. Key functions:
- Customer search with autocomplete
- Inline form: first/last name, email, phone, language, customer type
- Hotel guest lookup by room number
- Auto-populate num_people from guest count

**Step 2: Verify**

Run: `wc -l static/js/map/reservation-panel-v2/creation-customer-mixin.js`
Expected: ~300-350 lines

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/creation-customer-mixin.js
git commit -m "feat: add creation-customer-mixin.js — customer search/create for V2 (Phase 4.2)"
```

---

### Task 19: Create creation-safeguards-mixin.js

**Files:**
- Create: `static/js/map/reservation-panel-v2/creation-safeguards-mixin.js`

**Step 1: Write the mixin**

Port pre-creation validation from V1's `safeguard-checks.js` (329 lines):

```javascript
/**
 * Creation Safeguards Mixin
 * Pre-creation validation (7 safeguard checks)
 */
import { showToast } from './utils.js';

export const CreationSafeguardsMixin = (Base) => class extends Base {
    async runSafeguardChecks() { }   // Orchestrator
    checkPastDates() { }              // SG-05
    checkHotelStayDates() { }         // SG-03
    checkCapacityMismatch() { }       // SG-04
    checkFurnitureAvailability() { }  // SG-02
    checkDuplicateReservation() { }   // SG-01
    checkFurnitureContiguity() { }    // SG-07
};
```

Each check returns `{ pass: bool, warning: string, canProceed: bool }`.
Uses SafeguardModal for user confirmations (existing component).

**Step 2: Verify**

Run: `wc -l static/js/map/reservation-panel-v2/creation-safeguards-mixin.js`
Expected: ~280-300 lines

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/creation-safeguards-mixin.js
git commit -m "feat: add creation-safeguards-mixin.js — validation checks for V2 (Phase 4.3)"
```

---

### Task 20: Create creation-conflict-mixin.js

**Files:**
- Create: `static/js/map/reservation-panel-v2/creation-conflict-mixin.js`

**Step 1: Write the mixin**

Port multi-day conflict resolution from V1's `conflict-resolver.js` (240 lines):

```javascript
/**
 * Creation Conflict Mixin
 * Multi-day conflict resolution during creation
 */
import { showToast } from './utils.js';

export const CreationConflictMixin = (Base) => class extends Base {
    handleConflictResponse(conflicts) { }
    showConflictModal(conflicts) { }
    navigateToConflictDay(date) { }
    retryWithPerDayFurniture(furnitureByDate) { }
    persistCustomerDuringConflict() { }
};
```

**Step 2: Verify**

Run: `wc -l static/js/map/reservation-panel-v2/creation-conflict-mixin.js`
Expected: ~180-200 lines

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/creation-conflict-mixin.js
git commit -m "feat: add creation-conflict-mixin.js — conflict resolution for V2 (Phase 4.4)"
```

---

### Task 21: Create creation-save-mixin.js

**Files:**
- Create: `static/js/map/reservation-panel-v2/creation-save-mixin.js`

**Step 1: Write the mixin**

Port creation submission from V1's `panel-core.js` save logic:

```javascript
/**
 * Creation Save Mixin
 * Creation submission, payload building, waitlist conversion
 */
import { showToast } from './utils.js';

export const CreationSaveMixin = (Base) => class extends Base {
    async createReservation() { }
    buildCreationPayload() { }
    async markWaitlistAsConverted(waitlistId) { }
    handleCreationSuccess(result) { }
    handleCreationError(error) { }
};
```

- Runs safeguard checks first via `this.runSafeguardChecks()`
- Builds payload from `this.state.creationData`
- POST to `/beach/api/map/quick-reservation`
- Handles conflict response (delegates to conflict mixin)
- Waitlist conversion on success

**Step 2: Verify**

Run: `wc -l static/js/map/reservation-panel-v2/creation-save-mixin.js`
Expected: ~180-200 lines

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/creation-save-mixin.js
git commit -m "feat: add creation-save-mixin.js — submission + waitlist for V2 (Phase 4.5)"
```

---

### Task 22: Extend pricing-mixin.js and furniture-mixin.js for creation

**Files:**
- Modify: `static/js/map/reservation-panel-v2/pricing-mixin.js`
- Modify: `static/js/map/reservation-panel-v2/furniture-mixin.js`

**Step 1: Add creation pricing methods to pricing-mixin.js**

Add ~100 lines for creation context:

```javascript
// Add to PricingMixin:
initCreationPricing() { }       // Fetch packages for new reservation params
onCreationParamsChange() { }    // Recalculate when customer/date/furniture changes
```

**Step 2: Add creation furniture methods to furniture-mixin.js**

Add ~80 lines for creation context:

```javascript
// Add to FurnitureMixin:
renderCreationFurniture(furnitureIds) { }  // Show selected furniture from map
calculateCreationCapacity() { }            // Total capacity for selected furniture
showCapacityWarning(needed, available) { }  // Warning + "Add More" button
```

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/pricing-mixin.js static/js/map/reservation-panel-v2/furniture-mixin.js
git commit -m "feat: extend pricing + furniture mixins for creation mode (Phase 4.6)"
```

---

### Task 23: Update index.js composition and HTML template

**Files:**
- Modify: `static/js/map/reservation-panel-v2/index.js`
- Modify: `templates/beach/_reservation_panel.html`

**Step 1: Update index.js mixin composition**

Add the 5 creation mixins to the composition chain:

```javascript
import { CreationModeMixin } from './creation-mode-mixin.js';
import { CreationCustomerMixin } from './creation-customer-mixin.js';
import { CreationSafeguardsMixin } from './creation-safeguards-mixin.js';
import { CreationConflictMixin } from './creation-conflict-mixin.js';
import { CreationSaveMixin } from './creation-save-mixin.js';

const ReservationPanel = CreationSaveMixin(
    CreationConflictMixin(
        CreationSafeguardsMixin(
            CreationCustomerMixin(
                CreationModeMixin(
                    SaveMixin(
                        DetailsMixin(
                            PricingMixin(
                                FurnitureMixin(
                                    StateMixin(
                                        TagsMixin(
                                            PreferencesMixin(
                                                CustomerMixin(
                                                    EditModeMixin(
                                                        PanelLifecycleMixin(
                                                            ReservationPanelBase
                                                        )))))))))))))));
```

**Step 2: Add creation HTML sections to template**

Add creation-specific sections to `_reservation_panel.html`:

```html
<!-- Creation-only sections (hidden by default) -->
<section class="panel-section creation-customer-section" id="creationCustomerSection" style="display:none;">
    <!-- Customer search input -->
    <!-- Create customer form -->
    <!-- Room guest selector -->
</section>

<section class="panel-section creation-furniture-section" id="creationFurnitureSection" style="display:none;">
    <!-- Selected furniture chips -->
    <!-- Capacity warning -->
    <!-- Add more furniture button -->
</section>
```

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/index.js templates/beach/_reservation_panel.html
git commit -m "feat: update V2 composition with creation mixins + HTML template (Phase 4.7)"
```

---

### Task 24: Rebuild map-panels-bundle.js with creation mixins

**Files:**
- Modify: `static/js/map-panels-bundle.js`

**Step 1: Rebuild bundle**

Add the 5 creation mixin files to the bundle, maintaining correct order (creation mixins after existing mixins, before index.js):

Bundle order:
1. utils.js
2. panel-base.js
3. panel-lifecycle.js
4. edit-mode-mixin.js
5. customer-mixin.js
6. preferences-mixin.js
7. tags-mixin.js
8. state-mixin.js
9. furniture-mixin.js
10. pricing-mixin.js
11. details-mixin.js
12. save-mixin.js
13. **creation-mode-mixin.js** (new)
14. **creation-customer-mixin.js** (new)
15. **creation-safeguards-mixin.js** (new)
16. **creation-conflict-mixin.js** (new)
17. **creation-save-mixin.js** (new)
18. index.js

**Step 2: Verify bundle**

- Check no `import` statements remain
- Check all `export` keywords removed
- Verify `window.ReservationPanel` is set at end

**Step 3: Commit**

```bash
git add static/js/map-panels-bundle.js
git commit -m "feat: rebuild map-panels-bundle.js with creation mixins (Phase 4.8)"
```

---

### Task 25: Wire map-panels.js to use V2 for creation

**Files:**
- Modify: `static/js/map/map-page/map-panels.js`

**Step 1: Update panel initialization**

In `map-panels.js` (from Phase 1), change the new reservation flow to use V2:

```javascript
// Before: ctx.newReservationPanel = new NewReservationPanel(...);
// After: Use ctx.reservationPanel.openForCreation()

function openNewReservationPanel() {
    const selected = ctx.map.getSelectedFurnitureData();
    const furnitureIds = selected.map(f => f.id);
    const date = ctx.map.getCurrentDate();
    ctx.reservationPanel.openForCreation(furnitureIds, date);
}
```

**Step 2: Test creation flow**

1. Select furniture on map
2. Click "Reservar" button
3. Verify V2 panel opens in creation mode
4. Search/create customer
5. Configure reservation details
6. Submit — verify creation succeeds

**Step 3: Commit**

```bash
git add static/js/map/map-page/map-panels.js
git commit -m "feat: wire map-panels.js to use V2 for creation (Phase 4.9)"
```

---

### Task 26: Remove V1 panel files

**Files:**
- Delete: `static/js/map/reservation-panel/` (6 files, 2,730 lines)
- Modify: `static/js/map-panels-bundle.js` (remove V1 sections)

**Step 1: Full regression test before deletion**

Test ALL reservation flows:
1. Create reservation (uses V2 creation mode now)
2. View reservation (V2 view mode)
3. Edit reservation (V2 edit mode)
4. Move mode
5. Conflict resolution
6. Waitlist conversion

**Step 2: Remove V1 files**

```bash
rm -rf static/js/map/reservation-panel/
```

**Step 3: Clean V1 references from bundle**

Remove any V1 (`NewReservationPanel`) sections from `map-panels-bundle.js`.

**Step 4: Final test**

Verify map page loads and all flows work without V1 code.

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove V1 panel (6 files, 2,730 lines) — V2 handles all modes (Phase 4.10)"
```

---

## Success Criteria

After all phases:

- [ ] No JS file exceeds 500 lines (except BeachMap.js at 1,053 — acceptable orchestrator)
- [ ] No Python production file exceeds 600 lines
- [ ] All existing functionality works identically (no behavior changes)
- [ ] V1 panel directory completely removed
- [ ] Single panel architecture for both create and edit
- [ ] All bundles rebuilt and verified
- [ ] `pytest` passes after Python splits
- [ ] Map page loads and works after JS splits
- [ ] No console errors on map page

## Execution Order Summary

| Task | Phase | What | Risk |
|------|-------|------|------|
| 1-9 | 1 | map-page.js → 8 modules + bundle | Low |
| 10 | 1 | Verify + remove original | Low |
| 11-14 | 2 | MoveModePanel → 3 files + rebuild | Low |
| 15-16 | 3 | Python model splits | Low |
| 17-21 | 4 | Create 5 V2 creation mixins | Medium |
| 22 | 4 | Extend existing V2 mixins | Low |
| 23-24 | 4 | Wire up composition + rebuild bundle | Medium |
| 25 | 4 | Switch map to V2 creation | Medium |
| 26 | 4 | Remove V1 files | Medium (regression risk) |
