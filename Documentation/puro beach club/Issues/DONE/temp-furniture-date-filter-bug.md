# Temp Furniture Date Filter Bug

**Status:** DONE
**Reported:** 2026-01-07
**Fixed:** 2026-01-07
**Priority:** High

## Description

When creating temporary furniture with a specific date range (start_date → end_date), the furniture appears on ALL days instead of only the specified dates.

## Root Cause

The `get_all_furniture()` function in `models/furniture.py` did not filter temporary furniture by their date range. The map data endpoint was calling this function without passing the current date.

## Solution

1. **`models/furniture.py`**: Added `for_date` parameter to `get_all_furniture()`:
   ```python
   def get_all_furniture(zone_id=None, active_only=True, for_date=None):
       # ... existing query ...
       if for_date:
           query += '''
               AND (
                   f.is_temporary = 0
                   OR (f.is_temporary = 1
                       AND DATE(f.temp_start_date) <= DATE(?)
                       AND DATE(f.temp_end_date) >= DATE(?))
               )
           '''
   ```

2. **`blueprints/beach/routes/api/map_data.py`**: Pass date to furniture query:
   ```python
   furniture = get_all_furniture(active_only=True, for_date=date_str)
   ```

## Testing

- Created temp furniture T2 for 2026-01-07 only
- On Jan 7: T2 visible, Total = 12
- On Jan 8: T2 NOT visible, Total = 11
- Back to Jan 7: T2 visible again
