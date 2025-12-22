# Beach Club Development Plan

> **LIVING DOCUMENT**: This file tracks all development phases, decisions, and progress.
> Update this file after every work session to preserve context across conversations.

---

## Current Status

| Field | Value |
|-------|-------|
| **Current Phase** | Phase 8: Smart Features |
| **Last Updated** | 2025-12-22 |
| **Last Session** | Phase 7 Interactive Map Editor (Complete) |
| **Next Priority** | Phase 8 Smart features OR Phase 7B Live Map with availability |

---

## Phase Overview

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 1 | Foundation | Complete | 100% |
| 2 | Core Admin | Complete | 100% |
| 3 | Hotel Guests Integration | Complete | 100% |
| 4 | Beach Infrastructure | Complete | 100% |
| 4.5 | Enhanced Furniture Types | Complete | 100% |
| 4.6 | Enhanced Furniture Management | Complete | 100% |
| 5 | Customers | Complete | 100% |
| 6A | Reservations: Core CRUD + States | Complete | 100% |
| 6B | Reservations: Availability + Multi-day + Suggestions | Complete | 100% |
| 6C | Sentada State + Customer Stats | Complete | 100% |
| 6D | Configurable Reservation States | Complete | 100% |
| 7A | Interactive Map Editor | Complete | 100% |
| 7B | Live Map with Availability | Not Started | 0% |
| 8 | Smart Features | Not Started | 0% |
| 9 | Reports & Polish | Not Started | 0% |

---

## Phase 1: Foundation

### Objectives
- [x] Project structure created
- [x] Flask app factory pattern
- [x] Database schema implemented
- [x] Base templates with Bootstrap 5
- [x] Auth blueprint (login/logout)

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Create folder structure | Pending | |
| Create `app.py` with factory pattern | Pending | |
| Create `config.py` | Pending | Dev/Prod/Test configs |
| Create `extensions.py` | Pending | Flask extensions init |
| Create `database.py` | Pending | Connection + init_db() |
| Run initial migration | Pending | All 22 tables |
| Create `templates/base.html` | Pending | Bootstrap 5 + navbar |
| Create auth blueprint | Pending | Login, logout, profile |
| Create login page | Pending | Spanish UI |
| Test login flow | Pending | |

### Decisions Made
- (None yet)

### Issues Discovered
- (None yet)

---

## Phase 2: Core Admin

### Objectives
- [x] User CRUD
- [x] Role & permission management
- [x] Permission-based menu generation
- [x] Audit logging

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Create admin blueprint | Complete | |
| User list page | Complete | With filters |
| User create/edit forms | Complete | |
| Role management page | Complete | |
| Permission assignment UI | Complete | Checkbox grid |
| Dynamic menu from permissions | Complete | Sidebar component |
| Audit log table + functions | Complete | |
| Seed default roles/permissions | Complete | ~35 permissions |

### Decisions Made
- (None yet)

### Issues Discovered
- (None yet)

---

## Phase 3: Hotel Guests Integration

### Objectives
- [x] Excel import functionality
- [x] Hotel guests list with filters
- [x] Room number lookup API
- [x] Hierarchical menu structure

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Excel upload endpoint | Complete | POST /admin/hotel-guests/import |
| Column auto-detection | Complete | Spanish headers (Nombre, Apellidos, Háb., etc.) |
| Import logic with upsert | Complete | Unique key: room_number + arrival_date |
| Hotel guests list page | Complete | With search, room filter, active toggle |
| Filter by room/name/dates | Complete | Real-time filtering |
| Room lookup API endpoint | Complete | /api/hotel-guests/preview for validation |
| Guest detail view | Complete | Individual guest information |
| Delete guest functionality | Complete | Soft delete with confirmation |
| Hierarchical menu | Complete | Collapsible parent/child structure |

### Decisions Made
- Used openpyxl for Excel parsing with auto-detect header row
- Implemented upsert based on (room_number, arrival_date) as unique key
- Spanish column mapping: Nombre→first_name, Apellidos→last_name, Háb.→room_number
- Hierarchical menu with 4 parent sections: Administración, Configuración, Operaciones, Informes
- Bootstrap 5 collapse for submenu toggles

### Issues Discovered
- SQLite partial index with `date("now")` causes non-deterministic error → Removed WHERE clause
- Flask-WTF CSRF not initialized → Added CSRFProtect to extensions.py
- Windows file locking on temp Excel files → Added retry loop with time.sleep(0.1)
- Database doesn't auto-initialize on first run → Manual init_db() required

---

## Phase 4: Beach Infrastructure

### Objectives
- [x] Zones management
- [x] Furniture types
- [x] Furniture CRUD with positioning
- [x] Preferences & tags

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Zones CRUD | Complete | Hierarchical with parent_zone_id |
| Furniture types CRUD | Complete | With capacity, icon, color |
| Furniture list/grid view | Complete | With zone/type filters |
| Furniture positioning | Complete | x, y, rotation, width, height |
| Preferences management | Complete | With maps_to_feature for suggestions |
| Tags management | Complete | Color picker, used for customers/reservations |
| Feature mapping | Complete | Preference -> furniture feature mapping |

### Decisions Made
- Config routes under `/beach/config/*` sub-blueprint
- Furniture types as separate CRUD (not just a dropdown)
- Preferences map to furniture features via `maps_to_feature` field
- Tags shared between customers and reservations

### Issues Discovered
- None

---

## Phase 4.5: Enhanced Furniture Types

### Objectives
- [x] SVG-based visual representation for map
- [x] Auto-numbering system with prefixes
- [x] Decorative vs operative element classification
- [x] Two-panel UI with real-time SVG preview
- [x] Drag-drop reordering with Sortable.js

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Database migration (5 columns) | Complete | number_start, default_features, allowed_zones, display_order |
| Model functions (4 new) | Complete | SVG generation, numbering, validation, reorder |
| Routes update (4 new endpoints) | Complete | preview, next-number, reorder, delete |
| Two-panel template | Complete | 30% list + 70% form with drag-drop |
| SVG preview component | Complete | Single preview with fill_color |
| Form partial template | Complete | 6 collapsible sections |
| Jinja from_json filter | Complete | Added to app.py |

### Decisions Made
- Kept existing `is_suite_only` and added separate `is_decorative` flag
- Used existing DB column names (`map_shape`, `stroke_color`) instead of renaming
- **IMPORTANT: Status colors are NOT per furniture type** - they come from reservation states config (ADR-006)
- `number_prefix` for auto-numbering (e.g., H1, H2 for hamacas, B1, B2 for balinesas)
- Sortable.js (CDN) for drag-drop reordering
- SVG preview shows single shape with fill_color (state colors shown on map only)

### Issues Discovered
- Database already had some columns with different names than planned (map_shape vs svg_shape_type)
  - Resolution: Adapted to existing column names, added only missing columns
- Initial design had status_colors per furniture type - INCORRECT
  - Resolution: Removed status_colors from furniture types; colors come from beach_reservation_states

---

## Phase 4.6: Enhanced Furniture Management

