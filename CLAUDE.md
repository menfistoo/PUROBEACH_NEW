# Beach Club Management System

## Overview
Sistema profesional de gestión y reservas de beach club. Gestiona hamacas/balinesas, clientes internos (huéspedes) y externos, reservas multi-día, precios diferenciados, estados configurables, y mapa interactivo con disponibilidad en tiempo real.

## Tech Stack
- **Backend:** Flask 3.0+ (Python 3.11+), SQLite 3 (WAL mode)
- **Architecture:** Modular blueprints
- **Auth/Security:** Flask-Login, Flask-WTF CSRF, role-based permissions
- **Frontend:** Jinja2, Bootstrap 5, FontAwesome 6, JavaScript ES6+
- **Export:** openpyxl (Excel), ReportLab (PDF)

## Language Convention

**CRITICAL: Code in English, UI in Spanish**

- **Code (English):** Variables, functions, classes, comments, docstrings, database columns
- **UI (Spanish):** Labels, buttons, messages, errors, menus, tooltips, placeholders

```python
# Correct examples:
def get_active_reservations(date: str) -> list:  # English function
    pass

flash('Reserva creada exitosamente', 'success')  # Spanish message

# Database columns in English:
# first_name, last_name, customer_type, room_number
```

## Project Structure

```
beach_club/
├── app.py                      # Flask app factory (~100 lines)
├── config.py                   # Configuration classes
├── extensions.py               # Flask extensions
├── database.py                 # Database connection & functions
│
├── blueprints/
│   ├── auth/                   # Authentication
│   ├── admin/                  # Users, roles, permissions
│   ├── beach/                  # Main beach club module
│   │   ├── routes/
│   │   │   ├── map.py
│   │   │   ├── reservations.py
│   │   │   ├── customers.py
│   │   │   ├── infrastructure.py
│   │   │   └── reports.py
│   │   └── services/
│   │       ├── reservation_service.py
│   │       ├── availability_service.py
│   │       ├── customer_service.py
│   │       └── suggestion_service.py
│   └── api/                    # REST API endpoints
│
├── models/                     # Database queries
├── utils/
│   ├── decorators.py           # @login_required, @permission_required
│   ├── permissions.py          # Permission checking & caching
│   ├── cache.py                # TTL caching
│   ├── validators.py           # Input validation
│   └── messages.py             # Spanish UI messages (centralized)
│
├── templates/
├── static/
├── tests/
│
├── docs/
│   └── DEVELOPMENT_PLAN.md     # Living document for plans & decisions
│
├── code-review/                # Code review standards
├── security-review/            # Security review standards
└── design-review/              # Design review standards
```

## Code Conventions

### Python
- **Indentation:** 4 spaces
- **Type hints:** Required for function signatures
- **Docstrings:** Required for public functions
- **DB transactions:** `with get_db() as conn:`
- **Multi-step ops:** Use `BEGIN IMMEDIATE`
- **SQL:** Always parameterized queries (never f-strings)

### Naming
- **Tables:** plural, snake_case with prefix (`beach_*`)
- **Columns:** snake_case, English
- **Functions:** verb_noun (`get_all_customers`, `create_reservation`)
- **Routes:** kebab-case URLs (`/beach/admin/furniture-types`)
- **Permissions:** module.feature.action (`beach.reservations.create`)

### Security Checklist
- ✓ CSRF tokens on all forms
- ✓ `@login_required` on protected routes
- ✓ `@permission_required` for granular access
- ✓ Parameterized SQL queries
- ✓ No PII in logs
- ✓ Rate limiting on login (5/min)
- ✓ Session timeout (8h)

### Code Maintainability

**CRITICAL: Avoid monolithic files. Keep code modular and maintainable.**

#### File Size Limits
- **Target:** ~300-500 lines per module
- **Warning:** >600 lines - consider splitting
- **Critical:** >800 lines - must refactor before adding more code

#### Module Organization Pattern
When a file grows too large, split by responsibility:
```
models/
├── reservation.py           # Re-exports for backward compatibility
├── reservation_crud.py      # Create, read, update, delete
├── reservation_state.py     # State transitions and logic
└── reservation_queries.py   # Listing, filtering, statistics
```

