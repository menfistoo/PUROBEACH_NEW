# Reservation Characteristics - Design Document

**Date:** 2026-02-14
**Issue:** #21 - No hay opción de ver/cambiar características en reservas
**Status:** Approved

## Problem

Reservation creation and editing never writes characteristics to the `beach_reservation_characteristics` junction table. Only the deprecated CSV column (`beach_reservations.preferences`) gets updated. This means:

- Furniture suggestion scoring returns 0% match (reads junction table, finds nothing)
- No per-reservation characteristic UI in the reservation list edit form
- Data inconsistency between CSV column and junction table

## Solution

Wire the existing `set_reservation_characteristics()` into both create and edit flows. Add characteristic toggles to the reservation edit form matching the map panel style. Both paths edit the same data.

## Data Flow

```
Map Panel (create/edit) ──┐
                          ├──► set_reservation_characteristics() ──► beach_reservation_characteristics
Reservation Edit Form ────┘                                              │
                                                                         ▼
                                                          Suggestion Engine reads junction table
```

Single source of truth: `beach_reservation_characteristics` junction table.

## Backend Changes

### 1. Reservation Creation (`map_res_create.py`)
- After creating reservation, call `set_reservation_characteristics()` with preference codes
- Currently only calls `set_customer_characteristics_by_codes()` (line ~272, ~326)

### 2. Reservation Edit via Map (`map_res_edit_fields.py`)
- When preferences change (line ~103-106), call `set_reservation_characteristics()` instead of updating CSV
- Currently only updates `beach_reservations.preferences` CSV column

### 3. Reservation Edit Form Route (`reservations.py`)
- Pass available characteristics to the edit form template
- Handle characteristic IDs in form submission
- Call `set_reservation_characteristics()` on save

### 4. Reservation Detail
- Display assigned characteristics using `get_reservation_characteristics()`

## Frontend Changes

### Reservation Edit Form (`_step2_details.html`)
- Add characteristic toggle pills matching map panel style
- Pre-select based on `get_reservation_characteristics(reservation_id)`
- Submit characteristic IDs alongside other form data
- Brand-consistent styling (gold toggles, flat design)

### Reservation Detail View
- Show assigned characteristics as pills/badges

## Data Migration

- One-time script: parse existing CSV `preferences` → resolve to characteristic IDs → insert into junction table
- Idempotent (skip reservations already populated)

## Cleanup

- Stop writing to `beach_reservations.preferences` CSV column
- Keep column in schema (non-breaking) but deprecate
- Remove old `beach_preferences` / `beach_customer_preferences` references if unused elsewhere

## Files to Modify

| File | Change |
|------|--------|
| `blueprints/beach/routes/api/map_res_create.py` | Add `set_reservation_characteristics()` call |
| `blueprints/beach/routes/api/map_res_edit_fields.py` | Replace CSV write with junction table write |
| `blueprints/beach/routes/reservations.py` | Pass characteristics to edit template, handle on save |
| `templates/beach/reservation_form/_step2_details.html` | Add characteristic toggles UI |
| `templates/beach/reservation_detail.html` | Show characteristics (if exists) |

## Existing Infrastructure (no changes needed)

- `models/characteristic.py` - CRUD operations ✅
- `models/characteristic_assignments.py` - Junction table operations ✅
- `database/schema.py` - Tables exist ✅
- `blueprints/beach/routes/config/characteristics.py` - Admin config ✅
- `static/js/map/reservation-panel-v2/preferences-mixin.js` - Map panel UI ✅