### Objectives
- [x] Sequential auto-numbering based on furniture type prefix
- [x] Default zone selection
- [x] Live preview with real-time updates
- [x] Horizontal text in rotated elements
- [x] Duplication functionality in create mode
- [x] Duplication functionality in edit mode
- [x] Sequential numbering by prefix (not just type)

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Auto-number on type selection | Complete | Fetches next number via AJAX |
| Default zone selection | Complete | First zone auto-selected |
| Live preview updates | Complete | Position, size, rotation, color, number |
| Text always horizontal | Complete | Counter-rotation on text span |
| Duplication fields (copies, layout, spacing) | Complete | Horizontal/vertical with configurable spacing |
| Duplication in create mode | Complete | Creates multiple elements at once |
| Duplication in edit mode | Complete | "Duplicate" button creates copies |
| Sequential numbering by prefix | Complete | get_next_number_by_prefix() function |

### Decisions Made
- Duplication creates new elements starting from current position + spacing
- In edit mode, "Duplicate" button is separate from "Save" button
- Numbering follows the prefix pattern (B1→B5, not B1_1)
- Live preview limited to 10 items for performance

### Issues Discovered
- Template block mismatch: `{% block scripts %}` vs `{% block extra_js %}`
  - Resolution: Changed to `{% block extra_js %}` to match base.html
- Event listeners not registering for duplication fields
  - Resolution: Added both 'input' and 'change' events, explicit element checks
- Jinja2 attribute access with dict: `t.id` not working
  - Resolution: Changed to `t['id']` syntax

---

## Phase 5: Customers

### Objectives
- [x] Customer CRUD (interno/externo)
- [x] Integration with hotel guests
- [x] Deduplication logic
- [x] Customer merge functionality
- [x] Customer preferences assignment
- [ ] Bidirectional sync with reservations (Phase 6)

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Customer list with filters | Complete | Type, VIP, search with stats cards |
| Customer create form | Complete | Interno/externo tabs with pill navigation |
| Hotel guest auto-fill | Complete | Room number lookup via AJAX |
| Customer edit form | Complete | Reuses same template as create |
| Customer detail view | Complete | Full profile with preferences, tags, reservations |
| Deduplication check | Complete | Real-time on phone/room change |
| Customer merge UI | Complete | Source/target selection with search |
| Merge logic | Complete | Transfers reservations, prefs, tags |
| Customer search API | Complete | /beach/api/customers/search |
| Customer preferences UI | Complete | Checkbox selection in form |
| beach_customer_preferences M2M | Complete | Already existed in model |
| Hotel guest lookup API | Complete | /beach/api/hotel-guests/lookup |
| Sync prefs from reservation | Phase 6 | Will implement with reservations |
| Load customer prefs | Phase 6 | Will implement with reservations |
| Preference history | Future | Track when prefs added/removed |

### Decisions Made
- Customer form uses Bootstrap 5 pill tabs for interno/externo selection
- Hotel guest auto-fill parses guest_name into first_name/last_name
- Duplicate detection happens in real-time via AJAX and on form submit
- Customer merge transfers all related data then deletes source customer
- Stats cards show total, interno, externo, VIP counts

### Issues Discovered
- Template needed conditional check for stats variable (fixed with `{% if stats %}`)

---

## Phase 6: Reservations

> **Full specification:** See `docs/RESERVATIONS_SYSTEM_SPEC.md` for complete details

### Objectives
- [ ] Reservation CRUD with SPEC schema
- [ ] Ticket number generation (YYMMDDRR format)
- [ ] Multi-state management (CSV-based)
- [ ] Multi-day parent/child reservations
- [ ] Availability checking with releasing states
- [ ] Furniture suggestions with scoring algorithm
- [ ] Price validation (anti-fraud)
- [ ] PMS integration for consumption tracking

---

### Phase 6A: Core CRUD + State Management

| Task | Status | Notes |
|------|--------|-------|
| **Customer Section Enhancements** | Complete | Reservation form customer section |
| - Unified customer/hotel guest search | Complete | Accent-insensitive, multi-word |
| - Customer notes & preferences display | Complete | Show in reservation form |
| - Profile link button | Complete | Quick access to full details |
| - Customer stats (language, visits, spent) | Complete | Real-time display |
| - Check-in/check-out badges | Complete | Visual indicators in search |
| - Hide expired hotel stays | Complete | Filter interno customers after checkout |
| - Single guest per room in search | Complete | Show main guest + count |
| **Database & Model Layer** | Complete | Core reservation infrastructure |
| - DB migration (SPEC columns) | Complete | ticket_number, current_states, pricing fields |
| - generate_reservation_number() | Complete | Atomic YYMMDDRR format with retries |
| - generate_child_reservation_number() | Complete | Parent-N format for multi-day |
| - create_beach_reservation() | Complete | Full creation with furniture assignment |
| - get/update/delete functions | Complete | Basic CRUD operations |
| - add_reservation_state() | Complete | CSV accumulative state management |
| - remove_reservation_state() | Complete | Remove from CSV, recalculate priority |
| - change_reservation_state() | Complete | Replace current state |
| - cancel_beach_reservation() | Complete | Shortcut to add Cancelada state |
| - calculate_reservation_color() | Complete | Priority-based color selection |
| - get_active_releasing_states() | Complete | States that free availability |
| - sync_preferences_to_customer() | Complete | Bidirectional preference sync |
| - update_customer_statistics() | Complete | Auto-update visits on state change |
| - get_status_history() | Complete | State change audit trail |
| **Routes & Templates** | Complete | Connect frontend to backend |
| - Reservation list route | Complete | GET /beach/reservations with filters |
| - Reservation create route | Complete | GET/POST /beach/reservations/create |
| - Reservation detail route | Complete | GET /beach/reservations/<id> |
| - Reservation edit route | Complete | GET/POST /beach/reservations/<id>/edit |
| - Reservation delete route | Complete | POST /beach/reservations/<id>/delete |
| - Reservation cancel route | Complete | POST /beach/reservations/<id>/cancel |
| - State toggle API | Complete | POST /beach/api/reservations/<id>/toggle-state |
| - Status history API | Complete | GET /beach/api/reservations/<id>/history |
| - Available furniture API | Complete | GET /beach/api/furniture/available |
| - Templates | Complete | reservations.html, reservation_form.html, reservation_detail.html |

---

### Phase 6B: Availability + Multi-day + Suggestions

