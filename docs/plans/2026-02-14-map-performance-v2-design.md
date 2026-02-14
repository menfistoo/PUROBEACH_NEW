# Map Loading Performance V2 - Aggressive JS Bundling

**Issue:** #31 - Tiempo de carga del mapa demasiado lento
**Date:** 2026-02-14
**Prerequisite:** V1 design (CSS bundle + basic JS bundle + defer) already implemented

## Problem

After Phase 1 optimizations (CSS bundle, 5-file JS bundle, deferred init), the map page still takes ~4 seconds to load. Profiling revealed the root cause: **~40 ES6 module files loaded sequentially**, each incurring HTTP request overhead.

### Current State (Post Phase 1)

| Resource Type | Files | Size |
|--------------|-------|------|
| CSS | 1 bundle | ~214KB |
| Non-module JS bundle | 1 (map-bundle.js) | ~72KB |
| ES6 modules (map core) | ~15 files | ~200KB |
| ES6 modules (V2 panel) | 12 files | ~148KB |
| ES6 modules (waitlist) | ~10 files | ~108KB |
| V1 panel (traditional) | 7 files | ~105KB |
| **Total JS** | **~44 files** | **~633KB** |

### Load Waterfall

```
T0-200ms:  HTML + CSS (blocking)
T200-500ms: Base JS (Bootstrap, main.js)
T500-1500ms: 44 JS files load sequentially (~1000ms wasted on latency)
T1500-1700ms: API call /beach/api/map/data
T1700-1820ms: SVG rendering
```

**The #1 bottleneck is sequential JS loading: ~1000ms of pure network overhead.**

## Key Finding: V1 Panel is NOT Dead Code

Investigation revealed V1 (NewReservationPanel) and V2 (ReservationPanel) serve different purposes:
- **V1 = CREATE** new reservations (triggered by selecting furniture → "Reservar")
- **V2 = VIEW/EDIT** existing reservations (triggered by clicking occupied furniture)

Both must stay. They cannot replace each other.

## Solution: 3 JS Bundles

Concatenate all ES6 modules into 3 bundles, stripping `import`/`export` statements and ordering by dependency. Keep `window.*` global assignments for cross-bundle access.

### Bundle 1: `map-core-bundle.js` (~15 files)

Map rendering, interaction, and management. Dependency order:
1. `map/utils.js` (shared utilities, no deps)
2. `map/modal-state-manager.js` (singleton)
3. `map/tooltips.js` (depends on utils)
4. `map/selection.js` (depends on utils)
5. `map/navigation.js` (depends on utils)
6. `map/context-menu.js` (depends on utils)
7. `map/interaction.js` (depends on utils)
8. `map/renderer.js` (depends on utils)
9. `map/pinch-zoom.js` (no deps)
10. `map/BeachMap.js` (depends on all above)
11. `map/SearchManager.js` (depends on utils)
12. `map/block-manager.js` (depends on utils)
13. `map/temp-furniture-manager.js` (depends on utils)
14. `map/MoveMode.js` (depends on utils)
15. `map/MoveModePanel.js` (depends on utils)

Globals exposed: `window.BeachMap`, `window.modalStateManager`

### Bundle 2: `map-panels-bundle.js` (~19 files)

V1 + V2 reservation panels. Dependency order:

**V2 Panel (ES6 modules → concatenated):**
1. `reservation-panel-v2/utils.js`
2. `reservation-panel-v2/panel-base.js`
3. `reservation-panel-v2/panel-lifecycle.js`
4. `reservation-panel-v2/edit-mode-mixin.js`
5. `reservation-panel-v2/customer-mixin.js`
6. `reservation-panel-v2/preferences-mixin.js`
7. `reservation-panel-v2/state-mixin.js`
8. `reservation-panel-v2/furniture-mixin.js`
9. `reservation-panel-v2/pricing-mixin.js`
10. `reservation-panel-v2/details-mixin.js`
11. `reservation-panel-v2/save-mixin.js`
12. `reservation-panel-v2/index.js`

**V1 Panel (already traditional scripts):**
13. `reservation-panel/customer-handler.js`
14. `reservation-panel/date-availability.js`
15. `reservation-panel/pricing-calculator.js`
16. `reservation-panel/conflict-resolver.js`
17. `reservation-panel/safeguard-checks.js`
18. `reservation-panel/panel-core.js`
19. `new-reservation-panel.js`

Globals exposed: `window.ReservationPanel`, `window.NewReservationPanel`

### Bundle 3: `map-waitlist-bundle.js` (~10 files)

Waitlist manager. Dependency order:
1. `waitlist/utils.js`
2. `waitlist/state.js`
3. `waitlist/dom.js`
4. `waitlist/api.js`
5. `waitlist/renderers.js`
6. `waitlist/actions.js`
7. `waitlist/modal.js`
8. `waitlist/search.js`
9. `waitlist/form-handler.js`
10. `waitlist/index.js`

Globals exposed: `window.WaitlistManager`

### Entry Point: `map-page.js`

Stays as a standalone `<script type="module">` or converted to regular script. It's the app entry point that wires everything together.

### Concatenation Process

For each bundle:
1. Read files in dependency order
2. Strip `import` and `export` statements
3. Add section comment headers
4. Concatenate into bundle file

### map.html After Bundling

```html
{% block extra_js %}
<script src="{{ url_for('static', filename='js/map-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-core-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-panels-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map-waitlist-bundle.js') }}"></script>
<script src="{{ url_for('static', filename='js/map/map-page.js') }}"></script>
{% endblock %}
```

**5 script tags total** (down from ~44).

## Expected Results

| Metric | Phase 1 | Phase 2 (this) |
|--------|---------|----------------|
| JS files loaded | ~44 | 5 |
| HTTP requests saved | — | ~39 |
| Latency saved | — | ~800-1000ms |
| Estimated load time | ~4s | ~2-2.5s |

## Risks

1. **Concatenation order matters** — wrong order = runtime errors. Mitigated by testing.
2. **Debugging harder** — no source maps. Mitigated by using 3 bundles (not 1) with section comments.
3. **Maintenance overhead** — must regenerate bundle when editing source files. Source files preserved.

## Out of Scope

- Build system (esbuild/webpack/Vite)
- Source maps
- Minification
- Code splitting / lazy loading
- Server-side caching headers
