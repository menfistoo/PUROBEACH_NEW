# Demo Roadmap - PuroBeach Beach Club

> **IMPORTANT: This file must be kept updated.** After every work session, update the status
> of completed items and add any new issues discovered. This is the single source of truth
> for demo preparation progress.
>
> **Last Updated:** 2026-02-02

---

## Overall Status: IN PROGRESS

| Phase | Status | Items | Done |
|-------|--------|-------|------|
| Phase 1 - Critical | COMPLETED | 6 | 6/6 |
| Phase 2 - High | COMPLETED | 5 | 5/5 |
| Phase 3 - Polish | COMPLETED | 4 | 4/4 |
| Phase 4 - Nice to Have | PENDING | 6 | 0/6 |

---

## Phase 1 - CRITICAL (Must fix before ANY demo)

### 1.1 [x] Fix 10 API endpoints returning 302 instead of 200
- **Priority:** BLOCKER
- **Files:** `utils/decorators.py`, API route files
- **Symptom:** `@permission_required` decorator redirects authenticated API requests instead of returning JSON
- **Affects:**
  - Analytics/Insights: 6 endpoints (`/beach/api/insights/*`)
  - Furniture Lock: 2 endpoints (`toggle-lock`)
  - Move Mode: 2 endpoints (`assign`, `unassign`)
- **Tests failing:** `test_insights.py` (6), `test_furniture_lock.py` (2), `test_move_mode.py` (2)
- **Demo impact:** Analytics dashboard blank, cannot lock/move furniture

### 1.2 [x] Fix bare except clauses in app.py
- **Priority:** HIGH
- **Files:** `app.py` lines ~293-305
- **Symptom:** `except:` catches ALL exceptions silently in template filters
- **Fix:** Replace with `except (ValueError, TypeError):` or specific exceptions
- **Demo impact:** Errors invisible, corrupted data shown without warning

### 1.3 [x] Fix silent pricing failure in reservation creation
- **Priority:** HIGH
- **Files:** `blueprints/beach/routes/api/map_res_create.py` lines ~201-203
- **Symptom:** If pricing calculation fails, reservation created at EUR 0.00 silently
- **Fix:** Return error to user or set a warning flag on the reservation
- **Demo impact:** "Why are all reservations free?"

### 1.4 [x] Add input validation on API JSON payloads
- **Priority:** HIGH
- **Files:** `blueprints/beach/routes/api/map_res_create.py` and other API routes
- **Symptom:** No validation on date format, data types, null values, negative numbers
- **Fix:** Add validation layer for all JSON inputs
- **Demo impact:** Malformed data causes crashes or invalid reservations

### 1.5 [x] Add transaction locks for multi-day reservations
- **Priority:** HIGH
- **Files:** `models/reservation_multiday.py`, `models/reservation_crud.py`
- **Symptom:** No `BEGIN IMMEDIATE` between availability check and creation
- **Fix:** Wrap multi-step operations in explicit transactions
- **Demo impact:** Overbooking possible with concurrent requests

### 1.6 [x] Verify API health endpoint exists
- **Priority:** MEDIUM
- **Files:** `blueprints/api/routes.py`
- **Symptom:** Dockerfile healthcheck calls `/api/health` - must verify it exists
- **Fix:** Create endpoint if missing
- **Demo impact:** Docker thinks app is unhealthy

---

## Phase 2 - HIGH (Polished demo)

### 2.1 [x] Implement basic Excel export for reservations
- **Priority:** HIGH
- **Files:** `blueprints/beach/routes/reports/`, models
- **Symptom:** Export functionality referenced in UI but not implemented (stubs only)
- **Fix:** Implement basic Excel export using openpyxl (already in requirements)
- **Demo impact:** Cannot export any data