| Task | Status | Notes |
|------|--------|-------|
| **Module 1: Bulk Availability** | Complete | `reservation_availability.py` |
| check_furniture_availability_bulk() | Complete | Multiple furniture/dates check |
| check_duplicate_reservation() | Complete | Same customer + date overlap detection |
| get_furniture_availability_map() | Complete | Calendar view support |
| get_conflicting_reservations() | Complete | Get blocking reservations |
| **Module 2: Multi-day Reservations** | Complete | `reservation_multiday.py` |
| create_linked_multiday_reservations() | Complete | Parent/child creation with YYMMDDRR-N tickets |
| update_multiday_reservations() | Complete | Update all linked reservations |
| cancel_multiday_reservations() | Complete | Cancel entire group |
| get_multiday_summary() | Complete | Get group overview |
| is_parent_reservation() | Complete | Check if has children |
| get_child_reservations() | Complete | Get all children |
| **Module 3: Smart Suggestions** | Complete | `reservation_suggestions.py` |
| build_furniture_occupancy_map() | Complete | Spatial mapping by rows (±30px tolerance) |
| validate_cluster_contiguity() | Complete | Gap detection in selection |
| suggest_furniture_for_reservation() | Complete | Smart suggestions with weighted scoring |
| score_preference_match() | Complete | Preference scoring |
| get_customer_preferred_furniture() | Complete | History-based preferences |
| **API Endpoints** | Complete | All 11 endpoints implemented |
| POST /api/reservations/check-availability | Complete | Bulk availability check |
| POST /api/reservations/check-duplicate | Complete | Duplicate detection |
| GET /api/reservations/availability-map | Complete | Calendar availability |
| GET /api/reservations/conflicts | Complete | Get blocking reservations |
| POST /api/reservations/create-multiday | Complete | Multi-day creation |
| GET /api/reservations/<id>/multiday-summary | Complete | Group summary |
| POST /api/reservations/<id>/cancel-multiday | Complete | Cancel group |
| POST /api/reservations/<id>/update-multiday | Complete | Update group |
| POST /api/reservations/suggest-furniture | Complete | Smart suggestions |
| POST /api/reservations/validate-contiguity | Complete | Contiguity check |
| GET /api/customers/<id>/preferred-furniture | Complete | Customer history |
| POST /api/customers/create-from-guest | Complete | Convert hotel guest to customer |
| **Frontend Integration** | Complete | Reservation form enhancements |
| Duplicate detection warning | Complete | Alert when customer has existing reservation |
| Smart suggestions modal | Complete | Show weighted suggestions with scores |
| Contiguity validation warning | Complete | Warn when furniture not contiguous |
| Collapsible calendar picker | Complete | Multi-day date selection UI |

**Suggestion Algorithm Weights:**
- 40% Contiguity (no gaps between selected furniture)
- 35% Preference matching (customer prefs → furniture features)
- 25% Capacity fit (num_people vs furniture capacity)

---

### Phase 6C: Sentada State + Customer Statistics

**Note:** PMS integration deferred - prices are informational only for employees.

| Task | Status | Notes |
|------|--------|-------|
| migrate_add_sentada_state() | Complete | New state for tracking beach presence |
| migrate_customers_extended_stats() | Complete | Added no_shows, cancellations, total_reservations columns |
| Update seed_database() | Complete | Added 'Sentada' state to states_data |
| Update create_tables() | Complete | Added new columns to beach_customers |
| RESERVATION_STATE_DISPLAY_PRIORITY | Complete | Added Sentada at priority 6 |
| update_customer_statistics() | Complete | Calculates all extended stats on state changes |
| customer_crud.py allowed_fields | Complete | Added new stat fields |
| customer_detail.html | Complete | Display extended stats with icons |

**Customer Stats Auto-Update (Implemented):**
- total_reservations: Count excluding Cancelada and No-Show states
- total_visits: Reservations with 'Sentada' state
- no_shows: Reservations with 'No-Show' state
- cancellations: Reservations with 'Cancelada' state
- last_visit: Most recent 'Sentada' date

---

### Phase 6D: Configurable Reservation States

**Objective:** Fully dynamic reservation states managed from database with configuration UI.

| Task | Status | Notes |
|------|--------|-------|
| **Database Migration** | Complete | Added display_priority, creates_incident, is_system, is_default columns |
| migrate_reservation_states_configurable() | Complete | Idempotent migration with legacy state deactivation |
| Update seed_database() | Complete | 5 system states with proper properties |
| Update schema.py | Complete | New columns in beach_reservation_states |
| **Model Layer** | Complete | New models/state.py with full CRUD |
| get_all_states() | Complete | List states with active_only filter |
| get_state_by_id/code/name() | Complete | Lookup functions |
| get_default_state() | Complete | Returns state with is_default=1 |
| get_state_priority_map() | Complete | Dynamic priority lookup from DB |
| get_incident_states() | Complete | States with creates_incident=1 |
| get_releasing_states() | Complete | States with is_availability_releasing=1 |
| create_state() | Complete | Create non-system states |
| update_state() | Complete | Update with system field protection |
| delete_state() | Complete | Soft delete (active=0) |
| reorder_states() | Complete | Update display_order |
| **Refactored Hardcoded References** | Complete | All dynamic from DB |
| Remove RESERVATION_STATE_DISPLAY_PRIORITY | Complete | Replaced with get_state_priority_map() |
| reservation_crud.py | Complete | Uses get_default_state() |
| reservation_multiday.py | Complete | Uses get_default_state() |
| reservation_suggestions.py | Complete | Dynamic releasing states query |
| **Configuration UI** | Complete | Full CRUD interface |
| GET /config/states | Complete | List with show_inactive toggle |
| GET/POST /config/states/create | Complete | Create form with color picker |
| GET/POST /config/states/<id>/edit | Complete | Edit form |
| POST /config/states/<id>/delete | Complete | Soft delete |
| POST /config/states/reorder | Complete | AJAX reorder |
| states.html template | Complete | Table with centered columns |
| state_form.html template | Complete | Form with behavior switches |

**5 System States (Configured):**

| Estado | Color | Prioridad | Libera | Incidente | Default |
|--------|-------|-----------|--------|-----------|---------|
| Confirmada | #28A745 | 3 | No | No | Sí |
| Sentada | #2E8B57 | 6 | No | No | No |
| Cancelada | #DC3545 | 0 | Sí | No | No |
| No-Show | #FF4444 | 0 | Sí | Sí | No |
| Liberada | #6C757D | 0 | Sí | No | No |

**Key Properties:**
- `is_availability_releasing`: Furniture freed for new reservations
- `creates_incident`: Auto-log incident when state applied
- `is_system`: Cannot be deleted (protected)
- `is_default`: Auto-assigned to new reservations
- `display_priority`: Color precedence when multiple states

---

### Decisions Made
- **Schema approach:** Single `reservation_date` per reservation + parent/child for multi-day (SPEC approach)
- **Ticket number format:** YYMMDDRR (e.g., 25011601 = first reservation on Jan 16, 2025)
- **State management:** CSV in `current_states` field, priority-based `current_state` for display
- **Child numbering:** Parent ticket + suffix (-1, -2, etc.)
- Split Phase 6 into sub-phases for manageable implementation

### Issues Discovered
- Current schema uses start_date/end_date (different from SPEC)
  - Resolution: Will migrate to SPEC approach with new columns
- Phase 6 was incorrectly marked as Complete in previous version
  - Resolution: Reset all tasks to Pending

---

## Phase 7A: Interactive Map Editor

