# Simulation Health Check Report

**Date:** 2026-02-22
**Database:** `C:\Users\catia\programas\PuroBeach\PuroBeach\database\beach_club_sim.db`
**Run at:** 13:24:03

## Data Integrity

| Check | Severity | Issues |
|-------|----------|--------|
| Double bookings (same furniture, same date) | OK | 0 |
| Orphaned beach_reservation_furniture rows (no parent reservation) | OK | 0 |
| Multi-day child reservations with missing parent | OK | 0 |
| Active reservations with no furniture assignment | WARN | 537 |

### Active reservations with no furniture assignment

- ticket=26030205 on 2026-03-02 (Confirmada)
- ticket=26030206 on 2026-03-02 (Confirmada)
- ticket=26030216 on 2026-03-02 (Confirmada)
- ticket=26030230 on 2026-03-02 (Confirmada)
- ticket=26030231 on 2026-03-02 (Confirmada)
- ticket=26030240 on 2026-03-02 (Confirmada)
- ticket=26030246 on 2026-03-02 (Confirmada)
- ticket=26030301 on 2026-03-03 (Confirmada)
- ticket=26030306 on 2026-03-03 (Confirmada)
- ticket=26030310 on 2026-03-03 (Confirmada)
- ticket=26030312 on 2026-03-03 (Confirmada)
- ticket=26030315 on 2026-03-03 (Confirmada)
- ticket=26030317 on 2026-03-03 (Confirmada)
- ticket=26030330 on 2026-03-03 (Confirmada)
- ticket=26030341 on 2026-03-03 (Confirmada)
- ticket=26030343 on 2026-03-03 (Confirmada)
- ticket=26030364 on 2026-03-03 (Confirmada)
- ticket=26030367 on 2026-03-03 (Confirmada)
- ticket=26030404 on 2026-03-04 (Confirmada)
- ticket=26030411 on 2026-03-04 (Confirmada)

## Business Logic

| Check | Severity | Issues |
|-------|----------|--------|
| 'Sentada' state on past reservation dates | OK | 0 |
| External (externo) customer with charge_to_room=1 | OK | 0 |
| paid=1 with no payment_method set | OK | 0 |
| Furniture blocks overlapping active reservations | FAIL | 5 |
| Future reservations with releasing state (informational) | WARN | 118 |

### Furniture blocks overlapping active reservations

- block_id=22 (maintenance) on furniture_id=62 overlaps ticket=26032640 on 2026-03-26
- block_id=22 (maintenance) on furniture_id=62 overlaps ticket=26032640-1 on 2026-03-27
- block_id=22 (maintenance) on furniture_id=62 overlaps ticket=26032640-2 on 2026-03-28
- block_id=22 (maintenance) on furniture_id=62 overlaps ticket=26032640-3 on 2026-03-29
- block_id=22 (maintenance) on furniture_id=62 overlaps ticket=26032640-4 on 2026-03-30

### Future reservations with releasing state (informational)

- ticket=26030112 on 2026-03-01 (Cancelada)
- ticket=26030133 on 2026-03-01 (Cancelada)
- ticket=26030142 on 2026-03-01 (Cancelada)
- ticket=26030149 on 2026-03-01 (Liberada)
- ticket=26030162 on 2026-03-01 (Cancelada)

## Performance

| Check | Severity | Issues |
|-------|----------|--------|
| Availability check (furniture conflicts for a date) | OK | 2 |
| Reservation list with customer join (last 30 days) | OK | 2664 |
| Map load (all active furniture with today assignments) | OK | 80 |
| Customer search (name LIKE) | OK | 2 |
| Daily report aggregation (reservations by date) | OK | 2 |
| Audit log recent entries | OK | 67 |
