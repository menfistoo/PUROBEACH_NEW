# Move Temporary Furniture Bugs

**Reported:** 2026-01-07
**Fixed:** 2026-01-07
**Status:** ✅ DONE

## Issues

### 1. Snap back to original position
After moving temporary furniture, it snaps back to the original position most of the time.

**Root Cause:** Race condition - auto-refresh was re-rendering the map while position save was in progress because `isDraggingTemp` was set to `false` before the save completed.

**Fix:** Keep `isDraggingTemp = true` until after `savePosition()` completes (in `interaction.js`)

### 2. Delay between mouse drag and item movement
There's a noticeable delay between the mouse movement and the furniture following.

**Root Cause:** Zoom level wasn't being synced to the interaction manager when zoom changed.

**Fix:** Added `interaction.setZoom()` calls in `applyZoom()` and `setZoom()` methods (in `BeachMap.js`)

### 3. Flicker after drag (shows old position briefly, then new position)
After dragging and releasing, the furniture would briefly flash back to the old position before showing the new position.

**Root Cause:** After saving position, `onPositionSaved` callback called `loadData()` which triggered `renderFurniture()`. The render function does `layer.innerHTML = ''` destroying ALL SVG elements, then recreates them from server data - causing visible flicker.

**Fix:** Implemented **optimistic updates** pattern - removed the `onPositionSaved` callback entirely. The visual position is already correct after dragging (we just moved it there), so no refresh is needed. Position is saved to database in background, and only on error do we revert the visual position.

### 4. Snap-back when clicking elsewhere on map
After dragging temp furniture, clicking anywhere else on the map would cause it to snap back to original position.

**Root Cause:** `this.data.furniture` (local data cache) was never updated when positions were saved. Only the DOM transform was updated. Any subsequent `render()` call (from clicks, auto-refresh, etc.) would use the stale cached position data.

**Initial Fix Attempt:** Updated cache AFTER save completes - but this caused the opposite problem (snap-back on release, then correct position on click) because renders during the async save used stale cache.

**Final Fix:** True optimistic updates - update cache **IMMEDIATELY** when drag ends, BEFORE the async save:
```javascript
// In handleTempDragEnd (interaction.js):
// 1. Update cache IMMEDIATELY (before save)
if (this.onPositionUpdate) {
    this.onPositionUpdate(furnitureId, finalPos.x, finalPos.y);
}

// 2. Then save to server
try {
    await this.savePosition(furnitureId, finalPos.x, finalPos.y, finalPos.rotation);
} catch (error) {
    // On error: revert BOTH cache and DOM
    if (this.onPositionUpdate) {
        this.onPositionUpdate(furnitureId, startPos.x, startPos.y);
    }
    // ... revert DOM transform
}
```
This ensures any render during the async save uses the correct (new) position.

## Files Modified

### `static/js/map/interaction.js`
- Added `onPositionUpdate` callback option in constructor
- Call `onPositionUpdate` after successful position save in `handleTempDragEnd()`
- Keep `isDraggingTemp = true` until save completes to block auto-refresh
- On save error, revert visual position to original
- Removed debug console.log statements

### `static/js/map/BeachMap.js`
- Added `interaction.setZoom()` in `applyZoom()` to sync zoom after every zoom change
- Added `interaction.setZoom()` in `setZoom()` for manual zoom changes
- Added check in `refreshAvailability()` to skip refresh when `isDraggingTemp` is true
- Added `onPositionUpdate` callback that updates `this.data.furniture` cache

### `static/js/map/renderer.js`
- Added cursor override for temp furniture (`move` instead of default `pointer`)

## Testing
- ✅ Drag temp furniture - moves smoothly
- ✅ Position persists during auto-refresh
- ✅ Position persists after page reload
- ✅ Correct `move` cursor on temp furniture
- ✅ No flicker after drag (optimistic updates working)
- ✅ No snap-back when clicking elsewhere on map
- ✅ No snap-back when clicking on other furniture items
