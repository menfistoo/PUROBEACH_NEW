# Beach Club Development Plan

> **LIVING DOCUMENT**: This file tracks all development phases, decisions, and progress.
> Update this file after every work session to preserve context across conversations.

---

## Current Status

| Field | Value |
|-------|-------|
| **Current Phase** | Phase 6A: Reservations Core |
| **Last Updated** | 2025-12-21 |
| **Last Session** | Reservation form customer section enhancements |
| **Next Priority** | Complete reservation creation flow + state management |

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
| 6A | Reservations: Core CRUD + States | In Progress | 25% |
| 6B | Reservations: Availability + Multi-day | Not Started | 0% |
| 6C | Reservations: Pricing + PMS | Not Started | 0% |
| 7 | Interactive Map | Not Started | 0% |
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
| DB migration (SPEC columns) | Pending | ticket_number, current_states, pricing fields |
| generate_reservation_number() | Pending | Atomic YYMMDDRR format with retries |
| create_beach_reservation() | Pending | Full creation with validations |
| get/update/delete functions | Pending | Basic CRUD operations |
| add_reservation_state() | Pending | CSV accumulative state management |
| remove_reservation_state() | Pending | Remove from CSV, recalculate priority |
| cancel_beach_reservation() | Pending | Shortcut to add Cancelada state |
| calculate_reservation_color() | Pending | Priority-based color selection |
| get_active_releasing_states() | Pending | States that free availability |
| Reservation list route | Pending | GET /beach/reservations with filters |
| Reservation create route | Pending | GET/POST /beach/reservations/create |
| Reservation detail route | Pending | GET /beach/reservations/<id> |
| Reservation edit route | Pending | GET/POST /beach/reservations/<id>/edit |
| State toggle API | Pending | POST /beach/api/reservations/<id>/toggle-state |
| Status history API | Pending | GET /beach/api/reservations/<id>/history |
| Update templates | Pending | Connect forms to new model |

---

### Phase 6B: Availability + Multi-day + Suggestions

| Task | Status | Notes |
|------|--------|-------|
| check_furniture_availability() | Pending | Single furniture/date check |
| check_furniture_availability_bulk() | Pending | Multiple furniture/dates |
| check_duplicate_reservation() | Pending | Same customer + date overlap detection |
| create_linked_multiday_reservations() | Pending | Parent/child creation |
| get_linked_reservations() | Pending | Get all related reservations |
| suggest_furniture_for_reservation() | Pending | Smart suggestions with scoring |
| build_furniture_occupancy_map() | Pending | Spatial mapping by rows |
| validate_cluster_contiguity() | Pending | Gap detection in selection |
| Availability check API | Pending | POST /beach/api/reservations/check-availability |
| Duplicate check API | Pending | POST /beach/api/reservations/check-duplicate |
| Suggestion API | Pending | POST /beach/api/reservations/suggest-furniture |
| Multi-day creation API | Pending | POST /beach/api/reservations/create-multiday |

**Suggestion Algorithm Weights:**
- 40% Contiguity (no gaps between selected furniture)
- 35% Preference matching (customer prefs → furniture features)
- 25% Capacity fit (num_people vs furniture capacity)

---

### Phase 6C: Pricing + PMS Integration

| Task | Status | Notes |
|------|--------|-------|
| validate_and_calculate_price() | Pending | Anti-fraud server-side validation |
| get_applicable_consumption_policy() | Pending | Find policy by zone/type/customer |
| mark_consumption_charged_to_pms() | Pending | Mark reservation as charged |
| get_reservations_pending_pms_charge() | Pending | List pending charges |
| update_beach_customer_statistics() | Pending | Auto-update on state changes |
| PMS charge API | Pending | POST /beach/api/consumption/mark-charged/<id> |
| Pending charges report | Pending | GET /beach/reports/pending-charges |

**Customer Stats Auto-Update:**
- total_reservations: Count excluding releasing states
- total_visits: Reservations with 'Sentada' state
- no_shows: Reservations with 'No-Show' state
- cancellations: Reservations with 'Cancelada' state
- last_visit_date: Most recent 'Sentada' date

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

## Phase 7: Interactive Map

### Objectives
- [ ] SVG-based beach map
- [ ] Drag-and-drop furniture
- [ ] Real-time availability display
- [ ] Reservation creation from map

### Tasks

| Task | Status | Notes |
|------|--------|-------|
| Map container component | Pending | |
| Zone rendering | Pending | Colors, labels |
| Furniture rendering | Pending | SVG shapes |
| Availability colors | Pending | Available/occupied |
| Click to select | Pending | |
| Drag to reposition | Pending | Admin only |
| Tooltip on hover | Pending | Reservation info |
| Quick reservation modal | Pending | From map click |
| Date navigation | Pending | Previous/next day |
| Zoom controls | Pending | |
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
