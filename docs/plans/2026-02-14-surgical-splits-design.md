# Surgical Splits: Codebase Refactoring Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split monolithic files and consolidate V1/V2 panels to create a maintainable, scalable foundation before production launch (March 2026).

**Architecture:** Approach A — targeted splits of the 4 critical JS monoliths, light-touch Python model splits, and V1→V2 panel consolidation. No build tool changes. Same concatenation-based bundling.

**Tech Stack:** JavaScript ES6 (non-module, bundled via cat/sed), Python 3.11+/Flask, SQLite

---

## Context

### Current State (Feb 14, 2026)

**Codebase:** 39,694 Python lines + 25,961 JS lines across ~160 files

**JS Monoliths (Critical, >800 lines):**

| File | Lines | Problem |
|------|-------|---------|
| `map-page.js` | 2,368 | 23+ feature areas in one procedural script |
| `BeachMap.js` | 1,053 | Orchestrator class (acceptable — no split) |
| `MoveModePanel.js` | 961 | Mixes rendering, filtering, state management |
| `panel-core.js` (V1) | 872 | Entire V1 panel — eliminated by consolidation |

**Python Warning Zone (600-800 lines):**

| File | Lines | Action |
|------|-------|--------|
| `reservation_multiday.py` | 665 | Split by lifecycle phase |
| `reservation_crud.py` | 637 | Extract ticket generation |
| `reservations.py` (route) | 678 | Leave as-is (thin wrappers) |
| `customers.py` (route) | 630 | Leave as-is (thin wrappers) |
| Others (600-603) | ~600 | Leave as-is (well-organized internally) |

**V1/V2 Dual Panel System:**
- V1 (NewReservationPanel): 6 files, ~2,800 lines — creation only
- V2 (ReservationPanel): 13 files, ~4,145 lines — view/edit only
- Both active, loaded in same bundle, duplicate patterns

### CLAUDE.md File Size Limits
- **Target:** 300-500 lines per module
- **Warning:** >600 lines
- **Critical:** >800 lines — must refactor

---

## Phase 1: map-page.js Split

### Current Structure

Single `DOMContentLoaded` handler with 23+ feature areas, 11 state variables, and tight coupling through closure scope.

### Target Structure

8 focused modules sharing context via a `MapPageContext` object:

```javascript
// MapPageContext — passed to each module's init function
const ctx = {
    map,              // BeachMap instance
    csrfToken,        // CSRF token
    currentDate,      // Current selected date
    currentZoneId,    // Current zone filter
    // Manager references (populated during init)
    moveMode: null,
    moveModePanel: null,
    blockManager: null,
    searchManager: null,
    reservationPanel: null,
    newReservationPanel: null,
    waitlistManager: null
};
```

### Module Breakdown

| Module | ~Lines | Source Lines | Responsibility |
|--------|--------|-------------|----------------|
| `map-init.js` | 80 | 14-25, 2358-2365 | BeachMap instantiation, `window.beachMap`, zone re-apply on render |
| `map-managers.js` | 180 | 27-98, 295-371 | BlockManager, TempFurnitureManager, WaitlistManager setup + event wiring |
| `map-move-mode.js` | 200 | 100-294 | MoveMode + MoveModePanel init, global badge, onboarding, `window.moveMode` |
| `map-search.js` | 120 | 373-480 | SearchManager init, filter dropdowns, Ctrl+F shortcut |
| `map-panels.js` | 200 | 483-616 | ReservationPanel + NewReservationPanel init, addMoreFurniture mode |
| `map-conflicts.js` | 400 | 618-1169 | Conflict resolution + quick swap (tightly coupled, kept together) |
| `map-navigation.js` | 350 | 1247-1404, 1444-1594, 1596-1736 | Date nav, zone selector, zoom/pan, save/restore view, canvas info |
| `map-interaction.js` | 350 | 1738-2356 | Keyboard shortcuts, selection bar, furniture click handler, context menu, touch/pinch |

### Bundling

These 8 files replace the current `map-page.js`:

```bash
# Build map-page from modules (same sed/cat approach)
for file in map-init.js map-managers.js map-move-mode.js map-search.js \
            map-panels.js map-conflicts.js map-navigation.js map-interaction.js; do
    sed -E '/^import /d; s/^export //' "map-page/$file" >> map-page-bundle.js
done
```

In `map.html`, replace:
```html
<!-- Before -->
<script src="/static/js/map/map-page.js"></script>

<!-- After -->
<script src="/static/js/map-page-bundle.js"></script>
```

### Shared State

All modules share the `ctx` object. Module init order matters:

1. `map-init.js` — creates `ctx.map`
2. `map-managers.js` — creates `ctx.blockManager`, `ctx.waitlistManager`
3. `map-move-mode.js` — creates `ctx.moveMode`, `ctx.moveModePanel`
4. `map-search.js` — creates `ctx.searchManager`
5. `map-panels.js` — creates `ctx.reservationPanel`, `ctx.newReservationPanel`
6. `map-conflicts.js` — uses `ctx.map`, `ctx.moveMode`, `ctx.newReservationPanel`
7. `map-navigation.js` — uses `ctx.map`
8. `map-interaction.js` — uses everything

