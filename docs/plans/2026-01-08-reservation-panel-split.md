# ReservationPanel Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split the 2390-line `ReservationPanel` class into focused modules under 400 lines each

**Architecture:** Mixin composition pattern (same as map-editor split) - each module extends the base class with specific functionality

**Tech Stack:** ES6 JavaScript classes, mixin pattern, no build tools

---

## Current Structure Analysis

The `ReservationPanel` class (2390 lines) handles viewing/editing existing reservations. It has these logical sections:

| Section | Lines | Responsibility |
|---------|-------|---------------|
| Constructor & state | 1-82 | Initialization, state objects |
| DOM caching | 84-206 | `cacheElements()` - 120+ DOM refs |
| Event listeners | 208-321 | `attachListeners()`, pricing events, swipe |
| Panel lifecycle | 374-566 | open/close/collapse, map data |
| Edit mode | 568-700 | enter/exit edit, dirty state |
| Customer section | 761-840, 1891-2055 | Display, search, change |
| Preferences section | 857-1221 | View/edit preferences |
| Pricing section | 936-1153, 1432-1468 | Pricing edit mode, packages |
| State section | 1223-1365 | State chips, history |
| Furniture section | 1367-1404, 1573-1889 | View, reassignment mode |
| Details/Payment | 1406-1500 | Num people, notes, payment |
| Save handler | 2057-2232 | `saveChanges()` |
| Utilities | 2253-2391 | Formatters, helpers |

---

## Proposed Module Structure

```
static/js/map/reservation-panel-v2/
├── index.js                  # Main entry, mixin composition (~60 lines)
├── panel-base.js             # Base class, state, DOM cache (~250 lines)
├── panel-lifecycle.js        # Open/close/collapse (~200 lines)
├── edit-mode-mixin.js        # Edit mode toggle (~150 lines)
├── customer-mixin.js         # Customer section & search (~300 lines)
├── preferences-mixin.js      # Preferences view/edit (~200 lines)
├── state-mixin.js            # State chips & history (~250 lines)
├── furniture-mixin.js        # Furniture & reassignment (~350 lines)
├── pricing-mixin.js          # Pricing view/edit (~300 lines)
├── details-mixin.js          # Details & payment (~150 lines)
├── save-mixin.js             # Save changes logic (~200 lines)
└── utils.js                  # Utilities (~100 lines)
```

**Total: ~12 files, each under 350 lines**

---

## Task 1: Create Directory and Utils Module

**Files:**
- Create: `static/js/map/reservation-panel-v2/`
- Create: `static/js/map/reservation-panel-v2/utils.js`

**Step 1: Create directory**

```bash
mkdir -p static/js/map/reservation-panel-v2
```

**Step 2: Create utils.js (~100 lines)**

```javascript
/**
 * ReservationPanel Utilities
 * Date formatting, HTML helpers, toast notifications
 */

export function getInitials(firstName, lastName) {
    const first = (firstName || '')[0] || '';
    const last = (lastName || '')[0] || '';
    return (first + last).toUpperCase() || '?';
}

export function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        let date;
        if (dateStr.includes('T')) {
            date = new Date(dateStr);
        } else {
            date = new Date(dateStr + 'T00:00:00');
        }
        if (isNaN(date.getTime())) return dateStr;
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

export function parseDateToYMD(dateStr) {
    if (!dateStr) return '';
    try {
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
        const isoMatch = dateStr.match(/^(\d{4}-\d{2}-\d{2})T/);
        if (isoMatch) return isoMatch[1];
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return dateStr;
    } catch (e) {
        return dateStr;
    }
}

export function getFurnitureIcon(typeName) {
    const icons = {
        'hamaca': '🛏️',
        'balinesa': '🛖',
        'sombrilla': '☂️',
        'mesa': '🪑'
    };
    const lowerType = (typeName || '').toLowerCase();
    for (const [key, icon] of Object.entries(icons)) {
        if (lowerType.includes(key)) return icon;
    }
    return '🪑';
}

export function showToast(message, type = 'info') {
    if (window.PuroBeach?.showToast) {
        window.PuroBeach.showToast(message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}
```

**Step 3: Commit**

```bash
git add static/js/map/reservation-panel-v2/
git commit -m "refactor(reservation-panel): create utils module"
```

---

## Task 2: Create Base Class

**Files:**
- Create: `static/js/map/reservation-panel-v2/panel-base.js`

**Step 1: Create panel-base.js (~250 lines)**

Contains:
- Constructor with options, state initialization
- `cacheElements()` method (all DOM references)
- `attachListeners()` base setup
- `setupSwipeGestures()`
- `setMapData()`, `setStates()`, `fetchStates()`
- `isStandalone()`, `showLoading()`, `markDirty()`

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/panel-base.js
git commit -m "refactor(reservation-panel): create base class with DOM caching"
```

---

## Task 3: Create Panel Lifecycle Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/panel-lifecycle.js`

