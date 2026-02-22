# Simulation Health Check Report

**Date:** 2026-02-22
**Database:** `C:\Users\catia\programas\PuroBeach\PuroBeach\database\beach_club_sim.db`
**Run at:** 18:20:16

## Data Integrity

| Check | Severity | Issues |
|-------|----------|--------|
| Double bookings (same furniture, same date) | OK | 0 |
| Orphaned beach_reservation_furniture rows (no parent reservation) | OK | 0 |
| Multi-day child reservations with missing parent | OK | 0 |
| Active reservations with no furniture assignment | OK | 0 |

## Business Logic

| Check | Severity | Issues |
|-------|----------|--------|
| 'Sentada' state on past reservation dates | OK | 0 |
| External (externo) customer with charge_to_room=1 | OK | 0 |
| paid=1 with no payment_method set | OK | 0 |
| Furniture blocks overlapping active reservations | OK | 0 |
| Future reservations with releasing state (informational) | WARN | 116 |

### Future reservations with releasing state (informational)

- ticket=26040101 on 2026-04-01 (Cancelada)
- ticket=26040108 on 2026-04-01 (Cancelada)
- ticket=26040113 on 2026-04-01 (Cancelada)
- ticket=26040129 on 2026-04-01 (Cancelada)
- ticket=26040142 on 2026-04-01 (Cancelada)

## Performance

| Check | Severity | Issues |
|-------|----------|--------|
| Availability check (furniture conflicts for a date) | OK | 2 |
| Reservation list with customer join (last 30 days) | OK | 2151 |
| Map load (all active furniture with today assignments) | OK | 81 |
| Customer search (name LIKE) | OK | 3 |
| Daily report aggregation (reservations by date) | OK | 2 |
| Audit log recent entries | OK | 67 |
