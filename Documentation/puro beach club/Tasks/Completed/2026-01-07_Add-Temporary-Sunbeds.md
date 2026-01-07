# Add Temporary Sunbeds in the Live Map

**Status**: In Progress
**Started**: 2026-01-07

## Requirements
- **Add methods**: Right-click on empty map space AND toolbar button
- **Duration**: Date range (start_date → end_date)
- **Furniture types**: All types available

## Implementation Steps

1. Database migration - Add `temp_start_date`, `temp_end_date` columns
2. Model updates - Support date ranges in `furniture_daily.py`
3. API updates - Accept start/end dates
4. TempFurnitureManager.js - New JS module
5. Context menu - Empty space menu + delete option
6. Modal HTML - Create/delete modals
7. Toolbar button - Quick access
8. CSS styles - Dashed border, sky blue for temp items
9. Integration - BeachMap.js, renderer.js

## Visual Design
- Dashed border stroke
- Sky blue color (#0EA5E9)
- "T" prefix for numbers (T1, T2, etc.)
