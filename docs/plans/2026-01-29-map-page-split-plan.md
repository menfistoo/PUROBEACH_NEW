# map-page.js Split — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split `static/js/map/map-page.js` from 2,343 lines to ~1,150 by extracting 6 self-contained ES6 modules.

**Architecture:** Pure extraction — move code blocks into ES6 modules that export setup functions. Each module receives a `deps` object with its dependencies. No behavior changes. Each setup function returns an API object for cross-module calls.

**Branch:** `refactor/split-map-page` (worktree at `.worktrees/split-map-page`)

---

## Shared Pattern

Every extracted module follows this pattern:

```javascript
// static/js/map/page-<feature>.js
/**
 * <Feature> - Extracted from map-page.js
 * <Brief description>
 */

export function setup<Feature>(deps) {
    const { map, ... } = deps;

    // Extracted code, unchanged

    // Return API for cross-module calls (if needed)
    return { functionA, functionB };
}
```

In `map-page.js`, replace inline block with:

```javascript
import { setup<Feature> } from './page-<feature>.js';
const <feature>Api = setup<Feature>({ map, ... });
```

---

## Task 1: Extract `page-context-menu.js` (~160 lines)

**Why first:** Self-contained, no return API needed by other modules. Clean boundary.

**Create:** `static/js/map/page-context-menu.js`

**Extract lines:** 2165-2331 from map-page.js

**Content to extract:**
- Context menu DOM element references (contextMenu, contextMenuHeader, contextMenuAvailable, contextMenuOccupied, contextFurnitureId, contextReservationId)
- Click/contextmenu dismiss listeners (lines 2175-2180)
- `showContextMenu()` function (lines 2182-2224)
- `#map-container` contextmenu listener (lines 2226-2232)
- Context menu action handler with all cases: view-details, select, new-reservation, view-reservation, edit-reservation, cancel-reservation, block (lines 2234-2322)
- Escape key handler for context menu (lines 2324-2331) — merge into the main keyboard handler instead

**Dependencies (deps object):**
```javascript
{
    map,              // getCurrentDate, refreshAvailability, clearSelection, selectFurniture
    openReservationPanel,  // function(id, mode)
    updateSelectionBar,    // function()
    updateStats,           // function(zoneId)
    getCurrentZoneId,      // () => currentZoneId
    formatDateCompact      // function(dateStr)
}
```

**Setup function signature:**
```javascript
export function setupContextMenu(deps) { ... }
// No return value needed
```

**In map-page.js, replace with:**
```javascript
import { setupContextMenu } from './page-context-menu.js';
// ... (after openReservationPanel, updateSelectionBar, updateStats, formatDateCompact are defined)
setupContextMenu({
    map,
    openReservationPanel,
    updateSelectionBar,
    updateStats,
    getCurrentZoneId: () => currentZoneId,
    formatDateCompact
});
```

**Also:** Remove lines 2324-2331 (duplicate Escape handler) — it's already handled in keyboard shortcuts section at line 1737.

**Verify:** Right-click on furniture → context menu appears. Click actions work (select, new reservation, view reservation, block). Clicking away dismisses menu.

---

## Task 2: Extract `page-touch-handlers.js` (~90 lines)

**Create:** `static/js/map/page-touch-handlers.js`

**Extract lines:** 1162-1236 (touch long-press) + 1852-1867 (pinch zoom)

**Content to extract:**
- Touch handler initialization with `TouchHandler` (lines 1165-1171)
- Long-press handler for move mode (release furniture) and normal mode (context menu) (lines 1173-1236)
- Pinch zoom setup with `PinchZoomHandler` (lines 1852-1867)

**Dependencies (deps object):**
```javascript
{
    map,              // getData, handleFurnitureContextMenu, getZoom, setZoom, refreshAvailability
    moveMode,         // isActive, unassignFurniture
    updateZoomDisplay, // function()
    PinchZoomHandler  // constructor (imported in map-page.js)
}
```

**Setup function signature:**
```javascript
export function setupTouchHandlers(deps) { ... }
// No return value needed
```

**In map-page.js, replace with:**
```javascript
import { setupTouchHandlers } from './page-touch-handlers.js';
// ... (after moveMode and updateZoomDisplay are defined)
setupTouchHandlers({ map, moveMode, updateZoomDisplay, PinchZoomHandler });
```

**Note:** Move the `PinchZoomHandler` import from map-page.js to page-touch-handlers.js since it's only used there.

**Verify:** On touch device (or Chrome DevTools mobile simulation): long-press on occupied furniture in move mode releases it. Long-press outside move mode shows context menu. Pinch zoom works.

---

## Task 3: Extract `page-pan-zoom.js` (~210 lines)

**Create:** `static/js/map/page-pan-zoom.js`

**Extract lines:** 1500-1510 (zoom controls) + 1512-1585 (save/restore view) + 1587-1727 (Shift+Wheel zoom, Space+Drag pan)

