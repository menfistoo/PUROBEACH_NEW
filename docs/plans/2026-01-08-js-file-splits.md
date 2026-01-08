# JavaScript File Splits Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring all JavaScript files into CLAUDE.md compliance (target 300-500 lines, max 600 per module)

**Architecture:** Delete obsolete files, complete partial splits, create new modular structures using ES6 classes and mixin patterns

**Tech Stack:** ES6 JavaScript, no build tools (direct browser loading)

---

## Overview

| File | Current Lines | Status | Action |
|------|--------------|--------|--------|
| `map-editor.js` | 1824 | Split complete in `map-editor/` | Delete old file |
| `reservation-panel.js` | 2390 | Partial split exists | Complete split, delete old |
| `WaitlistManager.js` | 1372 | Monolithic | Full split into modules |

---

## Task 1: Delete Old map-editor.js

**Files:**
- Delete: `static/js/map-editor.js`
- Verify: `static/js/map-editor/index.js` exists
- Verify: `templates/beach/config/map_editor.html` uses new path

**Step 1: Verify templates use new modular path**

Run: `grep -n "map-editor" templates/beach/config/map_editor.html templates/beach/config/furniture_manager.html`

Expected output should show:
```
type="module" src="...js/map-editor/index.js"
```

**Step 2: Delete the old monolithic file**

```bash
rm static/js/map-editor.js
```

**Step 3: Verify map editor still works**

Run: Start server, navigate to `/beach/config/map-editor`
Expected: Editor loads, furniture can be dragged, zoom works

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove obsolete map-editor.js (split complete)"
```

---

## Task 2: Complete reservation-panel.js Split

The split has been STARTED (modules exist in `static/js/map/reservation-panel/`) but:
- Old monolithic file still loaded alongside modules
- Templates load BOTH old file and new modules
- Need to consolidate

**Current state:**
- `reservation-panel.js` (2390 lines) - OLD, still loaded
- `reservation-panel/panel-core.js` (704 lines) - NEW module
- `reservation-panel/customer-handler.js` (692 lines) - NEW module
- `reservation-panel/pricing-calculator.js` (388 lines) - NEW module
- `reservation-panel/date-availability.js` (249 lines) - NEW module
- `reservation-panel/conflict-resolver.js` (240 lines) - NEW module
- `reservation-panel/safeguard-checks.js` (329 lines) - NEW module

**Files:**
- Analyze: `static/js/map/reservation-panel.js`
- Modify: `templates/beach/map.html`
- Modify: `templates/beach/reservation_unified.html`
- Delete: `static/js/map/reservation-panel.js` (after verification)

### Step 1: Analyze what's still in old file vs new modules

Run:
```bash
head -100 static/js/map/reservation-panel.js
grep "class \|function " static/js/map/reservation-panel.js | head -30
```

Check if ReservationPanel class in old file is still being used or if panel-core.js replaced it.

### Step 2: Test if old file can be removed

Temporarily comment out the old file in `map.html`:
```html
<!-- <script src="{{ url_for('static', filename='js/map/reservation-panel.js') }}"></script> -->
```

Test the map page - if reservation panel works, old file is redundant.

### Step 3: Update templates to remove old file

**map.html** - Remove line loading old `reservation-panel.js`:
```html
<!-- DELETE THIS LINE -->
<script src="{{ url_for('static', filename='js/map/reservation-panel.js') }}"></script>
```

**reservation_unified.html** - Update to load modular files:
```html
<!-- Replace single script with modules -->
<script src="{{ url_for('static', filename='js/map/reservation-panel/customer-handler.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/reservation-panel/date-availability.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/reservation-panel/pricing-calculator.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/reservation-panel/conflict-resolver.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/reservation-panel/safeguard-checks.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/reservation-panel/panel-core.js') }}"></script>
```

### Step 4: Delete old monolithic file

```bash
rm static/js/map/reservation-panel.js
```

### Step 5: Verify functionality

Test on `/beach/map`:
- [ ] Click on occupied furniture - panel opens
- [ ] Customer section displays correctly
- [ ] Edit mode works
- [ ] State changes work
- [ ] Pricing displays

Test on `/beach/reservations/{id}`:
- [ ] Standalone panel loads
- [ ] All sections render

### Step 6: Address warning-level files (if needed)

If `panel-core.js` (704) or `customer-handler.js` (692) cause issues, consider further splitting:
- Extract state-section.js from panel-core.js
- Extract furniture-section.js from panel-core.js

### Step 7: Commit

```bash
git add -A
git commit -m "refactor: complete reservation-panel.js split, remove old file"
```

---

## Task 3: Split WaitlistManager.js (1372 lines)

**Current structure (single class, 1372 lines):**
- Constructor & state (lines 14-58)
- DOM Caching (lines 60-142)
- Event Listeners (lines 144-195)
- Public API (lines 197-277)
- Tab Management (lines 279-306)
- Data Loading (lines 308-403)
- Rendering (lines 405-528)
- Entry Actions (lines 530-745)
- Modal/Form handling (lines 747-889)
- Room Search (lines 891-1000)
- Customer Search (lines 1002-1103)
- Form Submission (lines 1105-1244)
- Utilities (lines 1246-1372)

**Proposed module structure:**

```
static/js/waitlist/
├── index.js              # Main class + re-exports (~80 lines)
├── state.js              # State management (~100 lines)
├── dom.js                # DOM caching (~90 lines)
├── api.js                # API calls & data loading (~200 lines)
├── renderers.js          # Entry card rendering (~200 lines)
├── actions.js            # Entry actions (convert, edit, status) (~220 lines)
├── modal.js              # Modal open/close/reset (~150 lines)
├── form-handler.js       # Form submission logic (~200 lines)
├── search.js             # Room & customer search (~250 lines)
└── utils.js              # Utilities & formatters (~100 lines)
```

**Files:**
- Create: `static/js/waitlist/` directory
- Create: All module files listed above
- Modify: `templates/beach/map.html` - Update script includes
- Delete: `static/js/WaitlistManager.js` (after verification)

### Step 1: Create directory structure

```bash
mkdir -p static/js/waitlist
```

### Step 2: Create utils.js (no dependencies)

**File:** `static/js/waitlist/utils.js` (~100 lines)

```javascript
/**
 * Waitlist Utilities
 * Date formatting, HTML escaping, status labels
 */

