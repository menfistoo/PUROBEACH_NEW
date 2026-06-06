# Hotel guest list ↔ sunbed reservation — audit & implementation status

_Last updated: 2026-06-06_

## The reservation number
Format `BASE-N`, e.g. `2026-2875-1`. The trailing `-N` is the **room index within a
multi-room booking** (`…-1` = room 1 of the booking, `…-2` = room 2). All guests in one
room share that one full number. **The full string is the stable key** for a room + its
guests — it does not change when the physical room number changes, and it exists before a
room is assigned (pre-arrival). We anchor sunbed reservations to it.

## How the system works (post-fix)
- Guest list enters via PMS auto-sync (`scripts/sync_pms_guests.py`, Nextcloud, ~2h) or
  manual Excel upload → `import_hotel_guests_from_excel` → per-row UPSERT into
  `hotel_guests` (`booking_reference` = the "Reserva" column).
- A sunbed reservation links to a guest via `customer_id → beach_customers`; the room is
  shown via a live join to `beach_customers.room_number`.
- **Anchor:** `beach_customers.booking_reference` and `beach_reservations.booking_reference`
  store the hotel reservation number, set when a reservation is linked/created.
- **Room stays correct everywhere:** on import, `sync_customer_room_by_booking()` updates
  the room of customers tied to a CURRENT reservation with that booking_reference. This is
  robust (keyed on the stable number, scoped to active reservations) — it replaced the old
  fragile `propagate_room_change` (old-room + fuzzy-name), which is now fallback-only.

## Done (committed + deployed)
- **#5** migration: add `booking_reference` to `beach_customers` + `beach_reservations`
  (additive, idempotent; NO backfill — a room is reused by many guests over time, so
  room-only backfill over-assigns; the original backfill was run then cleared in prod).
- **#6** persist `booking_reference` on `create_customer_from_hotel_guest` and on
  single-day + multi-day reservation inserts.
- **#7** `sync_customer_room_by_booking()` + wired into the import.

## Remaining
### #8 Pre-arrival + search by reservation number (UI — needs iPad testing)
- Let the customer search match/enter a **reservation number** (find in-house guests by it,
  or accept a typed number for a not-yet-arrived booking).
- Allow creating an **interno** reservation with a `booking_reference` but **no room yet**
  (today `room_number` is required for interno + the importer rejects room-less rows).
- Show **"Pendiente de habitación"** when interno + has `booking_reference` + no room.
  When the guest later appears in the import with a room, #7's sync auto-fills it.
- Files: `blueprints/beach/routes/api/customers.py`, `models/customer_search.py`,
  bundled panel JS (`static/js/map-panels-bundle.js` + sources under
  `static/js/map/reservation-panel*/`), `static/js/customer-search.js`.

### #9 Import hardening (lower priority)
- Normalize `guest_name` for matching (trim, collapse spaces, strip accents, case-fold,
  "Last, First"). Currently booking_reference matching requires an EXACT name match
  (`hotel_guest.py:304`) → name-format drift creates duplicates / misses room changes.
- Make each import atomic (per-row commit today; partial failures persist).
- Reconcile stale guests: mark absent-from-full-export guests checked-out/inactive
  (with a sanity guard so a truncated file can't wipe everyone). Today import is
  UPSERT-only — cancelled/early-checkout guests linger.

## Deploy notes
- `./static` is volume-mounted + `versioned_static` cache-busts by mtime → CSS/JS edits
  go live on refresh (no rebuild). **Python/migrations/templates need a rebuild**
  (`docker compose build app && docker compose up -d app`); the entrypoint runs
  `flask run-migrations` on start.
- Always back up `instance/beach_club.db` before a migration.