### Objectives
- [x] SVG-based beach map editor
- [x] Drag-and-drop furniture placement
- [x] Visual positioning tools (rulers, guides, snap-to-grid)
- [x] Furniture properties panel
- [x] Duplicate functionality

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Map editor container | Complete | Canvas with viewport, scroll, zoom |
| Zone rendering | Complete | Background color, dimensions from DB |
| Furniture rendering | Complete | SVG shapes from furniture types |
| Drag to reposition | Complete | With snap-to-grid |
| Click to select | Complete | Shows properties panel |
| Zoom controls | Complete | Ctrl+wheel zoom to mouse position |
| Pan controls | Complete | Space+drag or middle mouse |
| Rulers (H/V) | Complete | Pixel measurements, synced with scroll |
| Center guides | Complete | Crosshairs for alignment |
| Snap-to-grid | Complete | 10px, 25px, 50px options |
| Properties panel | Complete | Position, rotation, capacity, features |
| Furniture features | Complete | Tags from preferences table |
| Duplicate H/V | Complete | Multiple copies with spacing |
| Canvas bounds validation | Complete | Prevent elements outside canvas |
| Save/restore view | Complete | LocalStorage with memory fallback |
| Furniture numbering | Complete | Reuses gaps from deleted items |
| CSRF protection | Complete | Token in base template |

### Decisions Made
- SVG for furniture rendering, HTML5 Canvas considered for minimap (deferred)
- Zoom centered on mouse position for better UX
- Features loaded from beach_preferences table (maps_to_feature)
- Numbering finds first available gap instead of max+1

### Issues Discovered
- LocalStorage blocked by browser Tracking Prevention → Added memory fallback
- Horizontal panning blocked by CSS flex → Changed to overflow:scroll

---

## Phase 7B: Live Map with Availability

### Objectives
- [ ] Real-time availability display by date
- [ ] Reservation creation from map
- [ ] Reservation info on hover/click
- [ ] Date navigation

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Availability colors | Pending | Available/reserved/occupied states |
| Load reservations by date | Pending | API endpoint |
| Tooltip on hover | Pending | Reservation info |
| Quick reservation modal | Pending | From furniture click |
| Date navigation | Pending | Previous/next day |
| State color integration | Pending | From beach_reservation_states |
| Temporary furniture | Pending | Per-date visibility |

### Decisions Made
- (None yet)

### Issues Discovered
- (None yet)

---

## Phase 8: Smart Features

### Objectives
- [ ] Furniture suggestion algorithm
- [ ] Contiguity optimization
- [ ] Preference-based recommendations

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Suggestion algorithm | Pending | 40/35/25 weights |
| Occupancy map builder | Pending | |
| Contiguity validation | Pending | Gap detection |
| Preference matching | Pending | Pref -> feature map |
| Capacity scoring | Pending | |
| Multi-day optimization | Pending | Consistent furniture |
| Suggestion API endpoint | Pending | |
| Frontend integration | Pending | Auto-suggest button |
| Gap warning UI | Pending | Toast notification |

### Decisions Made
- (None yet)

### Issues Discovered
- (None yet)

---

## Phase 9: Reports & Polish

### Objectives
- [ ] Dashboard with KPIs
- [ ] Export to Excel/PDF
- [ ] Analytics charts
- [ ] Final UI polish

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Dashboard layout | Pending | |
| Today's reservations widget | Pending | |
| Occupancy stats | Pending | |
| Revenue summary | Pending | |
| Customer stats | Pending | Interno/externo |
| Reservations by date chart | Pending | |
| Excel export | Pending | openpyxl |
| PDF export | Pending | ReportLab |
| Date range reports | Pending | |
| UI consistency pass | Pending | |
| Mobile responsiveness | Pending | |
| Loading states | Pending | |
| Error handling UI | Pending | |
| Final testing | Pending | |

### Decisions Made
- (None yet)

### Issues Discovered
- (None yet)

---

## Architecture Decisions Log

### ADR-001: Blueprint Structure
- **Date:** 2025-12-14
- **Decision:** Modular blueprints with sub-blueprints for related routes
- **Rationale:** Clean separation of concerns, easier maintenance
- **Structure:**
  - `auth` - Authentication (login, logout, profile)
  - `admin` - User/role management, hotel guests
  - `beach` - Main beach operations with sub-blueprints:
    - `beach.beach_config` - Infrastructure config (zones, furniture, prefs, tags)
    - Future: `beach.reservations`, `beach.customers`
  - `api` - REST API endpoints
- **Consequences:** Clear organization, but requires careful URL prefix management

### ADR-002: Database Choice
- **Date:** 2025-12-14
- **Decision:** SQLite with WAL mode
- **Rationale:** Simple deployment, sufficient for single-hotel use case
- **Consequences:** No concurrent write scaling, but adequate for expected load

### ADR-003: Preferencias Bidireccionales
- **Date:** 2025-12-14
- **Decision:** Las preferencias se sincronizan bidireccionalmente entre clientes y reservas
- **Flow Reserva → Cliente:**
  1. Usuario crea/edita reserva con preferencias seleccionadas
  2. Al guardar, `sync_preferences_to_customer_profile()` actualiza `beach_customer_preferences`
  3. Próximas reservas del mismo cliente cargan estas preferencias automáticamente
- **Flow Cliente → Reserva:**
  1. Usuario selecciona cliente en nueva reserva
  2. Sistema carga preferencias desde `beach_customer_preferences`
  3. Auto-popula campo preferences (usuario puede modificar)
- **Rationale:** El perfil del cliente "aprende" de cada reserva, mejorando sugerencias futuras
- **Consequences:** Mayor complejidad en lógica de guardado, pero mejor UX y sugerencias más precisas

### ADR-004: Feature Mapping para Sugerencias
- **Date:** 2025-12-14
- **Decision:** Preferencias mapean a features de mobiliario via `maps_to_feature`
- **Ejemplo:**
  - `pref_sombra` → busca mobiliario con feature `sombra`
  - `pref_primera_linea` → busca mobiliario con feature `primera_linea`
- **Algoritmo:** 40% contigüidad + 35% preferencias + 25% capacidad
- **Rationale:** Permite sugerencias automáticas basadas en historial del cliente
- **Consequences:** Requiere mantener consistencia entre códigos de preferencia y features de mobiliario

### ADR-005: Sistema Visual SVG para Tipos de Mobiliario
- **Date:** 2025-12-14
- **Decision:** Cada tipo de mobiliario define su representación SVG con formas configurables
- **Formas soportadas:**
  - `rounded_rect` - Rectángulo con esquinas redondeadas (default)
  - `rectangle` - Rectángulo estándar
  - `circle` - Círculo
  - `ellipse` - Elipse
  - `custom` - Código SVG personalizado con placeholders {{fill}} y {{stroke}}
- **Colores:**
  - `fill_color` - Color de relleno base del tipo
  - `stroke_color` - Color de borde
  - **IMPORTANTE:** Los colores por estado NO se definen en el tipo de mobiliario
- **Auto-numeración:**
  - `number_prefix` - Prefijo (ej: "H" para hamacas)
  - `number_start` - Número inicial
  - Genera: H1, H2, H3... automáticamente
