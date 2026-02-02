# Reservation Furniture Highlight on Live Map

**Issue:** #2 - Highlight reservation furniture on map when viewing/editing
**Date:** 2026-01-28

## Goal

When the reservation panel opens on the live map, highlight all furniture items belonging to that reservation for the currently displayed date, using a pulsing gold glow effect.

## Visual Effect

- SVG filter `reservation-highlight-glow` added to map `<defs>`
- Gold (#D4AF37) drop-shadow, larger radius than existing `selected-glow`
- CSS `@keyframes pulse-glow` alternates opacity 0.6 → 1.0 over 1.5s
- Applied via `.reservation-highlight` class on furniture `<g>` elements
- State fill colors remain visible — glow is outer shadow, not overlay
- Replaces `.selected` glow while active; `.blocked` overlay unaffected

## Implementation Flow

1. `openReservationPanel()` opens panel, panel fetches reservation data
2. Panel data includes `furniture_assignments` — filter by current map date
3. Call `map.highlightFurniture(furnitureIds)` → adds `.reservation-highlight` to matching SVG elements
4. Panel close → `map.clearHighlights()` removes class from all elements
5. Opening a different reservation → clear previous, apply new

## Scope

- Only highlight furniture assigned for the currently displayed date
- Furniture from other days is not highlighted (map shows single-day state)

## Files Changed

- `static/js/map/renderer.js` — SVG filter def + `highlightFurniture()`/`clearHighlights()` methods
- `static/js/map/map-page.js` — call highlight on panel open, clear on panel close
- `templates/beach/map.html` or `static/css/map.css` — pulse animation keyframes + `.reservation-highlight` class
