# Map Loading Performance - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce map page load time by eliminating dead code, reducing HTTP requests via file concatenation, and deferring non-critical initialization.

**Architecture:** No build tooling - manual file concatenation and dead code removal. Flask serves static files directly.

**Tech Stack:** HTML, CSS, JavaScript (vanilla ES6), Jinja2 templates

---

## Task 1: Remove Dead V1 Reservation Panel Code

**Files:**
- Delete: `static/js/map/reservation-panel/` (entire directory - 6 files)
- Delete: `static/js/map/new-reservation-panel.js`
- Modify: `templates/beach/map.html:609-615`

**Step 1: Verify V1 is unused**

Search the entire codebase for references to V1 panel files:
```bash
grep -r "reservation-panel/panel-core" --include="*.html" --include="*.js" --include="*.py" .
grep -r "reservation-panel/customer-handler" --include="*.html" --include="*.js" .
grep -r "NewReservationPanel" --include="*.js" --include="*.html" .
```

Expected: Only references in map.html script tags and the files themselves. No actual usage.

**Step 2: Remove script tags from map.html**

Remove lines 609-615 (the 6 V1 script tags + new-reservation-panel.js):
```html
<!-- DELETE THESE LINES -->
<script src="...js/map/reservation-panel/customer-handler.js"></script>
<script src="...js/map/reservation-panel/date-availability.js"></script>
<script src="...js/map/reservation-panel/pricing-calculator.js"></script>
<script src="...js/map/reservation-panel/conflict-resolver.js"></script>
<script src="...js/map/reservation-panel/safeguard-checks.js"></script>
<script src="...js/map/reservation-panel/panel-core.js"></script>
<script src="...js/map/new-reservation-panel.js"></script>
```

Also remove the comment on line 608: `<!-- NewReservationPanel modules (must be loaded in dependency order) -->`

**Step 3: Delete V1 files**

```bash
rm -rf static/js/map/reservation-panel/
rm static/js/map/new-reservation-panel.js
```

**Step 4: Test the map page**

Start the server and verify:
- Map loads correctly
- Clicking furniture opens reservation panel (V2)
- Creating/editing reservations works
- No console errors about missing scripts

**Step 5: Commit**

```bash
git add -A
git commit -m "perf: remove dead V1 reservation panel code (6 files, ~2800 lines)

Fixes part of #31"
```

---

## Task 2: Concatenate CSS Files into Map Bundle

**Files:**
- Create: `static/css/map-bundle.css`
- Modify: `templates/beach/map.html:8-22`

**Step 1: Create concatenated CSS bundle**

Concatenate these 13 CSS files in order into `static/css/map-bundle.css`:
1. `static/css/customer-search.css`
2. `static/css/date-picker.css`
3. `static/css/reservation-panel.css`
4. `static/css/new-reservation-panel.css`
5. `static/css/conflict-resolution-modal.css`
6. `static/css/safeguard-modal.css`
7. `static/css/map-search.css`
8. `static/css/map-blocks.css`
9. `static/css/map-temporary.css`
10. `static/css/waitlist.css`
11. `static/css/offline.css`
12. `static/css/move-mode.css`
13. `static/css/map-page.css`

Add a header comment to identify each section:
```css
/* =============================================================================
 * MAP BUNDLE - Auto-concatenated CSS for /beach/map page
 * Source files preserved individually for maintainability
 * ============================================================================= */

/* --- customer-search.css --- */
...content...

/* --- date-picker.css --- */
...content...
```

**Step 2: Update map.html template**

Replace all 13 `<link>` tags (lines 8-22) with single reference:
```html
{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/map-bundle.css') }}">
{% endblock %}
```

**Step 3: Test**

- Map page loads correctly with all styles applied
- Reservation panel styling intact
- Search bar, filters, modals all styled correctly
- No visual regressions

**Step 4: Commit**

```bash
git add static/css/map-bundle.css templates/beach/map.html
git commit -m "perf: bundle 13 CSS files into single map-bundle.css

Reduces CSS requests from 13 to 1.
Fixes part of #31"
```

---

## Task 3: Concatenate Non-Module JS Files

**Files:**
- Create: `static/js/map-bundle.js`
- Modify: `templates/beach/map.html`

**Step 1: Create concatenated JS bundle**

Concatenate these non-module scripts into `static/js/map-bundle.js`:
1. `static/js/customer-search.js`
2. `static/js/date-picker.js`
3. `static/js/map/touch-handler.js`
4. `static/js/map/safeguard-modal.js`
5. `static/js/conflict-resolution-modal.js`

Wrap each in an IIFE or add section comments:
```javascript
// =============================================================================
// MAP BUNDLE - Concatenated non-module JS for /beach/map page
// =============================================================================

// --- customer-search.js ---
...content...

// --- date-picker.js ---
...content...
```

**Step 2: Update map.html template**

Replace the 5 non-module script tags with:
```html
<script src="{{ url_for('static', filename='js/map-bundle.js') }}"></script>
```

Keep the ES6 module scripts as-is:
```html
<script type="module" src="{{ url_for('static', filename='js/map/modal-state-manager.js') }}"></script>
<script type="module" src="{{ url_for('static', filename='js/map/reservation-panel-v2/index.js') }}"></script>
<script type="module" src="{{ url_for('static', filename='js/waitlist/index.js') }}"></script>
<script type="module" src="{{ url_for('static', filename='js/map/index.js') }}"></script>
<script type="module" src="{{ url_for('static', filename='js/map/map-page.js') }}"></script>
```

**Step 3: Test**

- Customer search works (autocomplete, selection)
- Date picker works (navigation, selection)
- Touch interactions work on map
- Safeguard modal appears when needed
- Conflict resolution modal works
- No console errors

**Step 4: Commit**

```bash
git add static/js/map-bundle.js templates/beach/map.html
git commit -m "perf: bundle 5 non-module JS files into single map-bundle.js

Reduces JS requests from 5 to 1.
Fixes part of #31"
```

---

## Task 4: Defer Non-Critical Manager Initialization

**Files:**
- Modify: `static/js/map/map-page.js`

**Step 1: Defer MoveMode unassigned check**

In `map-page.js`, find the call to `checkUnassignedReservationsGlobal()` (around line 272) and wrap it in a 2000ms delay:

```javascript
// Before:
checkUnassignedReservationsGlobal();

// After:
setTimeout(() => checkUnassignedReservationsGlobal(), 2000);
```

**Step 2: Add loading indicator for map**

Add a brief "Cargando mapa..." text or spinner that disappears when the SVG renders. Check if one already exists - if so, ensure it's visible during load.

**Step 3: Test**

- Map loads and renders correctly
- MoveMode unassigned badge appears after 2s delay
- Waitlist badge still appears (already delayed 500ms)
- No regressions in map functionality

**Step 4: Commit**

```bash
git add static/js/map/map-page.js
git commit -m "perf: defer non-critical manager initialization on map load

Delays MoveMode unassigned check to reduce initial load pressure.
Fixes #31"
```

---

## Summary

| Task | Requests Saved | Code Removed |
|------|---------------|-------------|
| 1. Remove V1 dead code | 7 requests | ~2800 lines |
| 2. CSS bundle | 12 requests | 0 (concatenated) |
| 3. JS bundle | 4 requests | 0 (concatenated) |
| 4. Defer init | 0 requests | N/A (timing) |
| **Total** | **23 requests** | **~2800 lines** |

Final state: 31 requests → 8 requests, zero dead code.