**Content to extract:**
- Zoom control button bindings (lines 1500-1510)
- Save/restore view: VIEW_STORAGE_KEY, savedView, loadSavedView, saveCurrentView, resetToSavedView (lines 1512-1585)
- Shift+Wheel zoom handler with mouse-position-aware zooming (lines 1587-1677)
- Space key tracking for pan mode (lines 1679-1695)
- Space+Drag and middle-mouse-button pan (lines 1697-1727)

**Dependencies (deps object):**
```javascript
{
    map,              // zoomIn, zoomOut, getZoom, setZoom
    updateZoomDisplay, // function() - defined in canvas info bar section
    getCurrentZoneId,  // () => currentZoneId
    zoneSelect,        // DOM element (for restoring zone in resetToSavedView)
    applyZoneView      // function(zoneId) - from date-navigation or inline
}
```

**Setup function signature:**
```javascript
export function setupPanZoom(deps) {
    // ...
    return { saveCurrentView, resetToSavedView };
}
```

**Returns:** `{ saveCurrentView, resetToSavedView }` — needed by keyboard shortcuts (Ctrl+S, Ctrl+0).

**In map-page.js, replace with:**
```javascript
import { setupPanZoom } from './page-pan-zoom.js';
// ... (after updateZoomDisplay, applyZoneView are defined)
const panZoomApi = setupPanZoom({
    map,
    updateZoomDisplay,
    getCurrentZoneId: () => currentZoneId,
    zoneSelect,
    applyZoneView
});
```

**Verify:** Shift+scroll wheel zooms map centered on cursor. Space+drag pans. Middle mouse button pans. Zoom buttons (+/-) work. Save/reset view buttons in info bar work.

---

## Task 4: Extract `page-keyboard-shortcuts.js` (~110 lines)

**Create:** `static/js/map/page-keyboard-shortcuts.js`

**Extract lines:** 1729-1837 (keyboard shortcuts + selectAllVisibleFurniture)

**Content to extract:**
- Main keydown handler with cases: Escape, Ctrl+A, Ctrl+/-, Ctrl+0, ArrowLeft/Right, R, Ctrl+S (lines 1732-1818)
- `selectAllVisibleFurniture()` function (lines 1821-1837)

**Dependencies (deps object):**
```javascript
{
    map,                  // clearSelection, getSelectedFurniture, getData, selectFurniture, zoomIn, zoomOut, goToPreviousDay, goToNextDay
    newReservationPanel,  // isOpen, close
    updateSelectionBar,   // function()
    updateZoomDisplay,    // function()
    saveCurrentView,      // function() - from panZoomApi
    resetToSavedView,     // function() - from panZoomApi
    getCurrentZoneId,     // () => currentZoneId
    btnRefresh            // DOM element
}
```

**Setup function signature:**
```javascript
export function setupKeyboardShortcuts(deps) { ... }
// No return value needed
```

**In map-page.js, replace with:**
```javascript
import { setupKeyboardShortcuts } from './page-keyboard-shortcuts.js';
// ... (after panZoomApi is created)
setupKeyboardShortcuts({
    map,
    newReservationPanel,
    updateSelectionBar,
    updateZoomDisplay,
    saveCurrentView: panZoomApi.saveCurrentView,
    resetToSavedView: panZoomApi.resetToSavedView,
    getCurrentZoneId: () => currentZoneId,
    btnRefresh
});
```

**Verify:** Escape closes panel or deselects. Ctrl+A selects all visible. Ctrl+/- zooms. ArrowLeft/Right navigates days. R refreshes. Ctrl+S saves view.

---

## Task 5: Extract `page-conflict-resolution.js` (~470 lines)

**Why last among extractions:** Largest module, most cross-references. Other modules being extracted first reduces the remaining complexity.

**Create:** `static/js/map/page-conflict-resolution.js`

**Extract lines:** 609-999 (conflict resolution) + 1001-1161 (quick swap)

**Content to extract:**

**Conflict Resolution (609-999):**
- `conflictResolutionContext` variable
- `conflictResolution:selectAlternative` event listener
- `highlightConflictingFurniture()`, `clearConflictHighlights()`
- `showConflictInstructions()`, `hideConflictInstructions()`
- `updateConflictSelectionCounter()`
- `updateSelectionBarForConflict()`
- `exitConflictResolutionMode()`
- `confirmAlternativeSelection()`

**Quick Swap (1001-1161):**
- `quickSwapContext` variable
- DOM references: quickSwapModal, quickSwapCancelBtn, quickSwapStartBtn, quickSwapBackdrop
- `showQuickSwapModal()`, `hideQuickSwapModal()`
- `enterSwapDestinationMode()`, `clearSwapSourceHighlight()`
- `performQuickSwap()`
- Button event bindings

**Dependencies (deps object):**
```javascript
{
    map,              // clearSelection, getSelectedFurniture, getSelectedFurnitureData, selectFurniture, deselectFurniture, goToDate, getCurrentDate, getData, refreshAvailability
    updateSelectionBar // function()
}
```

**Setup function signature:**
```javascript
export function setupConflictResolution(deps) {
    // ...
    return {
        getContext,                    // () => conflictResolutionContext
        updateConflictSelectionCounter, // function()
        showQuickSwapModal,            // function(furnitureId, reservationId, customerName, label)
        isQuickSwapSelectingDestination, // () => boolean
        performQuickSwap,              // async function(toFurnitureId)
        getQuickSwapContext            // () => quickSwapContext
    };
}
```