- **Rationale:** Permite visualización consistente en el mapa interactivo (Phase 7)
- **Consequences:**
  - Requiere migración de datos existentes
  - Mayor complejidad en UI pero mejor experiencia de configuración
  - Preview en tiempo real mejora UX significativamente

### ADR-006: Colores de Estado Globales (No por Tipo de Mobiliario)
- **Date:** 2025-12-14
- **Decision:** Los colores por estado de reserva son GLOBALES, definidos en `beach_reservation_states`
- **Ubicación:** Configuración → Estados de Reserva (una vez implementado)
- **Estados con color:**
  - Disponible, Reservado, Ocupado, Mantenimiento, etc.
  - Cada estado define: nombre, color, comportamiento (libera disponibilidad, etc.)
- **Flujo:**
  1. Usuario configura estados en "Estados de Reserva" con sus colores
  2. Al renderizar mapa, se obtienen colores desde `beach_reservation_states`
  3. Función `get_furniture_type_svg(type_config, state, state_colors)` recibe colores externos
- **Rationale:**
  - Consistencia visual en todo el sistema
  - Un solo punto de configuración de colores
  - Evita confusión de "¿por qué mi hamaca tiene diferente color que mi balinesa?"
  - Facilita cambios globales de esquema de colores
- **Consequences:**
  - Los tipos de mobiliario NO tienen campo `status_colors`
  - El mapa debe cargar estados antes de renderizar
  - Simplifica el formulario de tipos de mobiliario

### ADR-007: Esquema de Reservas con Fecha Única y Parent/Child
- **Date:** 2025-12-15
- **Decision:** Usar esquema SPEC con `reservation_date` única por reserva + parent/child para multi-día
- **Estructura:**
  - Cada reserva tiene una sola `reservation_date`
  - Reservas multi-día: primera fecha = parent, siguientes = children con `parent_reservation_id`
  - Ticket number format: YYMMDDRR (parent) y YYMMDDRR-N (children)
- **Campos clave:**
  - `ticket_number` - Identificador único formato YYMMDDRR
  - `reservation_date` - Fecha única de la reserva
  - `current_states` - CSV de estados acumulados ("Confirmada, Sentada")
  - `current_state` - Estado principal para display (prioridad)
  - `parent_reservation_id` - Enlace a reserva parent (NULL si es parent o single-day)
- **Rationale:**
  - Gestión de estados más limpia por día individual
  - Facilita cancelación/modificación de días específicos
  - Compatible con estados que liberan disponibilidad
  - Mejor trazabilidad de historial por día
- **Consequences:**
  - Requiere migración de esquema existente
  - Lógica adicional para mantener consistencia parent/child
  - Consultas más complejas para obtener grupo completo

---

## Default Preferences (Seed Data)

```python
DEFAULT_PREFERENCES = [
    # (code, display_name, icon, maps_to_feature)
    ('pref_sombra', 'Sombra', 'fa-umbrella', 'sombra'),
    ('pref_primera_linea', 'Primera Línea', 'fa-water', 'primera_linea'),
    ('pref_vip', 'Zona VIP', 'fa-star', 'vip'),
    ('pref_tranquilo', 'Zona Tranquila', 'fa-volume-off', 'tranquila'),
    ('pref_cerca_bar', 'Cerca del Bar', 'fa-martini-glass', 'cerca_bar'),
    ('pref_familia', 'Zona Familiar', 'fa-children', 'familia'),
    ('pref_accesible', 'Acceso Fácil', 'fa-wheelchair', 'accesible'),
    ('pref_cerca_mar', 'Cerca del Mar', 'fa-anchor', 'cerca_mar'),
]
```

---

## Session Log

### Session Template
```
### Session: YYYY-MM-DD
**Duration:** X hours
**Focus:** [Phase/Task]

#### Completed
- Item 1
- Item 2

#### Decisions
- Decision 1: Rationale

#### Issues
- Issue 1: Resolution or pending

#### Next Session
- Priority 1
- Priority 2
```

---

### Session: 2025-12-22 (Phase 7A Complete)
**Duration:** Single session
**Focus:** Interactive Map Editor

#### Completed
- **Map Editor Core** (`static/js/map-editor.js`, `templates/beach/config/map_editor.html`)
  - SVG-based canvas with configurable dimensions per zone
  - Drag-and-drop furniture from palette
  - Click to select, drag to reposition
  - Snap-to-grid (10px, 25px, 50px options)
  - Zoom with Ctrl+wheel centered on mouse position
  - Pan with Space+drag or middle mouse button
  - Rulers (horizontal/vertical) synced with scroll
  - Center guides (crosshairs) for alignment
  - Canvas bounds validation (prevent elements outside)

- **Properties Panel**
  - Position X/Y, rotation, capacity
  - Furniture features (tags from beach_preferences)
  - Duplicate functionality (horizontal/vertical)
  - Configurable copies count (1-50) and spacing

- **Backend Enhancements** (`blueprints/beach/routes/config/map_editor.py`)
  - GET /map-editor/features - Load available features
  - POST /map-editor/furniture/<id>/duplicate - Duplicate with bounds check

- **Numbering Fix** (`models/furniture_type.py`)
  - `get_next_number_for_type()` now finds first available gap
  - Deleted furniture numbers are reused

- **Infrastructure**
  - Added CSRF token meta tag to base.html
  - LocalStorage with memory fallback for blocked browsers

#### Decisions
- Minimap feature explored but removed (user preference)
- Zoom to mouse position for professional CAD-like experience
- Features from preferences table for consistency with suggestion algorithm

#### Issues Fixed
- LocalStorage blocked by Tracking Prevention → Memory fallback
- Horizontal panning not working → Changed CSS from flex to overflow:scroll
- Furniture numbering kept incrementing → Find first gap algorithm

#### Commits
- `808cfbc` - Implement interactive map editor with advanced features

#### Next Session
- Phase 7B: Live Map with availability display
- Or Phase 8: Smart Features

---

### Session: 2025-12-21 (Phase 6B Frontend + Calendar)
**Duration:** Single session
**Focus:** Phase 6B Frontend Integration + Collapsible Calendar

#### Completed
- **Frontend Integration** (`templates/beach/reservation_form.html`)
  - Duplicate detection: Alert when customer already has reservation on selected date
  - Smart suggestions modal: Show weighted suggestions with scores and reasons
  - Contiguity validation: Warning when selected furniture has gaps
  - Alert container for real-time warnings

- **Collapsible Calendar Picker**
  - Replaced date input with collapsible calendar
  - Click to expand, click outside to close
  - Click dates to select/deselect (gold highlight)
  - Calendar stays open during date selection (fixed interaction bug)
  - Selected dates shown as removable tags
  - Month navigation (left/right arrows)
  - Past dates disabled
  - Preview text: "3 dias: 22/12, 23/12, 24/12"
  - Form submission handles single-day (POST) and multi-day (AJAX API)

- **API Endpoint** (`blueprints/beach/__init__.py`)
  - Added `/api/customers/create-from-guest` for multi-day hotel guest reservations

