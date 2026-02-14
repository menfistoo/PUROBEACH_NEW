# Map Loading Performance V2 - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce map JS requests from ~44 to 5 by bundling ES6 modules into 3 concatenated files.

**Architecture:** Strip import/export from ES6 modules, concatenate in dependency order, expose classes via window globals. No build tooling.

**Tech Stack:** JavaScript ES6, Jinja2 templates, Bash for concatenation

---

## Task 1: Create map-core-bundle.js

**Files:**
- Create: `static/js/map-core-bundle.js`
- Source files (in order):
  1. `static/js/map/utils.js`
  2. `static/js/map/modal-state-manager.js`
  3. `static/js/map/tooltips.js`
  4. `static/js/map/selection.js`
  5. `static/js/map/navigation.js`
  6. `static/js/map/context-menu.js`
  7. `static/js/map/interaction.js`
  8. `static/js/map/renderer.js`
  9. `static/js/map/pinch-zoom.js`
  10. `static/js/map/BeachMap.js`
  11. `static/js/map/SearchManager.js`
  12. `static/js/map/block-manager.js`
  13. `static/js/map/temp-furniture-manager.js`
  14. `static/js/map/MoveMode.js`
  15. `static/js/map/MoveModePanel.js`

**Step 1: Read all source files and verify dependency order**

Read each file's imports to confirm the order above is correct. Verify no circular dependencies.

**Step 2: Create concatenation script**

Write a bash script that for each file:
1. Adds a section comment: `// --- filename.js ---`
2. Strips lines starting with `import ` or `export ` (both `export function`, `export class`, `export const`, `export default`, `export {`)
3. For `export class Foo` and `export function bar`, convert to just `class Foo` / `function bar`
4. Appends the processed content to the bundle

Add header comment:
```javascript
// =============================================================================
// MAP CORE BUNDLE - BeachMap, managers, utilities
// Source files preserved individually for maintainability
// =============================================================================
```

**Step 3: Verify globals are exposed**

Confirm that after stripping exports, the key classes are still assigned to `window`:
- `window.BeachMap = BeachMap` (in BeachMap.js)
- `window.modalStateManager` (in modal-state-manager.js)

If any `window.*` assignments are missing, add them at the end of the bundle.

**Step 4: Also check for `../offline/index.js` import in BeachMap.js**

BeachMap.js imports from `../offline/index.js`. This module needs to either:
- Be included in the bundle (if small)
- Or its import stripped and replaced with a window global

Investigate and handle appropriately.

**Step 5: Commit**

```bash
git add static/js/map-core-bundle.js
git commit -m "perf: create map-core-bundle.js (15 ES6 modules → 1 file)

Fixes part of #31"
```

---

## Task 2: Create map-panels-bundle.js

**Files:**
- Create: `static/js/map-panels-bundle.js`
- Source files (in order):

V2 panel modules:
  1. `static/js/map/reservation-panel-v2/utils.js`
  2. `static/js/map/reservation-panel-v2/panel-base.js`
  3. `static/js/map/reservation-panel-v2/panel-lifecycle.js`
  4. `static/js/map/reservation-panel-v2/edit-mode-mixin.js`
  5. `static/js/map/reservation-panel-v2/customer-mixin.js`
  6. `static/js/map/reservation-panel-v2/preferences-mixin.js`
  7. `static/js/map/reservation-panel-v2/state-mixin.js`
  8. `static/js/map/reservation-panel-v2/furniture-mixin.js`
  9. `static/js/map/reservation-panel-v2/pricing-mixin.js`
  10. `static/js/map/reservation-panel-v2/details-mixin.js`
  11. `static/js/map/reservation-panel-v2/save-mixin.js`
  12. `static/js/map/reservation-panel-v2/index.js`

V1 panel modules (already non-module, just concatenate):
  13. `static/js/map/reservation-panel/customer-handler.js`
  14. `static/js/map/reservation-panel/date-availability.js`
  15. `static/js/map/reservation-panel/pricing-calculator.js`
  16. `static/js/map/reservation-panel/conflict-resolver.js`
  17. `static/js/map/reservation-panel/safeguard-checks.js`
  18. `static/js/map/reservation-panel/panel-core.js`
  19. `static/js/map/new-reservation-panel.js`

**Step 1: Process V2 modules**

Same stripping process as Task 1. For each V2 file:
- Strip `import` lines
- Convert `export const MixinName = (Base) =>` to `const MixinName = (Base) =>`
- Convert `export class` to `class`
- Convert `export function` to `function`
- Convert `export default` to assignment or remove