**Returns:** API object needed by `onFurnitureClick` handler (lines 2074-2119) and `updateSelectionBar` (line 1940-1942).

**In map-page.js, replace with:**
```javascript
import { setupConflictResolution } from './page-conflict-resolution.js';
// ... (after map and updateSelectionBar are defined)
const conflictApi = setupConflictResolution({ map, updateSelectionBar });
```

**Update onFurnitureClick handler (stays in map-page.js) to use conflictApi:**
- Replace `conflictResolutionContext` → `conflictApi.getContext()`
- Replace `quickSwapContext && quickSwapModal.classList.contains('selecting-destination')` → `conflictApi.isQuickSwapSelectingDestination()`
- Replace `updateConflictSelectionCounter()` → `conflictApi.updateConflictSelectionCounter()`
- Replace `showQuickSwapModal(...)` → `conflictApi.showQuickSwapModal(...)`
- Replace `performQuickSwap(...)` → `conflictApi.performQuickSwap(...)`

**Update updateSelectionBar (stays in map-page.js):**
- Replace `if (conflictResolutionContext)` → `if (conflictApi.getContext())`
- The call to `updateSelectionBarForConflict()` is handled internally by the conflict module

**Verify:** Create multi-day reservation with conflict → conflict modal shows → select alternative → confirm works. Quick swap: click conflicting furniture → swap modal → select destination → swap executes. Cancel returns to conflict modal.

---

## Task 6: Update `map-page.js` imports and cleanup

**Modify:** `static/js/map/map-page.js`

After all 5 modules are extracted and imported, clean up:

1. Add all new imports at the top (after existing imports)
2. Ensure setup calls are in correct order (dependencies satisfied):
   - `setupContextMenu` — after `openReservationPanel`, `updateSelectionBar`, `updateStats`, `formatDateCompact`
   - `setupTouchHandlers` — after `moveMode`, `updateZoomDisplay`
   - `setupPanZoom` — after `updateZoomDisplay`, `applyZoneView`
   - `setupKeyboardShortcuts` — after `panZoomApi`
   - `setupConflictResolution` — after `map`, `updateSelectionBar`
3. Remove the `PinchZoomHandler` import from map-page.js (moved to page-touch-handlers.js)
4. Update `onFurnitureClick` handler to use `conflictApi`
5. Update `updateSelectionBar` to use `conflictApi.getContext()`
6. Remove duplicate Escape handler (lines 2324-2331)
7. Verify no dead code remains

**Expected final structure of map-page.js (~1,150 lines):**
```
Imports (6 existing + 5 new)              ~26
Map init                                   ~13
Block manager                              ~26
Temp furniture manager                     ~28
Move mode manager                         ~194
Waitlist manager                           ~72
Search manager                            ~105
Reservation panel                          ~32
New reservation panel                      ~34
Add more furniture mode                    ~62
Reservation highlight events               ~76
Date navigation + zone selector           ~158
Stats                                      ~38
Canvas info bar                            ~65
Refresh                                    ~12
Selection & bottom action bar             ~144
onFurnitureClick handler (updated)        ~121
Clear/block/new-reservation buttons        ~22
onRender zone view                          ~9
Setup calls for extracted modules          ~15
```

**Verify:** Run the map page (`python app.py`, navigate to `/beach/map`). Check:
- [ ] No console errors on page load
- [ ] Furniture selection works (click, Ctrl+A, clear)
- [ ] Date navigation (prev/next, picker, swipe, arrows)
- [ ] Zone selector switches zones
- [ ] Context menu (right-click) with all actions
- [ ] Keyboard shortcuts (Escape, Ctrl+/-, R, Ctrl+S)
- [ ] Pan (Space+drag, middle mouse) and zoom (Shift+wheel, buttons)
- [ ] Touch handlers (long-press on mobile simulation)
- [ ] Reservation panel opens on occupied furniture click
- [ ] New reservation panel opens on "Reservar" button
- [ ] Conflict resolution flow (if testable)
- [ ] Move mode toggle and functionality
- [ ] Search (Ctrl+F, type query)
- [ ] Stats update on zone/date change

---

## Task 7: Commit

```bash
git add static/js/map/page-context-menu.js static/js/map/page-touch-handlers.js static/js/map/page-pan-zoom.js static/js/map/page-keyboard-shortcuts.js static/js/map/page-conflict-resolution.js static/js/map/map-page.js
git commit -m "refactor(map): extract 5 modules from map-page.js (2343 → ~1150 lines)

Extract self-contained features into ES6 modules:
- page-context-menu.js: right-click menu setup and actions
- page-touch-handlers.js: long-press detection and pinch zoom
- page-pan-zoom.js: Shift+wheel zoom, Space+drag pan, save/restore view
- page-keyboard-shortcuts.js: keyboard shortcuts and select-all
- page-conflict-resolution.js: conflict resolution UI and quick swap

Each module exports a setup function receiving dependencies.
No behavior changes - pure extraction refactoring."
```
