# Add Temporary Sunbeds in the Live Map

**Status**: ✅ Completed
**Started**: 2026-01-07
**Completed**: 2026-01-07

## Requirements
- **Add methods**: Right-click on empty map space AND toolbar button
- **Duration**: Date range (start_date → end_date)
- **Furniture types**: All types available

## Implementation Summary

### Database Migration
- Added `temp_start_date` and `temp_end_date` columns to `beach_furniture` table
- Created migration script: `database/migrations/temp_furniture_date_range.py`

### Backend Changes
- **`models/furniture.py`**: Added `for_date` parameter to `get_all_furniture()` to filter temp furniture by date range
- **`models/furniture_daily.py`**:
  - Updated `create_temporary_furniture()` for date ranges
  - Added `get_next_temp_furniture_number()` for auto-generation (T1, T2, etc.)
  - Added `partial_delete_temp_furniture()` for single-day or full deletion
  - Added `get_temp_furniture_date_info()` for multi-day detection
- **`blueprints/beach/routes/api/map_temporary.py`**:
  - Updated POST endpoint for date range creation
  - Updated DELETE endpoint for partial/full deletion
  - Added `/info` endpoint for date info
  - Added `/next-number` endpoint

### Frontend Changes
- **`static/js/map/temp-furniture-manager.js`**: New module for modal interactions
- **`static/js/map/context-menu.js`**: Added empty space menu + delete temp option
- **`static/js/map/renderer.js`**: Added temporary class and sky blue styling
- **`static/js/map/BeachMap.js`**: Integrated TempFurnitureManager
- **`static/css/map-temporary.css`**: Visual styling for temp furniture
- **`templates/beach/map.html`**: Create and delete modals

## Visual Design
- Dashed border stroke (5px dash, 3px gap)
- Sky blue color: stroke `#0EA5E9`, fill `#E0F2FE`
- "T" prefix for numbers (T1, T2, T3...)
- Delete modal matches unblock modal UI pattern with radio options

## Features
- ✅ Right-click on empty map space → "Añadir Mobiliario Temporal"
- ✅ Toolbar button for quick access
- ✅ Zone, type, capacity, orientation selection
- ✅ Date range support (start_date → end_date)
- ✅ Auto-generate number (T1, T2, etc.)
- ✅ Right-click on temp furniture → "Eliminar Mobiliario Temporal"
- ✅ Partial delete (single day) or full delete (entire range)
- ✅ Date filter: temp furniture only visible within its date range
- ✅ Visual distinction with dashed sky-blue border
- ✅ Keyboard focus states for accessibility
- ✅ Design system compliance

## Bug Fixes
- Fixed date filter bug: temp furniture now only appears on dates within its range
- See: `Issues/DONE/temp-furniture-date-filter-bug.md`