#### Decisions
- Calendar closes only on click outside (not on date selection)
- No "Listo" button - simpler UX with outside click
- `calendarInteracting` flag prevents close during date/month clicks

#### Issues Fixed
- Calendar closing on every date click
  - Resolution: Added `calendarInteracting` flag with 50ms timeout
  - Flag set during toggleDate() and changeMonth() to prevent click-outside handler

#### Commits
- `ccfc69a` - Add collapsible calendar for multi-day reservation selection

#### Next Session
- Phase 7: Interactive Map

---

### Session: 2025-12-21 (Phase 6C Complete)
**Duration:** Single session
**Focus:** Sentada State + Customer Statistics

#### Completed
- **Database Migrations** (`database.py`)
  - `migrate_add_sentada_state()` - New state for tracking when customers are at the beach
  - `migrate_customers_extended_stats()` - Added no_shows, cancellations, total_reservations columns
  - Updated `seed_database()` with Sentada state
  - Updated `create_tables()` with new beach_customers columns

- **State Priority** (`models/reservation_state.py`)
  - Added 'Sentada' to `RESERVATION_STATE_DISPLAY_PRIORITY` at level 6
  - Extended `update_customer_statistics()` to calculate:
    - total_visits: Reservations with 'Sentada' state
    - no_shows: Reservations with 'No-Show' state
    - cancellations: Reservations with 'Cancelada' state
    - total_reservations: Count excluding Cancelada and No-Show

- **Customer CRUD** (`models/customer_crud.py`)
  - Added no_shows, cancellations, total_reservations to allowed_fields

- **Customer Detail UI** (`templates/beach/customer_detail.html`)
  - Enhanced Stats Card with:
    - Visitas (Sentada) with fa-couch icon
    - No-Shows with fa-user-times icon (red when count > 0)
    - Cancelaciones with fa-times-circle icon (orange when count > 0)

#### Decisions
- PMS integration deferred - prices are informational only for employees
- Sentada state represents physical beach presence (customer at their furniture)
- Auto-update of customer stats on any state change

#### All 70 Tests Passing

#### Next Session
- Phase 7: Interactive Map

---

### Session: 2025-12-22 (Phase 6D Complete)
**Duration:** Single session
**Focus:** Configurable Reservation States System

#### Completed
- **Database Migration** (`database/migrations.py`)
  - `migrate_reservation_states_configurable()` - Adds display_priority, creates_incident, is_system, is_default columns
  - Deactivates legacy states (pendiente, checkin, activa, completada)
  - Updates 5 core states with proper properties

- **New Model** (`models/state.py`)
  - Full CRUD: get_all_states, get_state_by_id/code/name, create_state, update_state, delete_state
  - Dynamic lookups: get_default_state, get_state_priority_map, get_incident_states, get_releasing_states
  - Reordering: reorder_states for drag-drop support

- **Refactored Hardcoded References**
  - Removed `RESERVATION_STATE_DISPLAY_PRIORITY` constant from reservation_state.py
  - `reservation_crud.py`: Uses get_default_state() instead of hardcoded 'Confirmada'
  - `reservation_multiday.py`: Uses get_default_state() for initial state
  - `reservation_suggestions.py`: Dynamic query using get_releasing_states()

- **Configuration UI**
  - Routes in `blueprints/beach/routes/config/states.py`
  - `states.html`: List with show_inactive toggle, centered columns
  - `state_form.html`: Create/edit form with color picker, behavior switches

- **Design Review Fixes**
  - Aligned states.html with tags.html design pattern
  - Centered all table columns
  - Simplified info card layout

#### Decisions
- 5 system states: Confirmada (default), Sentada, Cancelada, No-Show, Liberada
- Cobrada removed (not part of initial states)
- System states (is_system=1) cannot be deleted
- Soft delete pattern (active=0)

#### Files Created
- `models/state.py` (new)
- `blueprints/beach/routes/config/states.py` (new)
- `templates/beach/config/states.html` (new)
- `templates/beach/config/state_form.html` (new)

#### Commits
- `da850eb` - Implement configurable reservation states system

#### Next Session
- Phase 7: Interactive Map

---

### Session: 2025-12-21 (Phase 6B Complete)
**Duration:** Single session
**Focus:** Phase 6B - Availability, Multi-day, Smart Suggestions

#### Completed
- **Module 1: Bulk Availability** (`models/reservation_availability.py`)
  - `check_furniture_availability_bulk()` - Multiple furniture/dates check
  - `check_duplicate_reservation()` - Same customer + date overlap detection
  - `get_furniture_availability_map()` - Calendar view support with occupancy stats
  - `get_conflicting_reservations()` - Get reservations blocking availability

- **Module 2: Multi-day Reservations** (`models/reservation_multiday.py`)
  - `create_linked_multiday_reservations()` - Parent/child creation with YYMMDDRR-N tickets
  - `update_multiday_reservations()` - Bulk update across linked group
  - `cancel_multiday_reservations()` - Cancel entire group atomically
  - `get_multiday_summary()` - Get group overview with all dates
  - `is_parent_reservation()` / `get_child_reservations()` - Navigation helpers

- **Module 3: Smart Suggestions** (`models/reservation_suggestions.py`)
  - `build_furniture_occupancy_map()` - Spatial mapping by rows (±30px tolerance)
  - `validate_cluster_contiguity()` - Detect occupied gaps in selection
  - `suggest_furniture_for_reservation()` - Weighted scoring algorithm
  - `score_preference_match()` - Match preferences to furniture features
  - `get_customer_preferred_furniture()` - History-based furniture preferences

- **11 API Endpoints** added to `blueprints/beach/__init__.py`

#### Decisions
- Releasing states (Cancelada, No-Show, Liberada) respected in all availability checks
- Multi-day tickets: Parent=YYMMDDRR, Children=YYMMDDRR-1, YYMMDDRR-2...
- Suggestion weights: 40% contiguity + 35% preferences + 25% capacity
- Row grouping uses ±30px Y-position tolerance
- Preference-to-feature mapping (e.g., pref_sombra→shaded, pref_primera_linea→first_line)

#### Issues Fixed
- None significant - modular implementation worked well

#### Next Session
- Begin Phase 6C: Pricing + PMS Integration
- Or proceed to Phase 7: Interactive Map

---

### Session: 2025-12-21 (Phase 6A)
**Duration:** Single session
**Focus:** Reservation Form Customer Section Enhancements

#### Completed
- **Customer Search Enhancements** (`models/customer_search.py`)
  - Unified search for beach_customers and hotel_guests with accent-insensitive matching
  - Check-in/check-out today detection with visual badges
  - Filter expired hotel stays (interno customers after checkout not shown)
  - Single guest per room in search results (main guest + count in parentheses)
  - Date comparison fix: handle both date objects and ISO format strings

- **Reservation Form UI** (`templates/beach/reservation_form.html`)
  - Fixed hotel guest notes display (was hidden by `selectHotelGuest()`)
  - Added profile link button for quick access to full customer details
  - Added customer stats section (language, visits, total spent)
  - Added check-in badge (green) and check-out badge (red) in search results
  - Fixed room info display for external customers (hide "Hab. None")

