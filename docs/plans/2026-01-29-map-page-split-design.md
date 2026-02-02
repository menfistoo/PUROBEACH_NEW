# map-page.js Split — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split `static/js/map/map-page.js` from 2,343 lines to ~1,460 by extracting 6 self-contained modules.

**Architecture:** Pure extraction — move code blocks into ES6 modules that export setup functions. Each module receives its dependencies as arguments. No behavior changes.

**Pattern:**
```javascript
// New file: static/js/map/page-<feature>.js
export function setup<Feature>(map, moveMode, panels) {
    // Extracted code, unchanged
}

// In map-page.js, replace inline block with:
import { setup<Feature> } from './page-<feature>.js';
setupFeature(map, moveMode, { reservationPanel, newReservationPanel });
```

## Modules

| # | File | Content | Lines |
|---|------|---------|-------|
| 1 | `page-keyboard-shortcuts.js` | Keydown handlers (Escape, Delete, Ctrl+A, arrows, zoom) | ~88 |
| 2 | `page-date-navigation.js` | Date picker, prev/next, swipe, zone selector | ~147 |
| 3 | `page-touch-handlers.js` | Long-press, touch-to-move, pinch zoom | ~86 |
| 4 | `page-context-menu.js` | Right-click menu setup and all actions | ~160 |
| 5 | `page-conflict-resolution.js` | Alternative furniture UI, conflict modal, swap | ~217 |
| 6 | `page-move-mode.js` | Move mode listeners, selection bar updates, unassigned check | ~184 |

**Total extracted:** ~882 lines
**map-page.js after:** ~1,460 lines
