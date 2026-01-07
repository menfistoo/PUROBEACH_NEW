# Block Sunbeds in the Live Map

**Status:** Completed
**Date:** 2026-01-07
**Phase:** 7a - Live Map Enhancements

---

## Summary

Implemented the ability to block furniture (maintenance, VIP hold, event, etc.) directly from the live map. This feature allows staff to temporarily take furniture out of service without deleting it.

## Features Implemented

### 1. Visual Indicator on Map
- Blocked furniture displays with block type color (maintenance gray, VIP gold, event blue)
- Reduced opacity (0.85) distinguishes blocked from available furniture
- Block emoji indicator on furniture (wrench, star, calendar)

### 2. Context Menu (Right-Click)
- **Block** option for available furniture - opens block modal
- **Unblock** option for blocked furniture - opens unblock modal
- **View Block Details** - shows block info in toast notification
- Full keyboard accessibility (Tab, Enter, Space, Escape)
- Proper ARIA roles for screen readers

### 3. Block Modal
- Select block type (Mantenimiento, Reserva VIP, Evento, Otro)
- Date range picker (start/end dates)
- Optional reason text field
- Supports blocking multiple selected furniture at once

### 4. Unblock Modal
- Displays current block information
- Two unblock modes:
  - **Full unblock**: Removes entire block
  - **Partial unblock**: Unblock specific date range within a block
- Intelligent block handling:
  - Deletes block if unblocking entire range
  - Shrinks block if unblocking from start/end
  - Splits block if unblocking middle dates

### 5. Selection Panel Integration
- Block button appears when furniture is selected
- Unblock button appears when blocked furniture is selected
- Quick access without right-click

### 6. Blocked Furniture Protection
- Blocked furniture cannot be selected for new reservations
- Toast notification explains why furniture can't be selected
- Visual distinction prevents confusion

## Files Modified

### New Files
| File | Purpose |
|------|---------|
| `static/js/map/context-menu.js` | Right-click context menu manager |
| `static/js/map/block-manager.js` | Block/unblock API integration and modal logic |
| `static/css/map-blocks.css` | Styling for context menu, modals, blocked furniture |

### Modified Files
| File | Changes |
|------|---------|
| `blueprints/beach/routes/api/map_data.py` | Include blocks in map data response |
| `blueprints/beach/routes/api/map_blocks.py` | Added partial unblock endpoint |
| `models/furniture_block.py` | Added `partial_unblock()` function for splitting blocks |
| `static/js/map/renderer.js` | Render blocked furniture with visual indicator |
| `static/js/map/selection.js` | Prevent selection of blocked furniture |
| `static/js/map/tooltips.js` | Added `showBlock()` method for block tooltips |
| `static/js/map/index.js` | Initialize context menu and block managers |
| `templates/beach/map.html` | Block/unblock modal HTML |

## API Endpoints

### Block Furniture
```
POST /beach/api/map/furniture/{id}/block
Body: {
    "start_date": "2026-01-07",
    "end_date": "2026-01-10",
    "block_type": "maintenance",
    "reason": "Reparacion de tela"
}
```

### Unblock Furniture (Full)
```
DELETE /beach/api/map/furniture/{id}/block?date=2026-01-07
```

### Partial Unblock
```
POST /beach/api/map/furniture/{id}/unblock-partial
Body: {
    "block_id": 123,
    "unblock_start": "2026-01-08",
    "unblock_end": "2026-01-08"
}
Response: {
    "action": "split|shrunk_start|shrunk_end|deleted",
    "block_ids": [123, 124]
}
```

## Block Types

| Type | Spanish Name | Color | Icon |
|------|--------------|-------|------|
| maintenance | Mantenimiento | #9CA3AF | wrench |
| vip_hold | Reserva VIP | #D4AF37 | star |
| event | Evento | #3B82F6 | calendar |
| other | Otro | #6B7280 | ban |

## Design System Compliance

After implementation, a design review was conducted and the following improvements were made:

### Fixed Issues
1. **Unblock modal header**: Changed from green (bg-success) to Deep Ocean gradient matching other modals
2. **Focus states**: Added keyboard focus indicators for context menu items
3. **Transition timing**: Standardized to 0.2s (design system standard)
4. **z-index**: Documented using CSS variable `--z-context-menu: 1050`
5. **Radio buttons**: Styled with gold accent when selected
6. **Tooltip opacity**: Added 0.95 opacity for slight transparency
7. **Keyboard accessibility**: Added tabindex, ARIA roles, and Enter/Space support

## Testing

Tested scenarios:
- Block single furniture from context menu
- Block multiple furniture from selection panel
- Unblock furniture completely
- Partial unblock (shrink from start)
- Partial unblock (shrink from end)
- Partial unblock (split block in middle)
- Verify blocked furniture shows visual indicator
- Verify blocked furniture cannot be selected
- Keyboard navigation through context menu

## Commits

- `af4eb08` - Add block sunbeds feature with context menu, modals, and partial unblock
- (Design fixes committed with this documentation)

---

## Related Documentation

- Plan file: `.claude/plans/twinkly-seeking-papert.md`
- Model: `models/furniture_block.py`
- API Routes: `blueprints/beach/routes/api/map_blocks.py`