**Step 1: Create panel-lifecycle.js (~200 lines)**

Contains:
- `open(reservationId, date, mode)` - Opens panel, loads data
- `close()` - Closes panel with unsaved changes check
- `toggleCollapse()` - Collapse/expand panel
- `loadReservation(reservationId, date)` - API call to load data
- `renderContent(data)` - Orchestrates section rendering
- `showError(message)` - Error state display

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/panel-lifecycle.js
git commit -m "refactor(reservation-panel): create lifecycle mixin"
```

---

## Task 4: Create Edit Mode Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/edit-mode-mixin.js`

**Step 1: Create edit-mode-mixin.js (~150 lines)**

Contains:
- `toggleEditMode()` - Switch between view/edit
- `enterEditMode()` - Show edit UI, prefill fields
- `exitEditMode(discard)` - Return to view mode
- Event listener setup for edit inputs

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/edit-mode-mixin.js
git commit -m "refactor(reservation-panel): create edit mode mixin"
```

---

## Task 5: Create Customer Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/customer-mixin.js`

**Step 1: Create customer-mixin.js (~300 lines)**

Contains:
- `renderCustomerSection(customer)` - Display customer info
- `showCustomerSearch()`, `hideCustomerSearch()`
- `handleCustomerSearch(event)` - Debounced search
- `searchCustomers(query)` - API call
- `renderCustomerSearchResults(result)` - Render dropdown
- `selectCustomer(item)` - Handle selection

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/customer-mixin.js
git commit -m "refactor(reservation-panel): create customer mixin"
```

---

## Task 6: Create Preferences Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/preferences-mixin.js`

**Step 1: Create preferences-mixin.js (~200 lines)**

Contains:
- `renderPreferencesSection(customer)` - Display chips
- `enterPreferencesEditMode()`, `exitPreferencesEditMode()`
- `loadAllPreferences()` - API call
- `renderAllPreferencesChips()` - Toggleable chips
- `togglePreference(code)` - Toggle selection

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/preferences-mixin.js
git commit -m "refactor(reservation-panel): create preferences mixin"
```

---

## Task 7: Create State Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/state-mixin.js`

**Step 1: Create state-mixin.js (~250 lines)**

Contains:
- `renderStateSection(reservation)` - State chips
- `handleStateChange(event)` - Toggle state via API
- `loadStateHistory(reservationId)` - API call
- `renderStateHistory(history)` - History items
- `toggleStateHistory()` - Show/hide history

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/state-mixin.js
git commit -m "refactor(reservation-panel): create state mixin"
```

---

## Task 8: Create Furniture Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/furniture-mixin.js`

**Step 1: Create furniture-mixin.js (~350 lines)**

Contains:
- `renderFurnitureSection(reservation)` - Display chips
- `enterReassignmentMode()`, `exitReassignmentMode()`
- `toggleFurnitureSelection(furnitureId, data)` - Toggle selection
- `isInReassignmentMode()` - Check mode
- `updateReassignmentUI()` - Update counter/chips
- `renderOriginalFurnitureChips(furniture)`
- `saveReassignment()` - API call
- `highlightReservationFurniture()`, `unhighlightReservationFurniture()`

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/furniture-mixin.js
git commit -m "refactor(reservation-panel): create furniture mixin"
```

---

## Task 9: Create Pricing Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/pricing-mixin.js`

**Step 1: Create pricing-mixin.js (~300 lines)**

Contains:
- `setupPricingEventListeners()` - Input handlers
- `renderPricingSection(reservation)` - View mode
- `enterPricingEditMode()`, `exitPricingEditMode()`
- `fetchAvailablePackages()` - API call
- `updatePackageSelector()` - Populate dropdown
- `calculateAndUpdatePricing()` - API call

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/pricing-mixin.js
git commit -m "refactor(reservation-panel): create pricing mixin"
```

---

## Task 10: Create Details Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/details-mixin.js`

**Step 1: Create details-mixin.js (~150 lines)**

Contains:
- `renderDetailsSection(reservation)` - Num people, notes
- `renderPaymentSection(reservation)` - Payment ticket, method

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/details-mixin.js
git commit -m "refactor(reservation-panel): create details mixin"
```

---

## Task 11: Create Save Mixin

**Files:**
- Create: `static/js/map/reservation-panel-v2/save-mixin.js`

**Step 1: Create save-mixin.js (~200 lines)**

Contains:
- `saveChanges()` - Main save logic
- Collect changes from all sections
- API calls for reservation + preferences
- Error handling
- Success callbacks

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/save-mixin.js
git commit -m "refactor(reservation-panel): create save mixin"
```