- **API Updates** (`blueprints/beach/__init__.py`)
  - Added `is_checkin_today` and `is_checkout_today` flags to search response
  - Added `total_spent` to customer data
  - Fixed room_number to return null instead of "None" string

- **Customer List Fix** (`templates/beach/customers.html`)
  - Fixed reservation count badge contrast (changed from invalid `bg-outline-secondary` to `bg-secondary`)

#### Decisions
- Check-in/check-out detection uses hotel_guests table for both new hotel guests AND existing interno customers
- Interno customers without active hotel stay are filtered from search (prevents stale data)
- Date comparison handles both Python date objects and ISO format strings for compatibility

#### Issues Fixed
- Date comparison returning False: `datetime.date` vs string comparison issue
  - Resolution: Check `isinstance(arrival, str)` and compare appropriately
- API not passing check-in/check-out flags to frontend
  - Resolution: Added flags to API response dict
- "Hab. None" showing for external customers
  - Resolution: Check for "None" string in API and JavaScript
- Wrong guest returned for check-in today
  - Resolution: Added `(h.arrival_date = date('now')) DESC` to ORDER BY

#### Next Session
- Begin Phase 6A core: DB migration, reservation CRUD, state management
- Implement ticket number generation (YYMMDDRR format)
- Complete reservation creation flow

---

### Session: 2025-12-14 (Phase 5)
**Duration:** Single session
**Focus:** Phase 5 - Customer Management

#### Completed
- **Customer Model Enhancements** (`models/customer.py`)
  - `get_customers_filtered()` - Advanced filtering with pagination
  - `get_customer_with_details()` - Full customer with prefs, tags, reservations
  - `get_customer_stats()` - Dashboard statistics
  - `merge_customers()` - Full merge logic with transaction handling
  - `find_potential_duplicates_for_customer()` - Find duplicates for merge

- **Beach Blueprint Routes** (`blueprints/beach/__init__.py`)
  - Customer CRUD routes (list, create, edit, delete, detail)
  - Customer merge route
  - API endpoints: search, check-duplicates, hotel-guest-lookup

- **Templates Created**
  - `customers.html` - List with stats cards, filters, table
  - `customer_form.html` - Create/edit with interno/externo tabs, hotel guest auto-fill
  - `customer_detail.html` - Full profile with preferences, tags, reservation history
  - `customer_merge.html` - Source/target selection with search

- **Test Suite** (`tests/test_customer.py`)
  - 16 tests covering model functions and routes
  - All tests passing

#### Decisions
- Interno/externo selection via Bootstrap 5 pills
- Hotel guest auto-fill via AJAX lookup by room number
- Real-time duplicate detection on phone/room change
- Merge transfers reservations, preferences, tags then deletes source

#### Issues Fixed
- Template stats variable undefined (added `{% if stats %}` check)

#### Next Session
- Begin Phase 6: Reservations
- Reservation CRUD with multi-day support
- Availability checking and double-booking prevention

---

### Session: 2025-12-14 (Phase 4.6)
**Duration:** Single session
**Focus:** Phase 4.6 - Enhanced Furniture Management

#### Completed
- **Furniture Form Improvements** (`templates/beach/config/furniture_form.html`)
  - Reordered form fields: Type → Code → Zone (better UX flow)
  - Auto-generated sequential code when selecting furniture type
  - Default zone selection (first available zone)
  - Live preview updates in real-time for all fields
  - Text always horizontal in preview (counter-rotation technique)

- **Duplication Feature**
  - Added duplication section with: copy count, layout (H/V), spacing
  - Available in both create and edit modes
  - In create: creates multiple elements at once
  - In edit: "Duplicate" button creates copies without modifying original
  - Sequential numbering based on prefix (B1→B5, not B1_1)

- **Backend Updates** (`blueprints/beach/routes/config.py`)
  - Modified `furniture_create()` to handle duplication parameters
  - Modified `furniture_edit()` to support duplicate action
  - Duplication uses `get_next_number_by_prefix()` for correct sequence

- **New Model Function** (`models/furniture.py`)
  - `get_next_number_by_prefix(prefix)` - Finds max number with prefix and returns next

#### Decisions
- Duplication positions start from current element position + spacing
- Separate "Save" and "Duplicate" buttons in edit mode for clarity
- Preview limited to 10 items for performance

#### Issues Fixed
- Template block name mismatch (`{% block scripts %}` vs `{% block extra_js %}`)
- Jinja2 dict attribute access (`t.id` → `t['id']`)
- Event listeners not firing for duplication fields

#### Next Session
- Begin Phase 5: Customers
- Customer CRUD (interno/externo types)
- Hotel guest auto-fill integration

---

### Session: 2025-12-14 (Phase 4.5)
**Duration:** Single session
**Focus:** Phase 4.5 - Enhanced Furniture Types

#### Completed
- **Database Migration** (`database.py`)
  - Added new columns to `beach_furniture_types`
  - `number_start` - Starting number for auto-numbering
  - `default_features` - CSV of default features
  - `allowed_zones` - CSV of allowed zone IDs
  - `display_order` - For drag-drop reordering
  - Migration function `migrate_furniture_types_v2()` with idempotent ALTER TABLE
  - Migration function `migrate_add_furniture_types_menu()` for menu permission

- **Model Functions** (`models/furniture_type.py`)
  - `get_next_number_for_type(type_id, zone_id)` - Auto-numbering with prefix
  - `get_furniture_type_svg(type_config, state, state_colors)` - SVG generation
  - `validate_furniture_type_data(data, is_update)` - Complete validation with XSS prevention
  - `update_furniture_types_order(type_ids)` - Drag-drop reordering

- **New Routes** (`blueprints/beach/routes/config.py`)
  - `POST /config/furniture-types/preview` - AJAX SVG preview (single shape)
  - `GET /config/furniture-types/<id>/next-number` - Auto-numbering endpoint
  - `POST /config/furniture-types/reorder` - Drag-drop order update
  - `POST /config/furniture-types/<id>/delete` - Delete with validation

- **Templates** (`templates/beach/config/`)
  - `furniture_types.html` - Two-panel layout (30% list + 70% form)
  - `_furniture_type_form.html` - Partial with 6 collapsible sections:
    1. Identificación (code, name, icon picker)
    2. Representación Visual (shape, dimensions, fill/stroke colors, SVG preview)
    3. Capacidad (min/max/default)
    4. Comportamiento (rotation, decorative, suite-only, active)
    5. Numeración (prefix, start number)
    6. Configuración Avanzada (features, allowed zones)

- **App Filter** (`app.py`)
  - Added `from_json` Jinja2 template filter for parsing JSON strings

#### Decisions
- Kept existing `is_suite_only` + added separate `is_decorative` flag
- Adapted to existing DB column names (map_shape, stroke_color, etc.)
- **CRITICAL: Status colors are NOT per furniture type** (ADR-006)
  - Colors come from global reservation states configuration
  - Furniture types only define fill_color (base color) and stroke_color