**Step 2: Concatenate V1 modules**

V1 files are already traditional scripts (no import/export). Just concatenate them with section comments.

**Step 3: Verify globals**

Confirm these are exposed:
- `window.ReservationPanel` (in V2 index.js)
- `window.NewReservationPanel` or accessible globally (in new-reservation-panel.js)

**Step 4: Commit**

```bash
git add static/js/map-panels-bundle.js
git commit -m "perf: create map-panels-bundle.js (19 files → 1 file)

Bundles V1 + V2 reservation panels.
Fixes part of #31"
```

---

## Task 3: Create map-waitlist-bundle.js

**Files:**
- Create: `static/js/map-waitlist-bundle.js`
- Source files (in order):
  1. `static/js/waitlist/utils.js`
  2. `static/js/waitlist/state.js`
  3. `static/js/waitlist/dom.js`
  4. `static/js/waitlist/api.js`
  5. `static/js/waitlist/renderers.js`
  6. `static/js/waitlist/actions.js`
  7. `static/js/waitlist/modal.js`
  8. `static/js/waitlist/search.js`
  9. `static/js/waitlist/form-handler.js`
  10. `static/js/waitlist/index.js`

**Step 1: Read all files and verify order**

Check each file's imports. The waitlist modules use `import * as X from './Y.js'` pattern. When stripping imports, the functions need to be directly accessible (not namespaced).

**Important:** If waitlist code uses `api.fetchWaitlist()` (namespaced access), this won't work after stripping imports. Check if functions are accessed with namespace prefix or directly. If namespaced, wrap each module's exports in a namespace object:
```javascript
const api = { fetchWaitlist, updateWaitlist, ... };
```

**Step 2: Process and concatenate**

Strip imports/exports, handle namespacing if needed.

**Step 3: Verify globals**

Confirm `window.WaitlistManager` is exposed.

**Step 4: Commit**

```bash
git add static/js/map-waitlist-bundle.js
git commit -m "perf: create map-waitlist-bundle.js (10 modules → 1 file)

Fixes part of #31"
```

---

## Task 4: Convert map-page.js from ES6 module to regular script

**Files:**
- Modify: `static/js/map/map-page.js`

**Step 1: Strip import statements**

Remove all `import` lines from map-page.js. The classes it imports (BeachMap, SearchManager, BlockManager, etc.) will be available as globals from the bundles.

**Step 2: Remove `type="module"` behavior dependencies**

Check if map-page.js relies on module-specific behavior:
- Top-level `await` → wrap in async IIFE
- `import.meta` → remove or replace
- Strict mode → add `'use strict';` if needed

**Step 3: Commit**

```bash
git add static/js/map/map-page.js
git commit -m "perf: convert map-page.js from ES6 module to regular script

Removes import statements, uses window globals from bundles.
Fixes part of #31"
```

---

## Task 5: Update map.html and test

**Files:**
- Modify: `templates/beach/map.html`

**Step 1: Replace all script tags**

Replace the current `{% block extra_js %}` content with:
```html
{% block extra_js %}
<script src="{{ url_for('static', filename='js/map-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-core-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-panels-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-waitlist-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/map-page.js') }}"></script>
{% endblock %}
```

**Step 2: Test thoroughly**

Start the server and verify ALL functionality:
- Map loads and renders correctly
- Clicking available furniture selects it
- "Reservar" button opens V1 panel (create mode)
- Clicking occupied furniture opens V2 panel (view/edit mode)
- Waitlist panel opens and functions
- Search bar works
- Move mode works
- Block/unblock works
- Date picker works
- Customer search works
- No console errors

**Step 3: Commit**

```bash
git add templates/beach/map.html
git commit -m "perf: update map.html to use 3 JS bundles (44 files → 5 scripts)

Reduces JS HTTP requests from ~44 to 5.
Fixes #31"
```

---

## Summary

| Task | Before | After |
|------|--------|-------|
| 1. Map core bundle | 15 module files | 1 bundle |
| 2. Panels bundle | 19 files (V1+V2) | 1 bundle |
| 3. Waitlist bundle | 10 module files | 1 bundle |
| 4. Convert map-page.js | ES6 module | Regular script |
| 5. Update template | ~44 script tags | 5 script tags |

**Final state:** 5 JS script tags (map-bundle.js + 3 new bundles + map-page.js)
**Estimated time savings:** ~800-1000ms (network latency reduction)
