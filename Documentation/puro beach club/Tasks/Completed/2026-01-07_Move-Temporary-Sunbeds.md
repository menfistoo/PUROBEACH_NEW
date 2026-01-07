# Move Temporary Sunbeds - Drag and Drop

**Completed:** 2026-01-07
**Status:** ✅ Complete

## Summary

Implemented drag-and-drop repositioning for temporary furniture on the live beach map. Temporary furniture can now be moved by clicking and dragging, with position changes persisted to the database.

## Features Implemented

### Drag Behavior
- **Always draggable**: Temporary furniture can be dragged without requiring edit mode
- **Click vs drag detection**: 5px threshold distinguishes clicks (opens modal) from drags (moves)
- **Zoom-aware**: Drag calculations account for current zoom level
- **Grid snapping**: Positions snap to 10px grid for consistent alignment
- **Visual feedback**: Gold border and glow effect during drag (design system colors)
- **Cursor change**: `move` cursor on temporary furniture, `not-allowed` on blocked

### Position Persistence
- Uses existing `PUT /beach/api/map/furniture/<id>/position` endpoint
- Position updates apply permanently to the furniture definition
- Error handling with automatic revert on failure
- Success/error toasts in Spanish

### Click Suppression
- After a drag operation, the click event is suppressed to prevent the modal from opening
- Only affects the immediate click after drag ends

## Files Modified

### `static/js/map/interaction.js`
- Added temp furniture drag state properties to constructor
- Added `isTemporaryFurniture(element)` helper method
- Added `parseTransform(transform)` helper method
- Added `handleTempDragStart()`, `handleTempDrag()`, `handleTempDragEnd()` handlers
- Added `cancelTempDrag()` for error handling
- Updated `destroy()` to cleanup temp drag state

### `static/js/map/BeachMap.js`
- Added `_suppressNextClick` flag for click suppression
- Added bound methods for temp drag handlers
- Wired temp drag mouse events in `setupEventListeners()`
- Modified `handleFurnitureClick()` to check click suppression
- Updated `destroy()` to remove temp drag event listeners

### `static/css/map-temporary.css`
- Added `cursor: move` for `.furniture-item.temporary:not(.blocked)`
- Added `cursor: not-allowed` for `.furniture-item.temporary.blocked`
- Added `.dragging` visual state (gold border, glow, reduced opacity)
- Added text selection prevention during drag

### `static/js/map/renderer.js`
- Added cursor style override for temporary furniture (`move` instead of `pointer`)

## Visual Behavior

| State | Cursor | Border |
|-------|--------|--------|
| Temp furniture (hover) | `move` | Sky blue dashed |
| Temp furniture (dragging) | `move` | Gold solid + glow |
| Blocked temp furniture | `not-allowed` | Gray |
| Permanent furniture | `pointer` | No change |

## Technical Details

### Drag Flow
1. `mousedown` on temp furniture → Start tracking position
2. `mousemove` → If distance > 5px, activate drag mode, update visual position
3. `mouseup` → If was drag, save position via API, set click suppression flag

### Transform Handling
- Extracts `translate(x, y)` and `rotate(angle)` from SVG transform
- Preserves rotation during drag
- Applies grid snapping before visual update

### Error Handling
- Network errors: Toast message, revert to original position
- Permission denied: Toast message, revert to original position
- Context menu during drag: Cancel drag gracefully

## Testing Performed
- ✅ Drag temp furniture, position saves
- ✅ Click temp furniture, modal opens (no drag occurred)
- ✅ Position persists after page reload
- ✅ Cursor shows `move` for temp, `pointer` for regular
- ✅ Gold visual feedback during drag
- ✅ Grid snapping works correctly
- ✅ No flicker after drag (optimistic updates working)

## Bug Fixes (2026-01-07)
1. **Snap-back issue**: Fixed race condition where auto-refresh was re-rendering during save
2. **Delay issue**: Fixed zoom sync - interaction manager now receives zoom updates
3. **Cursor**: Fixed in renderer.js to set `move` cursor for temp furniture
4. **Flicker issue**: Implemented **optimistic updates** pattern - removed post-save refresh since visual position is already correct after dragging. Only revert on error.
5. **Click snap-back issue**: Fixed with TRUE optimistic updates - update local data cache (`this.data.furniture`) **IMMEDIATELY** when drag ends, BEFORE the async save. This ensures any render during save uses the correct position. On save error, revert both cache and DOM.

See `Issues/DONE/move-temp-furniture-bugs.md` for details.

## Architecture: True Optimistic Updates

The drag-and-drop uses a TRUE optimistic update pattern for smooth, flicker-free operation:

| Step | What Happens |
|------|--------------|
| 1. Drag | Visual position (DOM transform) updates immediately |
| 2. Drop | **Cache updated IMMEDIATELY** (before save) |
| 3. Save | Position saved to server in background |
| 4. Success | Nothing needed - cache and DOM already correct |
| 5. Error | Revert **both** cache and DOM, show toast |

**Key insight:** The local data cache must be updated **IMMEDIATELY** when drag ends, **BEFORE** the async save starts. This ensures any render that happens during the save (from event bubbling, auto-refresh, etc.) uses the correct new position from cache.

**Critical timing:**
```
WRONG:  drag → save (async) → update cache → done
        ↑ render here uses stale cache = snap-back

RIGHT:  drag → update cache → save (async) → done
        ↑ render here uses new cache = correct position
```

This eliminates both flicker and snap-back issues completely.

## Related Files
- Plan: `C:\Users\catia\.claude\plans\virtual-beaming-nygaard.md`
- Design System: `DESIGN_SYSTEM.md` (gold accent color #D4AF37)