#### Splitting Guidelines
1. **By responsibility:** CRUD, queries, state management, utilities
2. **By domain:** Keep related functions together
3. **Backward compatible:** Use re-exports in main module
4. **Clear sections:** Use header comments to organize within files

```python
# =============================================================================
# SECTION NAME
# =============================================================================
```

#### Proactive Maintenance
- Split files **before** they become problematic
- When adding new functionality, check if file is approaching limits
- Prefer multiple focused modules over one large file
- Each module should have a single, clear purpose

#### Foreign Key Cascades
Always verify CASCADE behavior when creating relationships:
```sql
-- Tables with user data should CASCADE on delete
REFERENCES parent_table(id) ON DELETE CASCADE

-- If no CASCADE, handle in application code before delete
```

## Database Schema Summary

### Core Tables (22 total)
1. **users** - System users with role_id
2. **roles** - System and custom roles
3. **permissions** - Granular permissions with menu support
4. **role_permissions** - M2M role-permission assignments
5. **beach_zones** - Hierarchical zones
6. **beach_furniture_types** - Hamaca, balinesa, etc.
7. **beach_furniture** - Individual furniture items with position
8. **hotel_guests** - PMS integration via Excel import
9. **beach_customers** - Interno/externo customers
10. **beach_tags** - Customer/reservation tags
11. **beach_customer_tags** - M2M
12. **beach_preferences** - Customer preferences
13. **beach_customer_preferences** - M2M
14. **beach_reservation_states** - Configurable states
15. **beach_reservations** - Main reservations
16. **beach_reservation_furniture** - Per-day furniture assignments
17. **beach_reservation_daily_states** - Per-day states
18. **beach_reservation_tags** - M2M
19. **beach_price_catalog** - Pricing rules
20. **beach_minimum_consumption_policies** - Minimum spend rules
21. **beach_config** - System configuration
22. **audit_log** - Action audit trail

### Key Indexes
- `idx_res_furniture_date` - (assignment_date, furniture_id)
- `idx_reservations_dates` - (start_date, end_date)
- `idx_hotel_guests_room` - (room_number)
- `idx_permissions_menu` - (is_menu_item) WHERE is_menu_item = 1

## Critical Business Logic

### Customer Types
- **Interno:** Hotel guest, requires room_number, internal pricing
- **Externo:** External visitor, requires email/phone, external pricing
- **Deduplication:** phone + room (interno) / phone + name (externo)

### Reservation States
States with `is_availability_releasing` flag:
- Releasing (frees furniture): Cancelada, No-Show, Liberada
- Non-releasing: Pendiente, Confirmada, Check-in, Activa, Completada

### Multi-day Reservations
- Parent/child via `parent_reservation_id`
- Furniture assignments per day in `beach_reservation_furniture`
- Daily states in `beach_reservation_daily_states`

### Furniture Suggestions Algorithm
Weighted scoring: **40% contiguity + 35% preferences + 25% capacity**
- Contiguity: Groups sit together (no gaps with occupied furniture)
- Preferences: Match customer preferences to furniture features
- Capacity: Penalize over/under-capacity

### Hotel Guests Integration
- Excel import from PMS (auto-detect column mappings)
- Room number lookup for interno customer auto-fill
- Upsert based on (room_number, arrival_date)

## Development Workflow

### Before Starting Any Task
1. Check `docs/DEVELOPMENT_PLAN.md` for current phase and pending items
2. Update the plan with your intended work
3. Follow the phased implementation order

### After Completing Work
1. Update `docs/DEVELOPMENT_PLAN.md` with:
   - Completed items
   - Any decisions made
   - New discoveries or issues
   - Next steps
2. Run tests: `python -m pytest`
3. Check for security issues if touching auth/data

### Reviews
- **QA Router:** `/qa` - Auto-detects changed files and runs appropriate reviews
- **Code Simplifier:** `/simplify` - Simplifies complex code
- **Code Standards:** `/code-standards` - Check CLAUDE.md compliance
- **Security Review:** `/security-review` for auth/data changes
- **Design Review:** `/design-review` for reviewing UI changes
- **Frontend Design:** `/frontend-design` for creating/editing UI (MUST use before any UI work)

