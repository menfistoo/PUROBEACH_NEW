# Map check-in / check-out sunbed markers

**Branch:** `feature/map-checkin-checkout-markers`
**Date:** 2026-06-07
**Goal:** Mark sunbeds on the interactive map whose occupying hotel guest **arrives (check-in)**
or **departs (check-out)** the hotel *today* (the viewed date), so staff can identify them at a glance.
**Definition (confirmed with user):** *hotel stay dates* — uses PMS `hotel_guests.arrival_date` /
`departure_date`, the same source as the existing customer-search badges.

## Current state (analysis)

- Check-in/check-out **already exists, but only in the customer-search dropdown** as
  `Check-in` / `Check-out` badges, driven by `is_checkin_today` / `is_checkout_today`
  (`models/hotel_guest.py`, `models/customer_search.py`). Verified across **all git branches**:
  a map-tile marker was never merged.
- The map's data payload (`models/reservation_availability.py::get_furniture_availability_map`)
  does **not** fetch arrival/departure, so the front-end has nothing to mark with.
- The SVG renderer (`static/js/map/renderer.js` → bundle `static/js/map-core-bundle.js`,
  `createFurnitureElement`) already draws corner indicators: 🔒 lock (top-right) and a notes
  badge (bottom-left). A new marker mirrors that pattern (top-left).
- **Bundle convention:** the template loads the hand-concatenated `map-core-bundle.js`; sources
  in `static/js/map/` are kept in sync manually (no automated build). Edit **both**.

## Changes (all additive / read-only — no schema change, no writes)

1. **Backend** `models/reservation_availability.py`
   - Add `c.booking_reference` to the reservations SELECT; carry `booking_reference` in `reservation_map`.
   - After building `reservation_map`, run **one batched** `hotel_guests` query (only stays
     overlapping the window, only the relevant booking_refs/rooms) → build
     `stay_by_ref` and `stays_by_room` lookups.
   - Per occupied entry, compute `is_checkin_today` / `is_checkout_today` vs that entry's date.
     Link by `booking_reference` (stable), fall back to `room_number` (pick the stay covering the date).
   - Externo / unmatched customers stay `False`.

2. **Frontend renderer** (`static/js/map/renderer.js` **and** `static/js/map-core-bundle.js`)
   - In `createFurnitureElement`, after the notes indicator, draw a top-left badge:
     **Entrada** = green `#55996D` `↓`; **Salida** = red `#E45E41` `↑`. If both (changeover), offset.

3. **Tooltip** (`static/js/map/tooltips.js` **and** bundle tooltips section)
   - Add a line: `🟢 Check-in hoy` / `🔴 Check-out hoy`.

4. **Legend** (`templates/beach/map.html`) — add legend entries *only if* a legend block exists; else skip.

## Safety / rollback

- Display-only + one extra read query; no migrations, no writes, no reservation-logic changes.
- Test on the branch (run `python -m pytest`), then user review, then careful deploy.
- Rollback = `git revert` of the commit (pure front-end + read query).

## Test checklist

- [ ] `python -m pytest` green (esp. availability map tests).
- [ ] A guest arriving today shows green ↓; departing today shows red ↑.
- [ ] Externo reservation shows no marker.
- [ ] Marker doesn't collide with lock / notes / VIP.
- [ ] Calendar/range endpoint (`/map/availability`) still correct.