- Sortable.js via CDN for drag-drop reordering
- Form uses Bootstrap accordion for collapsible sections

#### Issues Fixed
- Database column name mismatch (plan had svg_shape_type, DB had map_shape)
  - Resolution: Used existing column names, added only missing columns
- Jinja2 missing from_json filter
  - Resolution: Added filter to app.py context processors
- Initial design incorrectly had status_colors per type
  - Resolution: Removed; colors come from beach_reservation_states (to be implemented)
- Menu item "Tipos de Mobiliario" missing
  - Resolution: Added migration to insert menu permission
- Template block name mismatch (`{% block scripts %}` vs `{% block extra_js %}`)
  - Resolution: Changed to `{% block extra_js %}` to match base.html
- Sortable.js drag-drop not working
  - Resolution: Added `forceFallback: true`, filter for links, debug logging
- Icon picker click events not working
  - Resolution: Added `e.preventDefault()`, `e.stopPropagation()`, debug logging

#### Known Issues (Pending Debug)
- Drag-drop reordering needs testing after JS block fix
- Icon picker needs testing after JS block fix
- SVG preview AJAX needs testing

#### Next Session
- **PRIORITY: Debug Tipos de Mobiliario UI**
  - Test icon picker functionality
  - Test drag-drop reordering
  - Test SVG preview
  - Test form submission (create/edit)
- Then continue with Phase 5: Customers

---

### Session: 2025-12-14 (Phase 4)
**Duration:** Single session
**Focus:** Phase 4 - Beach Infrastructure

#### Completed
- **Config Routes Blueprint** (`blueprints/beach/routes/config.py`)
  - Zones CRUD with hierarchical parent support
  - Furniture Types CRUD with capacity, icon, color
  - Furniture CRUD with positioning (x, y, rotation, width, height)
  - Preferences CRUD with feature mapping for suggestions
  - Tags CRUD with color picker
  - API endpoint for map drag-drop positioning

- **Models Created**
  - `models/furniture_type.py` - Furniture type CRUD
  - `models/preference.py` - Customer preference CRUD with customer assignment
  - `models/tag.py` - Tag CRUD for customers and reservations

- **Templates** (`templates/beach/config/`)
  - `zones.html`, `zone_form.html` - Zone management
  - `furniture_types.html`, `furniture_type_form.html` - Type management
  - `furniture.html`, `furniture_form.html` - Furniture with position preview
  - `preferences.html`, `preference_form.html` - Preference management
  - `tags.html`, `tag_form.html` - Tag management with color picker

#### Decisions
- Config routes as sub-blueprint under `/beach/config/*`
- Preferences use `maps_to_feature` for suggestion algorithm mapping
- Tags shared between customers and reservations
- Furniture position preview in form using scaled canvas

#### Issues Fixed
- None

#### Next Session
- Begin Phase 5: Customers
- Customer CRUD (interno/externo types)
- Hotel guest auto-fill for room number

---

### Session: 2025-12-14 (Phase 3)
**Duration:** Multiple sessions
**Focus:** Phase 3 - Hotel Guests Integration

#### Completed
- **Hierarchical Menu Structure**
  - Reorganized navigation into 4 parent sections
  - Administración → Usuarios, Roles, Auditoría, Huéspedes Hotel
  - Configuración, Operaciones, Informes (placeholders)
  - Updated `utils/permissions.py` for nested menu generation
  - Updated `_sidebar.html` with Bootstrap 5 collapsible menus
  - Added CSS transitions and styling

- **Hotel Guests Model** (`models/hotel_guest.py`)
  - Full CRUD operations
  - `upsert_hotel_guest()` for import deduplication
  - `get_guest_count()` for dashboard stats
  - `get_distinct_rooms()` for filter dropdown

- **Excel Import Service** (`blueprints/admin/services.py`)
  - Auto-detect Spanish column headers from PMS export
  - Column mapping: Nombre, Apellidos, Háb., Llegada, Salida, País, Tipo
  - Date parsing for multiple formats
  - Validation and preview endpoints
  - Successfully tested with 535 records (285 unique guests)

- **Admin Routes** (`blueprints/admin/routes.py`)
  - `/admin/hotel-guests` - List with filters
  - `/admin/hotel-guests/import` - Excel upload
  - `/admin/hotel-guests/<id>` - Detail view
  - `/admin/hotel-guests/<id>/delete` - Delete
  - `/admin/api/hotel-guests/preview` - AJAX preview

- **Templates**
  - `hotel_guests.html` - Guest list with stats
  - `hotel_guests_import.html` - Upload with preview
  - `hotel_guest_detail.html` - Guest information

#### Decisions
- Upsert key: room_number + arrival_date (unique per stay)
- openpyxl for Excel parsing (supports .xlsx and .xls)
- Windows temp file cleanup with retry loop

#### Issues Fixed
- SQLite non-deterministic index error → Removed partial index
- CSRF token undefined → Added CSRFProtect initialization
- Windows file locking → Added retry with sleep(0.1)

#### Next Session
- Begin Phase 4: Beach Infrastructure
- Zones CRUD
- Furniture types and positioning

---

### Session: 2025-12-14 (Phase 1 & 2)
**Duration:** Multiple sessions
**Focus:** Phase 1 & 2 completion, starting Phase 3

#### Completed
- Phase 1: Foundation fully implemented
  - Flask app factory pattern with blueprints
  - Database with all 22 tables
  - Auth blueprint (login, logout, profile)
  - Base templates with Bootstrap 5 design system
  - Error pages (403, 404, 500)
- Phase 2: Core Admin fully implemented
  - User CRUD with filtering
  - Role management with permission assignment
  - Dynamic sidebar menu based on permissions
  - Admin dashboard
- Test suite created in tests/ folder
- Moved test_app.py to tests/ folder

#### Decisions
- Used sidebar + topbar layout instead of navbar
- Implemented design system (DESIGN_SYSTEM.md)

#### Issues
- None

#### Next Session
- Begin Phase 3: Hotel Guests Integration
- Excel import functionality
- Hotel guests list with filters

---

### Session: (First Session)
**Duration:** -
**Focus:** Project initialization

#### Completed
- Created CLAUDE.md
- Created DEVELOPMENT_PLAN.md
- Created bootstrap prompt

#### Decisions
- (None yet)

#### Issues
- (None yet)

#### Next Session
- Begin Phase 1: Create project structure
- Implement app factory pattern
- Create database schema

---

## Quick Reference

### File Locations
- **CLAUDE.md:** Project context for Claude
- **DEVELOPMENT_PLAN.md:** This file (living plan)
- **BEACH_CLUB_NEW_PROJECT_PROMPT.md:** Bootstrap prompt for new sessions

### Commands
```bash
# Start server
python app.py

# Run tests
python -m pytest

# Run specific test
python -m pytest tests/unit/test_customers.py -v
```

### Review Commands
```
/review              # Code review
/security-review     # Security review
/design-review       # Design review
```