## Quick Reference

### Start Dev Server
```bash
python app.py
```

### Run Tests
```bash
python -m pytest                    # All tests
python -m pytest tests/unit/        # Unit tests only
python -m pytest -x                 # Stop on first failure
```

### Common Endpoints
- `/` - Login
- `/beach/map` - Interactive map
- `/beach/reservations` - Reservations list
- `/beach/customers` - Customer management
- `/beach/config` - Configuration
- `/admin/users` - User management
- `/admin/roles` - Role & permission management
- `/admin/hotel-guests` - Hotel guest import

### Default Roles
- **admin** - Full access (bypass permission checks)
- **manager** - Beach club management
- **staff** - Daily operations
- **readonly** - View only

## Maintaining This File

### When to Update CLAUDE.md
- Adding/modifying database tables
- Creating new routes/endpoints
- Changing code conventions
- Adding configurations
- Architectural changes

### Update Format
```
SECTION: "Database Schema"
CHANGE: Add "23. beach_waitlist"
REASON: New waitlist feature
```

---

## Design System

**CRITICAL:** Before creating or editing ANY UI elements, run `/frontend-design` to load design guidelines.

**Reference:** See `DESIGN_SYSTEM.md` for complete specifications:
- Color palette, typography, spacing
- Component patterns (buttons, cards, forms, tables, modals)
- Beach map styles (furniture states, zones)
- Reservation state colors
- CSS variables and Bootstrap 5 integration

---

## GitHub Issues (Proactive)

**CRITICAL: Proactively use GitHub Issues to track bugs, features, and ideas WITHOUT waiting for user commands.**

### When to Create Issues Automatically
| Situation | Action |
|-----------|--------|
| User mentions a bug while testing | Create issue with `bug` label |
| User describes a feature idea | Create issue with `feature,planning` labels |
| I discover a bug while working | Create issue with `bug` label |
| User says "we should add X later" | Create issue with `planning` label |
| Task is deferred for later | Create issue to track it |

### Labels
| Label | Color | Use For |
|-------|-------|---------|
| `bug` | red | Something broken |
| `feature` | #1A3A5C | New functionality |
| `enhancement` | cyan | Improvements to existing |
| `planning` | #D4AF37 | Future ideas, not urgent |
| `map` | #4A7C59 | Live map related |
| `reservations` | #6B8E23 | Reservations system |
| `customers` | #708090 | Customer management |
| `pricing` | #E5A33D | Pricing and payments |
| `priority:high` | #C1444F | Urgent |
| `priority:low` | #F5E6D3 | Nice to have |

### Commands
```bash
# Create issue
gh issue create -t "Title" -b "Description" -l "label1,label2"

# List issues
gh issue list
gh issue list -l "planning"    # By label
gh issue list -s closed        # Closed issues

# View/close
gh issue view 123
gh issue close 123
```

### Commit Integration
- `Fixes #123` in commit message → auto-closes issue
- `Relates to #123` → links without closing

### Web Access
https://github.com/menfistoo/PUROBEACH_NEW/issues

---

## Demo Roadmap

**CRITICAL: `docs/DEMO_ROADMAP.md` is the active roadmap for demo preparation.**
- Must be updated after every work session
- Contains all known issues organized by priority (Phase 1-4)
- Tracks fix status with checkboxes
- **Always check this file before starting any work session**

---

## Extended Documentation

- **Demo Roadmap:** `docs/DEMO_ROADMAP.md` **(ACTIVE - update after every session)**
- **GitHub Issues:** https://github.com/menfistoo/PUROBEACH_NEW/issues
- **Design System:** `DESIGN_SYSTEM.md` (colors, typography, components)
- **Development Plan:** `docs/DEVELOPMENT_PLAN.md` (living document)
- **Code Review Standards:** `code-review/README.md`
- **Security Review Standards:** `security-review/README.md`
- **Design Review Standards:** `design-review/README.md`
- **Bootstrap Prompt:** `BEACH_CLUB_NEW_PROJECT_PROMPT.md`