---

## Phase 2: MoveModePanel Split

### Current: 961 lines in one file

### Target: 3 files

| Module | ~Lines | Responsibility |
|--------|--------|----------------|
| `MoveModePanel.js` | 400 | Core class: open/close, pool state, API calls, event handling |
| `MoveModePanelRenderer.js` | 350 | `renderPoolItem()`, `renderPoolList()`, badge HTML, capacity display |
| `MoveModePanelFilters.js` | 200 | Filter state, `applyFilters()`, type/VIP/preference filter UI, search input |

### Integration

Renderer and Filters are composed into the main class:

```javascript
class MoveModePanel {
    constructor(containerId, moveMode) {
        this.renderer = new MoveModePanelRenderer(this);
        this.filters = new MoveModePanelFilters(this);
    }
}
```

Update `map-core-bundle.js` to include the 3 files instead of 1.

---

## Phase 3: Python Model Splits

### reservation_multiday.py (665 → 4 files)

| Module | ~Lines | Functions |
|--------|--------|-----------|
| `reservation_multiday.py` | 50 | Re-exports for backward compatibility |
| `reservation_multiday_create.py` | 320 | `create_linked_multiday_reservations()` |
| `reservation_multiday_manage.py` | 200 | `update_multiday_reservations()`, `cancel_multiday_reservations()` |
| `reservation_multiday_queries.py` | 100 | `get_multiday_summary()`, `is_parent_reservation()`, `get_child_reservations()` |

Re-export pattern:
```python
# reservation_multiday.py (backward compatible)
from .reservation_multiday_create import create_linked_multiday_reservations
from .reservation_multiday_manage import update_multiday_reservations, cancel_multiday_reservations
from .reservation_multiday_queries import get_multiday_summary, is_parent_reservation, get_child_reservations
```

### reservation_crud.py (637 → 2 files)

| Module | ~Lines | Functions |
|--------|--------|-----------|
| `reservation_crud.py` | 560 | All CRUD + furniture assignment (minus ticket gen) |
| `reservation_ticket.py` | 80 | `generate_reservation_number()`, `generate_child_reservation_number()` |

Add import in `reservation_crud.py`:
```python
from .reservation_ticket import generate_reservation_number, generate_child_reservation_number
```

### Verification

After each split, run:
```bash
python -m pytest tests/ -x -q
```

---

## Phase 4: V1 → V2 Panel Consolidation

### Strategy

Extend V2's mixin architecture with creation-specific mixins. Keep two separate UIs (creation panel and edit panel) but share the underlying code. V2 gets a `mode` property: `'view'`, `'edit'`, or `'create'`.

### New Mixins

#### 1. creation-mode-mixin.js (~150 lines)

Core creation mode support:

```javascript
const CreationModeMixin = (Base) => class extends Base {
    openForCreation(furnitureIds, date, waitlistEntry = null) { }
    initCreationState(furnitureIds, date) { }
    resetCreationForm() { }
    isCreationMode() { return this.state.mode === 'create'; }
};
```

- Initializes empty state (no reservation ID, no API load)
- Shows creation-specific DOM sections, hides view/edit sections
- Stores selected furniture IDs and date from map
- Handles waitlist pre-fill if converting from waitlist

#### 2. creation-customer-mixin.js (~350 lines)

Customer selection and inline creation for new reservations:

```javascript
const CreationCustomerMixin = (Base) => class extends Base {
    initCreationCustomerSearch() { }
    showCreateCustomerForm() { }
    saveNewCustomer() { }
    handleHotelGuestSelect(guestId) { }
    convertGuestToCustomer(guestId) { }
    fetchRoomGuests(roomNumber) { }
    populateFromCustomer(customer) { }
};
```

- Integrates external `CustomerSearch` component
- Inline form: first/last name, email, phone, language, customer type
- Hotel guest lookup by room number
- Auto-populates num_people from guest count
- Sets customer on panel state for pricing/preferences

#### 3. creation-safeguards-mixin.js (~300 lines)

Pre-creation validation (7 safeguard checks):

```javascript
const CreationSafeguardsMixin = (Base) => class extends Base {
    async runSafeguardChecks() { }  // Orchestrator — runs all checks in order
    checkPastDates() { }            // SG-05: No past dates
    checkHotelStayDates() { }       // SG-03: Dates within hotel stay
    checkCapacityMismatch() { }     // SG-04: People vs furniture capacity
    checkFurnitureAvailability() { } // SG-02: Furniture not already booked
    checkDuplicateReservation() { }  // SG-01: Same customer+date exists
    checkFurnitureContiguity() { }   // SG-07: No gaps between furniture
};
```

- Each check returns `{ pass: bool, warning: string, canProceed: bool }`
- Uses SafeguardModal for user confirmations (existing component)
- Short-circuits on blocking errors (SG-05)

#### 4. creation-conflict-mixin.js (~200 lines)

Multi-day conflict resolution during creation:

```javascript
const CreationConflictMixin = (Base) => class extends Base {
    handleConflictResponse(conflicts) { }
    showConflictModal(conflicts) { }
    navigateToConflictDay(date) { }
    retryWithPerDayFurniture(furnitureByDate) { }
    persistCustomerDuringConflict() { }
};
```

- Shows ConflictResolutionModal (existing component)
- Minimizes panel, allows map interaction for alternative selection
- Preserves customer data during the conflict flow
- Retries creation with per-day furniture selections

#### 5. creation-save-mixin.js (~200 lines)

Creation submission:

```javascript
const CreationSaveMixin = (Base) => class extends Base {
    async createReservation() { }
    buildCreationPayload() { }
    async markWaitlistAsConverted(waitlistId) { }
    handleCreationSuccess(result) { }
    handleCreationError(error) { }
};
```

- Runs safeguard checks first
- Builds payload: customer_id, furniture_ids, dates, num_people, time_slot, notes, preferences, tag_ids, package_id, price_override, payment details
- POST to `/beach/api/map/quick-reservation`
- Handles conflict response (delegates to conflict mixin)
- Waitlist conversion on success

### Extended Existing Mixins

**pricing-mixin.js** — Add ~100 lines:
```javascript
// New methods for creation context
initCreationPricing() { }       // Fetch packages for new reservation params
onCreationParamsChange() { }    // Recalculate when customer/date/furniture changes
```

**furniture-mixin.js** — Add ~80 lines:
```javascript
// New methods for creation context
renderCreationFurniture(furnitureIds) { }  // Show selected furniture from map
calculateCreationCapacity() { }            // Total capacity for selected furniture
showCapacityWarning(needed, available) { }  // Warning + "Add More" button
```

### Updated Mixin Composition

```javascript
// index.js — updated composition order
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
                                                        ))))))))))))));
```

### HTML Template Changes

Add creation-specific sections to `_reservation_panel.html`:

```html
<!-- Creation-only sections (hidden by default, shown when mode === 'create') -->
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

<!-- Existing sections work for both edit and create modes -->
<!-- Tags, preferences, pricing, notes — shared -->
```

### Migration Steps

1. Build all 5 creation mixins (V1 and V2 both active)
2. Add creation HTML sections to template
3. Update `index.js` composition
4. Update `map-panels.js` (from Phase 1) to use V2 for creation:
   ```javascript
   // Replace: new NewReservationPanel(...)
   // With: ctx.reservationPanel.openForCreation(furnitureIds, date)
   ```
5. Test creation flow end-to-end
6. Remove V1 files (`reservation-panel/` directory — 6 files)
7. Remove V1 from `map-panels-bundle.js`

### Net Effect

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| V1 panel code | 2,800 lines | 0 | -2,800 |
| V2 creation mixins | 0 | 1,380 lines | +1,380 |
| V2 mixin extensions | 0 | 180 lines | +180 |
| **Net lines** | | | **-1,240** |
| Panel architectures | 2 (V1 + V2) | 1 (V2 only) | Unified |
| Bundle files affected | map-panels-bundle.js | map-panels-bundle.js | Same file, smaller |

---

## What We Don't Touch

| File | Lines | Reason |
|------|-------|--------|
| `BeachMap.js` | 1,053 | Well-structured orchestrator class, sub-modules already extracted |
| API route files (678, 630) | 1,308 | Thin wrappers, size comes from endpoint count not complexity |
| `reservation_queries.py` | 604 | Well-organized, close to target |
| `reservation_state.py` | 600 | Well-organized, close to target |
| `furniture.py` | 603 | Well-organized, close to target |
| `demo_seed.py` | 995 | Non-production script |
| `test_insights.py` | 921 | Test file |
| `simulate_month.py` | 824 | Non-production script |

---

## Execution Order

| Phase | What | Effort | Risk | Impact |
|-------|------|--------|------|--------|
| 1 | map-page.js → 8 modules | 1-2 days | Low | High — largest monolith eliminated |
| 2 | MoveModePanel → 3 files | 0.5 day | Low | Medium — cleaner separation |
| 3 | Python model splits | 0.5 day | Low | Medium — maintainability |
| 4 | V1→V2 consolidation | 2-3 days | Medium | High — 1,240 lines removed, unified architecture |

**Total estimated effort: 4-5 days**

---

## Success Criteria

- [ ] No JS file exceeds 500 lines (except BeachMap.js — acceptable at 1,053)
- [ ] No Python production file exceeds 600 lines
- [ ] All existing functionality works identically (no behavior changes)
- [ ] V1 panel directory completely removed
- [ ] Single panel architecture for both create and edit
- [ ] All bundles rebuilt and verified
- [ ] `pytest` passes after Python splits
- [ ] Map page loads and works after JS splits

---

## Future Considerations (Post-Launch)

- **Build tool migration:** Introduce esbuild/Vite when there's breathing room. Files will already be well-organized modules, making migration straightforward.
- **BeachMap.js:** If it grows past 1,200 lines, extract rendering logic into a separate `BeachMapRenderer` class.
- **Further Python splits:** If any model file crosses 700 lines due to new features, follow the established re-export pattern.
