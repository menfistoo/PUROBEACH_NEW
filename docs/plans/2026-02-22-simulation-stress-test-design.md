# Simulation Stress Test Design

**Date:** 2026-02-22
**Branch:** `simulation/stress-test-2026-02`
**Approach:** Option B — Simulation + automated health-check script

---

## Goal

Run a realistic one-month simulation at 80-100% occupancy and programmatically detect potential flaws across data integrity, business logic, and performance.

---

## Section 1 — Branch & Database Setup

- New branch: `simulation/stress-test-2026-02`
- Copy `database/beach_club.db` → `database/beach_club_sim.db`
- Both scripts accept a `--sim-db` flag to target `beach_club_sim.db`
- Add `beach_club_sim.db` to `.gitignore` — never committed

---

## Section 2 — Simulation Script Changes

Minimal changes to `scripts/simulate_month.py`:

- Add `--high-occupancy` flag: overrides `WEEKLY_OCCUPANCY` with flat `(80, 100)` every day
- Weekdays: `(80, 100)`, Weekends: `(95, 100)`
- Add `--month YYYY-MM` as a cleaner alternative to `--start-date`
- Add `--sim-db` flag to point at `beach_club_sim.db`
- All existing logic unchanged

---

## Section 3 — Health Check Script (`scripts/health_check.py`)

New script. Runs after simulation. Checks 4 categories:

### 3.1 Data Integrity
- Double-bookings: same furniture on same date in 2+ active reservations
- Orphaned `beach_reservation_furniture` rows (no parent reservation)
- Missing `beach_reservation_daily_states` entries
- Multi-day parent/child consistency (parent exists, child count matches date range)

### 3.2 Business Logic
- Invalid states for date context (e.g. `Sentada` on past dates)
- Availability conflicts (furniture available flag vs. active reservation)
- Pricing anomalies (`paid=1` with no `payment_method`, `charge_to_room=1` on `externo`)
- Furniture blocks overlapping active reservations

### 3.3 Performance
- Times 6 key queries: availability check, reservation list, map load, customer search, reports, audit log
- Warning threshold: >500ms
- Critical threshold: >2000ms

### 3.4 Report Output
- Terminal: summary table (category → pass/warn/fail + issue count)
- File: `docs/simulation-report-YYYY-MM-DD.md` with full per-issue details

---

## Section 4 — Execution Flow

```bash
# 1. Create branch
git checkout -b simulation/stress-test-2026-02

# 2. Copy production DB
cp database/beach_club.db database/beach_club_sim.db

# 3. Preview (dry run)
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db --dry-run

# 4. Run simulation
python scripts/simulate_month.py --high-occupancy --month 2026-03 --sim-db

# 5. Analyze
python scripts/health_check.py --sim-db

# 6. Review report
# docs/simulation-report-YYYY-MM-DD.md
```

---

## Out of Scope

- No changes to `main` branch
- `beach_club_sim.db` never committed
- Branch archived or deleted after findings are turned into GitHub Issues