---

## Task 12: Create Index with Mixin Composition

**Files:**
- Create: `static/js/map/reservation-panel-v2/index.js`

**Step 1: Create index.js (~60 lines)**

```javascript
/**
 * ReservationPanel - Main Entry Point
 * Composes all mixins into the final ReservationPanel class
 */

import { ReservationPanelBase } from './panel-base.js';
import { PanelLifecycleMixin } from './panel-lifecycle.js';
import { EditModeMixin } from './edit-mode-mixin.js';
import { CustomerMixin } from './customer-mixin.js';
import { PreferencesMixin } from './preferences-mixin.js';
import { StateMixin } from './state-mixin.js';
import { FurnitureMixin } from './furniture-mixin.js';
import { PricingMixin } from './pricing-mixin.js';
import { DetailsMixin } from './details-mixin.js';
import { SaveMixin } from './save-mixin.js';

/**
 * Compose all mixins into the final ReservationPanel class
 * Order matters: each mixin may depend on methods from previous mixins
 */
const ReservationPanel = SaveMixin(
    DetailsMixin(
        PricingMixin(
            FurnitureMixin(
                StateMixin(
                    PreferencesMixin(
                        CustomerMixin(
                            EditModeMixin(
                                PanelLifecycleMixin(
                                    ReservationPanelBase
                                )
                            )
                        )
                    )
                )
            )
        )
    )
);

// Export for ES modules
export { ReservationPanel };

// Also expose on window for legacy compatibility
window.ReservationPanel = ReservationPanel;
```

**Step 2: Commit**

```bash
git add static/js/map/reservation-panel-v2/index.js
git commit -m "refactor(reservation-panel): create index with mixin composition"
```

---

## Task 13: Update Templates

**Files:**
- Modify: `templates/beach/map.html`
- Modify: `templates/beach/reservation_unified.html`

**Step 1: Update map.html**

Replace:
```html
<script src="{{ url_for('static', filename='js/map/reservation-panel.js') }}"></script>
```

With:
```html
<script type="module" src="{{ url_for('static', filename='js/map/reservation-panel-v2/index.js') }}"></script>
```

**Step 2: Update reservation_unified.html**

Replace:
```html
<script src="{{ url_for('static', filename='js/map/reservation-panel.js') }}"></script>
```

With:
```html
<script type="module" src="{{ url_for('static', filename='js/map/reservation-panel-v2/index.js') }}"></script>
```

**Step 3: Commit**

```bash
git add templates/beach/map.html templates/beach/reservation_unified.html
git commit -m "refactor(reservation-panel): update templates to use modular version"
```

---

## Task 14: Test and Verify

**Verification checklist:**

On `/beach/map`:
- [ ] Click on occupied furniture → panel opens
- [ ] Customer section displays correctly (name, room, VIP badge)
- [ ] State chips show and can be clicked to change state
- [ ] Furniture section shows assigned items
- [ ] Pricing section shows total
- [ ] Click Edit button → enters edit mode
- [ ] Can edit num_people, notes
- [ ] Can search and change customer
- [ ] Can toggle preferences
- [ ] Can change furniture (reassignment mode)
- [ ] Save changes works
- [ ] Cancel discards changes
- [ ] Close panel works (with unsaved changes warning)

On `/beach/reservations/{id}` (standalone):
- [ ] Panel loads correctly
- [ ] All sections render
- [ ] Edit mode works
- [ ] Save works

**Step 1: Manual testing**

Test all scenarios above.

**Step 2: Run automated tests**

```bash
python -m pytest tests/ -v
```

---

## Task 15: Delete Old File

**Only after verification passes!**

**Files:**
- Delete: `static/js/map/reservation-panel.js`

**Step 1: Delete old file**

```bash
rm static/js/map/reservation-panel.js
```

**Step 2: Final commit**

```bash
git add -A
git commit -m "refactor(reservation-panel): remove old monolithic file (split complete)"
```

---

## Expected Line Counts

| Module | Target Lines |
|--------|-------------|
| index.js | ~60 |
| panel-base.js | ~250 |
| panel-lifecycle.js | ~200 |
| edit-mode-mixin.js | ~150 |
| customer-mixin.js | ~300 |
| preferences-mixin.js | ~200 |
| state-mixin.js | ~250 |
| furniture-mixin.js | ~350 |
| pricing-mixin.js | ~300 |
| details-mixin.js | ~150 |
| save-mixin.js | ~200 |
| utils.js | ~100 |
| **Total** | **~2510** |

All modules under 350 lines, well within the 500-line target.