### 2.2 [x] Add state transition validation
- **Priority:** HIGH
- **Files:** `models/reservation_state.py`
- **Symptom:** No validation prevents invalid transitions (e.g., Completada -> Pendiente)
- **Fix:** Define valid transition matrix and enforce
- **Demo impact:** Reservations in impossible states

### 2.3 [x] Consistent API response format
- **Priority:** MEDIUM
- **Files:** All API routes
- **Symptom:** Some return `{success, error}`, others `{error}`, others `{data, status}`
- **Fix:** Standardize all responses to `{success: bool, data?: any, error?: string}`
- **Demo impact:** Frontend error handling unreliable

### 2.4 [x] Add loading states on buttons
- **Priority:** MEDIUM
- **Files:** JS files, templates
- **Symptom:** No visual feedback when operations are in progress
- **Fix:** Disable button + spinner while AJAX calls run
- **Demo impact:** Users click multiple times, duplicate operations

### 2.5 [x] Hide canvas info bar on mobile
- **Priority:** MEDIUM
- **Files:** `static/css/map-page.css`, `templates/beach/map.html`
- **Symptom:** Canvas info bar takes 30% of mobile screen
- **Fix:** Hide or collapse on mobile breakpoints
- **Demo impact:** Map unusable on tablets (staff use case)

---

## Phase 3 - POLISH

### 3.1 [ ] Normalize phone numbers for customer deduplication
- **Files:** `models/customer_crud.py`, `models/customer_queries.py`
- **Symptom:** "+34 666-123-456" and "666123456" create duplicates

### 3.2 [ ] Replace browser confirm() with modals
- **Files:** JS files using `confirmDelete()`
- **Symptom:** Native browser dialogs look unprofessional

### 3.3 [ ] Add empty states with helpful messages
- **Files:** Templates for lists, map
- **Symptom:** Empty lists show nothing, no guidance

### 3.4 [ ] Remove backup files from repo
- **Files:** `templates/beach/reservation_form.html.BACKUP_*`
- **Symptom:** Backup files shouldn't be in version control

---

## Phase 4 - NICE TO HAVE

### 4.1 [ ] Bundle/minify CSS and JS assets
- 14 CSS + 71 JS files loaded on map page

### 4.2 [ ] Add print styles for reports
- No print CSS exists

### 4.3 [ ] Improve mobile touch interactions
- Hover menus don't work on touch devices

### 4.4 [ ] Add timezone awareness
- Uses naive `date.today()` without TZ

### 4.5 [ ] Add pagination to list API endpoints
- All records returned at once, no limit/offset

### 4.6 [ ] Cleanup dual reservation panel (v1 vs v2)
- Both systems loaded simultaneously, wasted bandwidth

---

## Known Strengths (Do NOT break these)

- Modular blueprint architecture
- Database schema well-designed (22 tables, proper FKs, indexes)
- Security: CSRF, bcrypt, parameterized SQL, rate limiting
- Design system: Professional Mediterranean theme
- Demo seed script: Creates realistic data (~80 furniture, ~50 reservations)
- Docker deployment: Dockerfile, nginx, gunicorn, SSL
- Interactive map: Core feature works (zoom, pan, drag, context menu)

---

## Demo Seed Data Checklist

Run `python scripts/demo_seed.py` to populate:
- [x] 2 zones (Pool Club, Terraza Sur)
- [x] ~80 furniture pieces
- [x] ~40 diverse customers
- [x] ~50 multi-day reservations
- [x] Pricing and configuration data
- [x] Reservation states
- [x] Furniture types

---

## Pre-Demo Verification Steps

```bash
# 1. Fresh database
python -c "from database.schema import init_db; init_db()"

# 2. Run seed
python scripts/demo_seed.py

# 3. Run tests
python -m pytest tests/ -x --tb=short

# 4. Start server
python app.py

# 5. Manual checks:
# - Login as admin/admin123
# - View map with furniture
# - Create reservation
# - Check analytics dashboard
# - Lock/unlock furniture
# - Move mode test
```