export function getTodayDate() {
    return new Date().toISOString().split('T')[0];
}

export function formatDateDisplay(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr + 'T12:00:00');
        return date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
    } catch (e) {
        return dateStr;
    }
}

export function formatDateShort(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        return `${day}/${month}`;
    } catch (e) {
        return dateStr;
    }
}

export function formatTimeAgo(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Ahora';
        if (diffMins < 60) return `hace ${diffMins} min`;
        if (diffHours < 24) return `hace ${diffHours}h`;
        if (diffDays === 1) return 'Ayer';
        return `hace ${diffDays} dias`;
    } catch (e) {
        return '';
    }
}

export function getStatusLabel(status) {
    const labels = {
        'waiting': 'En espera',
        'contacted': 'Contactado',
        'converted': 'Convertido',
        'declined': 'Rechazado',
        'no_answer': 'Sin respuesta',
        'expired': 'Expirado'
    };
    return labels[status] || status;
}

export function getTimePreferenceLabel(pref) {
    const labels = {
        'morning': 'Manana',
        'manana': 'Manana',
        'afternoon': 'Tarde',
        'tarde': 'Tarde',
        'mediodia': 'Mediodia',
        'all_day': 'Todo el dia',
        'todo_el_dia': 'Todo el dia'
    };
    return labels[pref] || pref;
}

export function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export function showToast(message, type = 'info') {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}
```

### Step 3: Create state.js

**File:** `static/js/waitlist/state.js` (~100 lines)

```javascript
/**
 * Waitlist State Management
 */

export function createInitialState(options = {}) {
    return {
        isOpen: false,
        currentDate: options.currentDate || getTodayDate(),
        currentTab: 'pending',
        entries: [],
        historyEntries: [],
        isLoading: false,
        selectedCustomerId: null,
        selectedHotelGuestId: null,
        customerType: 'interno',
        zones: [],
        furnitureTypes: [],
        packages: [],
        editingEntryId: null
    };
}

function getTodayDate() {
    return new Date().toISOString().split('T')[0];
}

