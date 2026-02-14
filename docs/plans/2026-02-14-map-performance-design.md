# Map Loading Performance - Design Document

**Issue:** #31 - Tiempo de carga del mapa demasiado lento
**Date:** 2026-02-14

## Problem

The `/beach/map` page loads 31 individual files (13 CSS + 18 JS scripts), totaling ~908KB. The backend responds in ~5ms, so the bottleneck is entirely frontend: too many HTTP requests and dead code.

Key discovery: The V1 reservation panel (6 script files, ~2800 lines) is loaded but **never used** - V2 completely replaced it.

## Root Causes

1. **Dead code:** V1 reservation-panel/ (6 files) loaded but never instantiated
2. **Too many HTTP requests:** 13 CSS + 18 JS = 31 individual requests
3. **Render-blocking CSS:** All 13 CSS files in `<head>` block first paint
4. **Eager initialization:** Non-critical managers (BlockManager, TempFurniture, MoveMode) initialized immediately

## Solution: Quick Wins (No Build Tooling)

### 1. Remove Dead V1 Code
- Delete `static/js/map/reservation-panel/` directory (6 files)
- Delete `static/js/map/new-reservation-panel.js` (stale wrapper)
- Remove 7 `<script>` tags from map.html (lines 609-615)
- **Saves:** 6 HTTP requests, ~2800 lines of dead JS

### 2. Concatenate CSS Files
- Merge 13 map-specific CSS files into `static/css/map-bundle.css`
- Keep individual files for maintainability, use a build script to concatenate
- Or: manually merge since these files rarely change
- **Saves:** 12 HTTP requests (13 → 1)

### 3. Concatenate Non-Module JS
- Merge non-module scripts into `static/js/map-bundle.js`:
  - customer-search.js
  - date-picker.js
  - touch-handler.js
  - safeguard-modal.js
  - conflict-resolution-modal.js
- Keep ES6 modules separate (they already use import/export)
- **Saves:** 4 HTTP requests (5 → 1)

### 4. Defer Non-Critical Initialization
- Move `checkUnassignedReservationsGlobal()` to 2000ms delay (was immediate)
- MoveMode panel: lazy-init on first toggle
- BlockManager: lazy-init on first use
- TempFurnitureManager: lazy-init on first use

### Expected Results

| Metric | Before | After |
|--------|--------|-------|
| HTTP requests | 31 | ~8 |
| Dead JS loaded | ~2800 lines | 0 |
| CSS files | 13 | 1 |
| Non-module JS files | 5 | 1 |
| ES6 module files | 3 | 3 (unchanged) |

## Out of Scope

- Build system (esbuild/webpack) - unnecessary complexity for Flask app
- Code splitting / dynamic imports for ES6 modules
- Server-side caching headers (can be done later)
- Service worker optimizations
