# Reservation anchor (booking_reference) enforcement

**Branch:** `feature/reservation-anchor-enforcement` (built on top of the check-in/out markers branch)
**Date:** 2026-06-07
**Goal:** Guarantee that interno sunbed reservations are anchored to the stable hotel
reservation number (`booking_reference`), so room/guest matching is unambiguous (fixes the
changeover-day ambiguity and makes the check-in/out markers accurate).

## Problem (measured on real data)

Of 101 current/future interno reservations, only **1** had an anchor. The anchor is only set
today when staff pick the guest from the GuestInHouse search; creating an interno by typing a
room, reusing an un-anchored customer, or a pre-arrival booking all leave it empty.

## Design

Single source of truth: **`beach_reservations.booking_reference`** (per existing code comment in
`hotel_guest.py`). Two new functions in `models/hotel_guest.py`:

- `resolve_booking_reference(room_number, on_date, guest_name=None, conn=None)` — resolves the
  anchor from `hotel_guests` by room + the stay covering `on_date`; disambiguates a changeover
  day by normalized name; returns None when not unambiguous.
- `backfill_missing_anchors(conn=None)` — fills the anchor on current/future interno reservations
  that are resolvable; propagates to the customer when empty. Only writes empty anchors, never
  overwrites, never touches past reservations, idempotent.

### Hooks
1. **Creation-time** (`reservation_crud.create_beach_reservation` + `reservation_multiday`): when
   interno + room but no anchor, resolve and set it on the reservation and the customer.
2. **PMS import** (`user_service.import_hotel_guests_from_excel`): after reconciliation, run
   `backfill_missing_anchors()` so pre-arrival bookings self-heal when the guest appears.
3. **CLI** `scripts/backfill_anchors.py` (`--dry-run` supported) for a one-time/manual run.

## Verification (staging, copy DB, real data)

- Backfill coverage: **1/101 → 84/101**; 83 anchored (incl. 1 changeover resolved by name → 0
  ambiguous); 17 pending (not yet in PMS). Second pass updates 0 (idempotent).
- App boots cleanly with all new code (no circular imports), map still serves.

## Coverage reality

100% at creation can't be guaranteed for pre-arrival bookings (no PMS row yet), but every
*resolvable* reservation is anchored automatically at creation and at each import, and the import
logs `X anchored, Y pending` so gaps are visible, not silent.

## Production rollout (pending approval)

1. Build image, run `python -m pytest` in a throwaway container (must pass).
2. `docker compose up -d --build` (ships backend; brief restart).
3. `docker compose exec app python scripts/backfill_anchors.py` (one-time fill of the ~83).
4. Verify import logs show anchoring on the next PMS sync.
Rollback: `git checkout main && docker compose up -d --build` (anchors already written are valid
data and harmless).