export function createCallbacks(options = {}) {
    return {
        onConvert: options.onConvert || null,
        onCountUpdate: options.onCountUpdate || null
    };
}
```

### Step 4: Create dom.js

**File:** `static/js/waitlist/dom.js` (~90 lines)

Extract `_cacheElements()` method into standalone function that returns DOM element references object.

### Step 5: Create api.js

**File:** `static/js/waitlist/api.js` (~200 lines)

Extract:
- `_loadPendingEntries()`
- `_loadHistoryEntries()`
- `_loadDropdownOptions()`
- `_loadPackages()`
- API helper function for fetch with CSRF

### Step 6: Create renderers.js

**File:** `static/js/waitlist/renderers.js` (~200 lines)

Extract:
- `_renderPendingEntries()`
- `_renderHistoryEntries()`
- `_renderEntryCard()`
- `_populateZonesDropdown()`
- `_populateFurnitureTypesDropdown()`

### Step 7: Create actions.js

**File:** `static/js/waitlist/actions.js` (~220 lines)

Extract:
- `_handleEntryAction()`
- `_handleConvert()`
- `_handleEdit()`
- `markAsConverted()`
- `_attachEntryListeners()`

### Step 8: Create modal.js

**File:** `static/js/waitlist/modal.js` (~150 lines)

Extract:
- `_openAddModal()`
- `_closeAddModal()`
- `_resetForm()`
- `_setCustomerType()`
- `_onReservationTypeChange()`

### Step 9: Create search.js

**File:** `static/js/waitlist/search.js` (~250 lines)

Extract:
- `_onRoomSearch()`, `_searchRooms()`, `_renderRoomResults()`, `_selectGuest()`, `_clearSelectedGuest()`
- `_onCustomerSearch()`, `_searchCustomers()`, `_renderCustomerResults()`, `_selectCustomer()`, `_clearSelectedCustomer()`
- `_showCreateCustomer()`

### Step 10: Create form-handler.js

**File:** `static/js/waitlist/form-handler.js` (~200 lines)

Extract:
- `_submitEntry()` (the main form submission logic)
- Form validation helpers

### Step 11: Create index.js (main coordinator)

**File:** `static/js/waitlist/index.js` (~80 lines)

```javascript
/**
 * WaitlistManager - Main Entry Point
 * Coordinates all modules into the WaitlistManager class
 */

import { createInitialState, createCallbacks } from './state.js';
import { cacheElements } from './dom.js';
import { attachListeners } from './listeners.js';
import * as api from './api.js';
import * as renderers from './renderers.js';
import * as actions from './actions.js';
import * as modal from './modal.js';
import * as search from './search.js';
import * as formHandler from './form-handler.js';
import * as utils from './utils.js';

class WaitlistManager {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: '/beach/api',
            debounceMs: 300,
            ...options
        };

        this.state = createInitialState(options);
        this.callbacks = createCallbacks(options);
        this.csrfToken = document.getElementById('waitlistCsrfToken')?.value ||
                         document.querySelector('meta[name="csrf-token"]')?.content || '';
        this.searchTimeout = null;

        // Cache DOM & attach listeners
        this.elements = cacheElements();
        if (this.elements.panel) {
            attachListeners(this);
        }
    }

    // Public API
    setDate(date) { /* delegate */ }
    async open() { /* delegate */ }
    close() { /* delegate */ }
    async refresh() { /* delegate */ }
    getCount() { return this.state.entries.filter(e => e.status === 'waiting').length; }
    isOpen() { return this.state.isOpen; }
    async markAsConverted(entryId, reservationId) { /* delegate */ }
}

// Expose globally
window.WaitlistManager = WaitlistManager;
export { WaitlistManager };
```

### Step 12: Update templates

**map.html** - Replace single script with module:
```html
<!-- OLD -->
<script src="{{ url_for('static', filename='js/WaitlistManager.js') }}"></script>

<!-- NEW -->
<script type="module" src="{{ url_for('static', filename='js/waitlist/index.js') }}"></script>
```

### Step 13: Test waitlist functionality

- [ ] Open waitlist panel from map
- [ ] Add new entry (interno)
- [ ] Add new entry (externo)
- [ ] Edit existing entry
- [ ] Change status
- [ ] Convert to reservation
- [ ] View history tab

### Step 14: Delete old monolithic file

```bash
rm static/js/WaitlistManager.js
```

### Step 15: Commit

```bash
git add -A
git commit -m "refactor: split WaitlistManager.js into modular structure"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `map-editor.js` deleted, map editor works
- [ ] `reservation-panel.js` deleted, reservation panel works
- [ ] `WaitlistManager.js` deleted, waitlist works
- [ ] All new modules under 500 lines
- [ ] No JavaScript files over 800 lines
- [ ] All tests pass

---

## Estimated Module Sizes

### Task 1: map-editor (already done)
| Module | Lines |
|--------|-------|
| canvas.js | 328 |
| operations.js | 338 |
| editor-core.js | 273 |
| viewport.js | 264 |
| furniture-renderer.js | 234 |
| selection.js | 195 |
| marquee.js | 193 |
| persistence.js | 182 |
| drag-drop.js | 81 |
| index.js | 45 |

### Task 2: reservation-panel (existing split)
| Module | Lines |
|--------|-------|
| panel-core.js | 704 (warning) |
| customer-handler.js | 692 (warning) |
| pricing-calculator.js | 388 |
| safeguard-checks.js | 329 |
| date-availability.js | 249 |
| conflict-resolver.js | 240 |

### Task 3: waitlist (planned)
| Module | Lines (target) |
|--------|-------|
| search.js | ~250 |
| actions.js | ~220 |
| api.js | ~200 |
| renderers.js | ~200 |
| form-handler.js | ~200 |
| modal.js | ~150 |
| state.js | ~100 |
| utils.js | ~100 |
| dom.js | ~90 |
| index.js | ~80 |
