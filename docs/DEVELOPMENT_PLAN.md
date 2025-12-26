# Beach Club Management System - Development Plan

**Last Updated:** 2025-12-25
**Current Phase:** Payment & Pricing System Planning

---

## Table of Contents
1. [Payment & Pricing System](#payment--pricing-system)
2. [Insights & Analytics Planning](#insights--analytics-planning)
3. [Implementation Roadmap](#implementation-roadmap)
4. [Technical Decisions](#technical-decisions)
5. [Completed Items](#completed-items)

---

## Payment & Pricing System

### Overview
Comprehensive pricing and payment control system for beach club reservations. Does not handle direct payment processing or revenue tracking - focuses on **pricing configuration, reservation type selection, and price calculation** at booking time.

### Business Context
- **No direct payment integration:** System controls pricing logic, not payment processing
- **No revenue/ticket tracking:** External systems handle financial transactions
- **Focus:** Configure pricing rules, select reservation type, calculate amounts during booking

---

### Reservation Types

The system supports **3 distinct reservation types** that determine pricing and service delivery:

#### Type 1: Incluido en Reserva (Included)
**Description:** No additional charge - included in hotel package or complimentary

**Characteristics:**
- Default for **interno** (hotel guest) customers
- Price = €0.00
- No minimum consumption required
- Typically for hotel all-inclusive packages

**Use Cases:**
- Hotel guests with beach access included in room rate
- VIP complimentary reservations
- Staff/employee reservations

**UI Label:** "Incluido en Reserva" / "Incluido" (Spanish)

---

#### Type 2: Paquete (Package)
**Description:** Pre-configured service packages with fixed or per-person pricing

**Configuration Fields:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `package_name` | TEXT | Yes | Package title | "Paquete Premium", "Día de Playa VIP" |
| `package_description` | TEXT | No | Services included | "2 hamacas + sombrilla + toallas + bebida bienvenida" |
| `base_price` | DECIMAL | Yes | Package base price | 89.00 |
| `price_type` | ENUM | Yes | 'per_package' or 'per_person' | 'per_person' |
| `min_people` | INTEGER | Yes | Minimum capacity | 1 |
| `standard_people` | INTEGER | Yes | Standard/recommended capacity | 2 |
| `max_people` | INTEGER | Yes | Maximum capacity | 4 |
| `furniture_types_included` | TEXT | No | Included furniture types (comma-separated) | "hamaca,sombrilla" |
| `customer_type` | ENUM | No | Applies to 'interno', 'externo', or 'both' | 'externo' |
| `zone_id` | INTEGER | No | Specific zone restriction | 3 |
| `valid_from` | DATE | No | Valid from date | 2025-06-01 |
| `valid_until` | DATE | No | Valid until date | 2025-09-30 |
| `active` | BOOLEAN | Yes | Active status | 1 |
| `display_order` | INTEGER | No | Display priority in UI | 1 |

**Pricing Calculation Logic:**
```python
if price_type == 'per_package':
    total_price = base_price  # Fixed price regardless of people count
elif price_type == 'per_person':
    total_price = base_price * num_people  # Multiply by number of guests
```

**Validation Rules:**
- `min_people` ≤ `standard_people` ≤ `max_people`
- If reservation has `num_people` outside `[min_people, max_people]`, show warning or block
- `base_price` must be > 0

**Use Cases:**
- Day pass packages for external visitors
- Premium packages with extra services
- Group packages with fixed pricing
- Seasonal special offers

**UI Labels:**
- "Paquete" (dropdown option)
- Show: "Paquete Premium - €89.00 por persona (2-4 pax)"

---

#### Type 3: Consumo Mínimo (Minimum Consumption)
**Description:** Minimum spend requirement - guests must consume at least X amount

**Configuration Fields:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `policy_name` | TEXT | Yes | Policy title | "Consumo Mínimo Fin de Semana" |
| `policy_description` | TEXT | No | Policy details | "Válido sábados y domingos temporada alta" |
| `minimum_amount` | DECIMAL | Yes | Minimum spend required | 50.00 |
| `calculation_type` | ENUM | Yes | 'per_reservation' or 'per_person' | 'per_person' |
| `furniture_type` | TEXT | No | Applies to specific furniture type | "balinesa" |
| `customer_type` | ENUM | No | Applies to 'interno', 'externo', or 'both' | 'externo' |
| `zone_id` | INTEGER | No | Specific zone restriction | 2 |
| `priority_order` | INTEGER | No | Priority when multiple policies match | 1 |
| `is_active` | BOOLEAN | Yes | Active status | 1 |
| `created_at` | TIMESTAMP | Auto | Creation timestamp | - |

**Calculation Logic:**
```python
if calculation_type == 'per_reservation':
    required_minimum = minimum_amount  # Total for entire reservation
elif calculation_type == 'per_person':
    required_minimum = minimum_amount * num_people  # Per guest
```

**Policy Matching Priority:**
When multiple policies could apply, use `priority_order` (lowest number = highest priority):
1. Specific furniture type + zone + customer type
2. Furniture type + customer type
3. Zone + customer type
4. Customer type only
5. Default policy

**Use Cases:**
- Weekend minimum consumption for balinesas
- High-season minimum spend requirements
- VIP zone minimum consumption
- External customer spend requirements

**UI Labels:**
- "Consumo Mínimo" (dropdown option)
- Show: "Consumo Mínimo: €50.00 por persona"

---

### Database Schema Changes

#### New Table: `beach_packages`
```sql
CREATE TABLE beach_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name TEXT NOT NULL,
    package_description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    price_type TEXT NOT NULL CHECK(price_type IN ('per_package', 'per_person')),
    min_people INTEGER NOT NULL DEFAULT 1,
    standard_people INTEGER NOT NULL DEFAULT 2,
    max_people INTEGER NOT NULL DEFAULT 4,
    furniture_types_included TEXT,  -- Comma-separated furniture type codes
    customer_type TEXT CHECK(customer_type IN ('interno', 'externo', 'both')),
    zone_id INTEGER REFERENCES beach_zones(id),
    valid_from DATE,
    valid_until DATE,
    active INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_people_range CHECK(min_people <= standard_people AND standard_people <= max_people),
    CONSTRAINT valid_price CHECK(base_price > 0)
)
```

**Indexes:**
```sql
CREATE INDEX idx_packages_active ON beach_packages(active, display_order);
CREATE INDEX idx_packages_customer_zone ON beach_packages(customer_type, zone_id);
CREATE INDEX idx_packages_dates ON beach_packages(valid_from, valid_until);
```

---

#### Update Table: `beach_minimum_consumption_policies`
```sql
-- Add new field (already exists, just documenting expected structure)
ALTER TABLE beach_minimum_consumption_policies
ADD COLUMN calculation_type TEXT DEFAULT 'per_reservation'
CHECK(calculation_type IN ('per_reservation', 'per_person'));
```

Expected full structure:
```sql
CREATE TABLE beach_minimum_consumption_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_name TEXT NOT NULL,
    policy_description TEXT,
    minimum_amount DECIMAL(10,2) NOT NULL,
    calculation_type TEXT DEFAULT 'per_reservation' CHECK(calculation_type IN ('per_reservation', 'per_person')),
    furniture_type TEXT,
    customer_type TEXT CHECK(customer_type IN ('interno', 'externo', 'both')),
    zone_id INTEGER REFERENCES beach_zones(id),
    priority_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:**
```sql
CREATE INDEX idx_min_consumption_priority ON beach_minimum_consumption_policies(priority_order, is_active);
CREATE INDEX idx_min_consumption_lookup ON beach_minimum_consumption_policies(furniture_type, customer_type, zone_id, is_active);
```

---

#### Update Table: `beach_reservations`
```sql
-- Add new fields for reservation type tracking
ALTER TABLE beach_reservations ADD COLUMN reservation_type TEXT DEFAULT 'incluido'
    CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo'));

ALTER TABLE beach_reservations ADD COLUMN package_id INTEGER
    REFERENCES beach_packages(id);

ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_policy_id INTEGER
    REFERENCES beach_minimum_consumption_policies(id);

ALTER TABLE beach_reservations ADD COLUMN calculated_price DECIMAL(10,2) DEFAULT 0.00;

ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_amount DECIMAL(10,2) DEFAULT 0.00;

-- Note: Keep existing fields for backward compatibility:
-- price, final_price, payment_status, charge_to_room, etc.
```

**Field Descriptions:**

| Field | Purpose | Example |
|-------|---------|---------|
| `reservation_type` | Selected type at booking | 'paquete' |
| `package_id` | FK to selected package (if type='paquete') | 5 |
| `minimum_consumption_policy_id` | FK to policy (if type='consumo_minimo') | 3 |
| `calculated_price` | Auto-calculated price at creation time | 178.00 |
| `minimum_consumption_amount` | Calculated minimum spend required | 100.00 |

---

### Implementation Roadmap

#### Phase 1: Database & Models (Week 1)
**Goal:** Set up database schema and data access layer

**Tasks:**
- [ ] Create migration script for schema changes
  - [ ] Create `beach_packages` table
  - [ ] Update `beach_minimum_consumption_policies` table
  - [ ] Add new columns to `beach_reservations`
  - [ ] Create indexes
- [ ] Create `models/package.py` - Package CRUD operations
  - [ ] `get_all_packages(active_only=True, customer_type=None, zone_id=None)`
  - [ ] `get_package_by_id(package_id)`
  - [ ] `get_applicable_packages(customer_type, zone_id, reservation_date, num_people)`
  - [ ] `create_package(**data)`
  - [ ] `update_package(package_id, **data)`
  - [ ] `delete_package(package_id)`
  - [ ] `validate_package_capacity(package_id, num_people)`
- [ ] Update `models/pricing.py` - Enhance pricing functions
  - [ ] `calculate_package_price(package_id, num_people) -> dict`
  - [ ] `calculate_minimum_consumption(policy_id, num_people) -> float`
  - [ ] `get_applicable_minimum_consumption_policy(furniture_type, customer_type, zone_id) -> dict`
  - [ ] `update_minimum_consumption_policy(policy_id, **data)`
  - [ ] `create_minimum_consumption_policy(**data)`
- [ ] Add seed data for testing
  - [ ] 3-5 sample packages
  - [ ] 2-3 minimum consumption policies

**Validation Rules:**
```python
# In models/package.py
def validate_package_capacity(package_id: int, num_people: int) -> tuple[bool, str]:
    """
    Validate if num_people fits package capacity.

    Returns:
        (is_valid, error_message)
    """
    package = get_package_by_id(package_id)
    if num_people < package['min_people']:
        return False, f"Mínimo {package['min_people']} personas para este paquete"
    if num_people > package['max_people']:
        return False, f"Máximo {package['max_people']} personas para este paquete"
    return True, ""
```

---

#### Phase 2: Configuration UI (Week 2)
**Goal:** Admin interface for managing packages and policies

**Tasks:**
- [ ] Create config route: `blueprints/beach/routes/config/packages.py`
  - [ ] `GET /beach/config/packages` - List all packages (table view)
  - [ ] `GET /beach/config/packages/new` - Create package form
  - [ ] `POST /beach/config/packages` - Save new package
  - [ ] `GET /beach/config/packages/<id>/edit` - Edit package form
  - [ ] `POST /beach/config/packages/<id>` - Update package
  - [ ] `POST /beach/config/packages/<id>/delete` - Soft delete (set active=0)
  - [ ] `POST /beach/config/packages/<id>/toggle` - Toggle active status
- [ ] Create config route: `blueprints/beach/routes/config/minimum_consumption.py`
  - [ ] `GET /beach/config/minimum-consumption` - List policies
  - [ ] `GET /beach/config/minimum-consumption/new` - Create policy form
  - [ ] `POST /beach/config/minimum-consumption` - Save policy
  - [ ] `GET /beach/config/minimum-consumption/<id>/edit` - Edit form
  - [ ] `POST /beach/config/minimum-consumption/<id>` - Update policy
  - [ ] `POST /beach/config/minimum-consumption/<id>/delete` - Delete policy
- [ ] Create templates:
  - [ ] `templates/beach/config/packages/list.html` - Package list table
  - [ ] `templates/beach/config/packages/form.html` - Package create/edit form
  - [ ] `templates/beach/config/minimum_consumption/list.html` - Policy list
  - [ ] `templates/beach/config/minimum_consumption/form.html` - Policy form
- [ ] Add permissions:
  - [ ] `beach.config.packages.view`
  - [ ] `beach.config.packages.create`
  - [ ] `beach.config.packages.edit`
  - [ ] `beach.config.packages.delete`
  - [ ] `beach.config.minimum_consumption.view`
  - [ ] `beach.config.minimum_consumption.manage`
- [ ] Navigation menu updates:
  - [ ] Add "Paquetes" under "Configuración"
  - [ ] Add "Consumo Mínimo" under "Configuración"

**UI Components:**

**Package List Table:**
```
| Nombre              | Tipo Precio  | Precio Base | Capacidad | Tipo Cliente | Zona  | Estado   | Acciones |
|---------------------|--------------|-------------|-----------|--------------|-------|----------|----------|
| Paquete Premium     | Por persona  | €89.00      | 2-4 pax   | Externo      | VIP   | Activo   | [Edit] [Toggle] |
| Día de Playa        | Por paquete  | €150.00     | 1-6 pax   | Ambos        | Todas | Activo   | [Edit] [Toggle] |
```

**Package Form Fields:**
- Nombre del Paquete* (text input)
- Descripción (textarea)
- Precio Base* (number input with € symbol)
- Tipo de Precio* (radio buttons: "Por Paquete" / "Por Persona")
- Capacidad:
  - Mínimo de Personas* (number)
  - Estándar (Recomendado)* (number)
  - Máximo de Personas* (number)
- Tipo de Cliente (dropdown: "Interno" / "Externo" / "Ambos")
- Zona (dropdown: "Todas" / specific zones)
- Muebles Incluidos (multi-select: hamaca, balinesa, sombrilla, etc.)
- Vigencia:
  - Válido Desde (date picker)
  - Válido Hasta (date picker)
- Estado (checkbox: "Activo")

**Minimum Consumption Form Fields:**
- Nombre de Política* (text input)
- Descripción (textarea)
- Monto Mínimo* (number input with €)
- Tipo de Cálculo* (radio: "Por Reserva" / "Por Persona")
- Tipo de Mueble (dropdown: "Todos" / specific furniture types)
- Tipo de Cliente (dropdown: "Interno" / "Externo" / "Ambos")
- Zona (dropdown: "Todas" / specific zones)
- Prioridad (number input, lower = higher priority)
- Estado (checkbox: "Activa")

---

#### Phase 3: Reservation Form Integration (Week 3)
**Goal:** Add reservation type selection to booking flow

**Tasks:**
- [ ] Update reservation creation form UI
  - [ ] Add "Tipo de Reserva" section at top of form (after customer selection)
  - [ ] Radio buttons for 3 types: "Incluido" / "Paquete" / "Consumo Mínimo"
  - [ ] Show/hide sections based on selected type
- [ ] Package selection (when type='paquete')
  - [ ] Dropdown populated with applicable packages
  - [ ] Filter by: customer_type, zone_id (if selected), reservation_date, active=1
  - [ ] Display format: "Paquete Premium - €89.00/persona (2-4 pax)"
  - [ ] On package change: validate num_people, update calculated price
  - [ ] Show package description below dropdown
- [ ] Minimum consumption display (when type='consumo_minimo')
  - [ ] Auto-select applicable policy based on furniture, customer, zone
  - [ ] Display: "Consumo Mínimo: €50.00 por persona (Total: €100.00)"
  - [ ] Read-only display (auto-calculated)
  - [ ] Show policy description if available
- [ ] Price calculation display
  - [ ] Real-time price calculation as user selects options
  - [ ] Show breakdown:
    ```
    Tipo: Paquete Premium (2 personas)
    Precio Base: €89.00 × 2 = €178.00
    ────────────────────────────
    Total: €178.00
    ```
  - [ ] For minimum consumption, show:
    ```
    Consumo Mínimo Requerido: €100.00
    (No hay cargo por reserva, se aplica consumo mínimo)
    ```
- [ ] Form validation
  - [ ] If type='paquete', package_id required
  - [ ] Validate num_people within package capacity
  - [ ] Show warning if outside standard_people range
- [ ] Update `blueprints/beach/routes/reservations.py`
  - [ ] Modify `create_reservation()` to handle new fields
  - [ ] Save `reservation_type`, `package_id`, `minimum_consumption_policy_id`
  - [ ] Calculate and save `calculated_price`, `minimum_consumption_amount`
- [ ] JavaScript enhancements
  - [ ] `static/js/reservation_pricing.js` - Price calculation logic
  - [ ] AJAX call to `/api/packages/<id>/calculate` for real-time pricing
  - [ ] AJAX call to `/api/minimum-consumption/calculate` for policy lookup
  - [ ] Dynamic form section visibility toggle

**API Endpoints for AJAX:**
```python
# In blueprints/beach/routes/api/pricing.py (new file)

@api_bp.route('/packages/<int:package_id>/calculate', methods=['POST'])
def calculate_package_price_api(package_id):
    """
    Calculate price for package with given number of people.

    POST body: {"num_people": 2}
    Response: {"price": 178.00, "price_per_person": 89.00, "breakdown": "..."}
    """
    pass

@api_bp.route('/minimum-consumption/calculate', methods=['POST'])
def calculate_minimum_consumption_api():
    """
    Get applicable minimum consumption policy.

    POST body: {
        "furniture_type": "balinesa",
        "customer_type": "externo",
        "zone_id": 3,
        "num_people": 2
    }
    Response: {
        "policy_id": 5,
        "policy_name": "...",
        "minimum_amount": 100.00,
        "per_person": 50.00
    }
    """
    pass

@api_bp.route('/packages/applicable', methods=['GET'])
def get_applicable_packages_api():
    """
    Get list of applicable packages for filter criteria.

    Query params: ?customer_type=externo&zone_id=3&date=2025-07-15&num_people=2
    Response: [{"id": 1, "name": "...", "price": 89.00, ...}, ...]
    """
    pass
```

---

#### Phase 4: Display & Reporting (Week 4)
**Goal:** Show pricing info in reservation views and reports

**Tasks:**
- [ ] Update reservation list view
  - [ ] Add "Tipo" column showing reservation type badge
  - [ ] Add "Precio" column showing calculated_price
  - [ ] Add filter: "Tipo de Reserva" (dropdown)
  - [ ] Color-code types:
    - Incluido: Green badge
    - Paquete: Gold badge
    - Consumo Mínimo: Blue badge
- [ ] Update reservation detail view
  - [ ] Show pricing section:
    ```
    ┌─ Información de Precio ────────────┐
    │ Tipo: Paquete Premium              │
    │ Precio Base: €89.00 por persona    │
    │ Personas: 2                        │
    │ Total Calculado: €178.00           │
    │                                    │
    │ Descripción: 2 hamacas + sombrilla │
    │              + toallas + bebida     │
    └────────────────────────────────────┘
    ```
  - [ ] For minimum consumption, show required amount and calculation
- [ ] Update map view
  - [ ] Show pricing indicator on reservation tooltip
  - [ ] Example: "Reserva #25011601 - Paquete Premium (€178.00)"
- [ ] Export updates
  - [ ] Add pricing fields to Excel export
  - [ ] Add pricing section to PDF reservation tickets
- [ ] Reporting queries
  - [ ] Revenue projection (calculated_price × reservations)
  - [ ] Package popularity report
  - [ ] Minimum consumption compliance tracking (future: actual vs. required)

---

#### Phase 5: Testing & Validation (Week 5)
**Goal:** Comprehensive testing and edge case handling

**Tasks:**
- [ ] Unit tests
  - [ ] `tests/unit/test_package_model.py`
    - Test CRUD operations
    - Test capacity validation
    - Test price calculation (per package vs per person)
    - Test date range filtering
  - [ ] `tests/unit/test_minimum_consumption.py`
    - Test policy matching priority
    - Test calculation (per reservation vs per person)
    - Test multiple policy scenarios
  - [ ] `tests/unit/test_reservation_pricing.py`
    - Test reservation creation with each type
    - Test price calculation at booking time
    - Test validation rules
- [ ] Integration tests
  - [ ] `tests/integration/test_reservation_flow.py`
    - Test full booking flow with each reservation type
    - Test type switching during edit
    - Test multi-day reservations with packages
- [ ] UI/UX tests
  - [ ] Manual testing of all forms
  - [ ] Test responsive design on mobile
  - [ ] Test JavaScript price calculation
  - [ ] Test error messages and validation
- [ ] Edge cases
  - [ ] Package with no applicable packages (customer/zone mismatch)
  - [ ] Multiple overlapping minimum consumption policies
  - [ ] Package capacity exceeded during multi-day reservation
  - [ ] Date range edge cases (valid_from/valid_until)
- [ ] Data migration testing
  - [ ] Test migration on copy of production data
  - [ ] Verify backward compatibility (existing reservations still work)
  - [ ] Test rollback procedure

---

### UI/UX Design Specifications

#### Reservation Type Selection (Reservation Form)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Tipo de Reserva *                                       │
│                                                         │
│ ○ Incluido en Reserva                                   │
│   Sin cargo - incluido en paquete hotelero             │
│                                                         │
│ ● Paquete                                               │
│   Seleccionar paquete con servicios incluidos          │
│   ┌─────────────────────────────────────────────────┐  │
│   │ Paquete: [Dropdown]                       ▼    │  │
│   └─────────────────────────────────────────────────┘  │
│   📦 Paquete Premium                                   │
│   2 hamacas + sombrilla + toallas + bebida             │
│   €89.00 por persona | Capacidad: 2-4 personas         │
│                                                         │
│   💰 Precio Calculado: €178.00 (2 personas)            │
│                                                         │
│ ○ Consumo Mínimo                                        │
│   Consumo mínimo requerido sin cargo inicial           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Behavior:**
- Default selection based on `customer_type`:
  - Interno → "Incluido en Reserva" selected by default
  - Externo → "Paquete" or "Consumo Mínimo" (first available)
- Show/hide package dropdown only when "Paquete" selected
- Real-time price calculation on:
  - Package selection change
  - Number of people change
- Visual feedback:
  - Gray out unavailable options (no applicable packages/policies)
  - Show loading spinner during AJAX price calculation
  - Validation errors in red below field

---

#### Package Configuration Form

**Design Guidelines:**
- Use Design System colors (Primary Gold: #D4AF37)
- Form validation on blur and submit
- Help text in gray below each field
- Required fields marked with *
- Section dividers with headers

**Example:**
```
┌─ Información General ───────────────────────────────────┐
│ Nombre del Paquete *                                    │
│ [_____________________________________________]          │
│ Ej: "Paquete Premium", "Día de Playa VIP"              │
│                                                         │
│ Descripción                                             │
│ [_______________________________________________]        │
│ [_______________________________________________]        │
│ [_______________________________________________]        │
│ Describe servicios incluidos (opcional)                 │
└─────────────────────────────────────────────────────────┘

┌─ Precio y Capacidad ────────────────────────────────────┐
│ Precio Base * €                                         │
│ [_______]                                               │
│                                                         │
│ Tipo de Precio *                                        │
│ ● Por Paquete (precio fijo)                             │
│ ○ Por Persona (precio × personas)                       │
│                                                         │
│ Capacidad de Personas *                                 │
│ Mínimo:    [__] Estándar: [__] Máximo: [__]           │
│ Ej: 1-2 personas, 2-4 personas, 1-6 personas           │
└─────────────────────────────────────────────────────────┘

┌─ Aplicabilidad ─────────────────────────────────────────┐
│ Tipo de Cliente                                         │
│ [Dropdown: Ambos ▼]                                     │
│                                                         │
│ Zona                                                    │
│ [Dropdown: Todas las zonas ▼]                           │
│                                                         │
│ Muebles Incluidos                                       │
│ ☑ Hamaca  ☑ Sombrilla  ☐ Balinesa  ☐ Toallas          │
└─────────────────────────────────────────────────────────┘

┌─ Vigencia ──────────────────────────────────────────────┐
│ Válido Desde         Válido Hasta                       │
│ [01/06/2025]        [30/09/2025]                       │
│                                                         │
│ ☑ Activo                                                │
└─────────────────────────────────────────────────────────┘

[Guardar Paquete]  [Cancelar]
```

---

### Business Logic & Calculation Examples

#### Example 1: Package Pricing (Per Person)
```python
# Package: "Paquete Premium"
# base_price: 89.00
# price_type: 'per_person'
# min_people: 2, standard_people: 2, max_people: 4

# Reservation: 2 people
calculated_price = 89.00 * 2 = €178.00

# Reservation: 4 people
calculated_price = 89.00 * 4 = €356.00

# Reservation: 1 person - ERROR
# Error: "Mínimo 2 personas para este paquete"
```

#### Example 2: Package Pricing (Per Package)
```python
# Package: "Día de Playa Familiar"
# base_price: 250.00
# price_type: 'per_package'
# min_people: 1, standard_people: 4, max_people: 6

# Reservation: 2 people
calculated_price = €250.00 (fixed)

# Reservation: 6 people
calculated_price = €250.00 (fixed)

# Same price regardless of people count (within capacity)
```

#### Example 3: Minimum Consumption (Per Person)
```python
# Policy: "Consumo Mínimo Balinesa Fin de Semana"
# minimum_amount: 50.00
# calculation_type: 'per_person'
# furniture_type: 'balinesa'
# customer_type: 'externo'

# Reservation: 2 people, furniture_type='balinesa', customer_type='externo'
minimum_consumption_amount = 50.00 * 2 = €100.00
calculated_price = 0.00  # No upfront charge

# UI shows: "Consumo Mínimo Requerido: €100.00 (€50.00 por persona)"
```

#### Example 4: Policy Priority Matching
```python
# Multiple policies in system:
# Policy A: furniture_type='balinesa', customer_type='externo', zone_id=3, priority=1
# Policy B: furniture_type='balinesa', customer_type='externo', zone_id=NULL, priority=2
# Policy C: customer_type='externo', priority=3

# Reservation: balinesa, externo, zone_id=3
# → Matches Policy A (most specific, lowest priority number)

# Reservation: balinesa, externo, zone_id=5
# → Matches Policy B (furniture + customer match, zone NULL = all zones)

# Reservation: hamaca, externo, zone_id=3
# → Matches Policy C (only customer type matches)
```

---

### Technical Decisions

#### Decision 1: Reservation Type Enum
**Choice:** Use TEXT column with CHECK constraint vs. separate pricing type tables

**Decision:** Use ENUM-style TEXT field `reservation_type` with CHECK constraint

**Rationale:**
- Simple 3-option enum, unlikely to grow significantly
- Easy to query and filter
- No JOIN overhead for common queries
- CHECK constraint ensures data integrity

**Implementation:**
```sql
reservation_type TEXT DEFAULT 'incluido'
    CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo'))
```

---

#### Decision 2: Price Calculation Timing
**Choice:** Calculate on save vs. recalculate on read

**Decision:** Calculate once on reservation creation, store in `calculated_price`

**Rationale:**
- Price at booking time is final (audit trail)
- Packages/policies may change later, shouldn't affect existing reservations
- Faster queries (no real-time calculation on list views)
- Historical accuracy for reporting

**Implementation:**
- Calculate price when creating/editing reservation
- Store result in `calculated_price`
- Display stored value (not recalculated)
- Exception: Allow manual override if needed (future feature)

---

#### Decision 3: Package Applicability Filtering
**Choice:** Client-side vs. server-side filtering

**Decision:** Hybrid approach - server-side initial filter, client-side refinement

**Rationale:**
- Server-side: Filter by customer_type, zone_id, active, date_range (reduces payload)
- Client-side: Filter by num_people validation (better UX, no extra API calls)
- Best of both worlds: Performance + user experience

**Implementation:**
```javascript
// On page load: fetch applicable packages via AJAX
// Filter: customer_type, zone_id, reservation_date, active=1

// On num_people change: client-side validation
// Check if num_people within [min_people, max_people]
// Disable packages outside capacity range
```

---

#### Decision 4: Minimum Consumption Policy Storage
**Choice:** Denormalize policy data vs. FK reference only

**Decision:** Store both `minimum_consumption_policy_id` (FK) and `minimum_consumption_amount` (denormalized)

**Rationale:**
- Policy details may change over time
- Need snapshot of amount at booking time
- Faster queries (no JOIN for amount lookup)
- Maintains audit trail

**Trade-offs:**
- Slight data redundancy
- Acceptable for historical accuracy

---

### Questions to Resolve

**Business Logic:**
1. Can users manually override calculated price? (e.g., special discount)
2. What happens if package is deactivated after reservation created? (Display only? Prevent edit?)
3. Should minimum consumption be enforced? (Or just informational?)
4. Can a reservation type be changed after creation? (e.g., Incluido → Paquete)
5. How to handle multi-day reservations with packages? (Same package for all days? Or daily selection?)

**Configuration:**
6. Should packages have seasonal pricing? (e.g., high season vs. low season)
7. Can packages include extra add-ons? (e.g., +€20 for champagne)
8. Should there be package categories/tags? (e.g., "Premium", "Familiar", "Romántico")
9. Maximum number of active packages? (UI pagination if many)
10. Should policies have effective dates? (Not just valid_from/until, but day-of-week rules?)

**UI/UX:**
11. Show package comparison table before selection? (Side-by-side comparison)
12. Allow guest to see prices before creating reservation? (Public pricing page?)
13. How to display pricing on map view? (Too cluttered if showing all prices)
14. Mobile-optimized package selection? (Current design assumes desktop)

**Technical:**
15. Should we cache package/policy lookups? (High read, low write - good candidate)
16. Need API endpoint for external systems to query prices? (Future integration)
17. Audit log for pricing changes? (Track when packages/policies are modified)
18. Export format for pricing reports? (Excel? PDF? Both?)

---

### Migration Strategy

#### Step 1: Schema Migration (Non-breaking)
```sql
-- Run these migrations in order:
BEGIN TRANSACTION;

-- 1. Create new beach_packages table
CREATE TABLE beach_packages (...);

-- 2. Update beach_minimum_consumption_policies
ALTER TABLE beach_minimum_consumption_policies
    ADD COLUMN calculation_type TEXT DEFAULT 'per_reservation';

-- 3. Add new columns to beach_reservations (nullable initially)
ALTER TABLE beach_reservations ADD COLUMN reservation_type TEXT DEFAULT 'incluido';
ALTER TABLE beach_reservations ADD COLUMN package_id INTEGER;
ALTER TABLE beach_reservations ADD COLUMN calculated_price DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_amount DECIMAL(10,2) DEFAULT 0.00;

-- 4. Create indexes
CREATE INDEX idx_packages_active ON beach_packages(active, display_order);
-- ... (all other indexes)

COMMIT;
```

#### Step 2: Data Migration (Existing Reservations)
```sql
-- Set default reservation_type for existing reservations
UPDATE beach_reservations
SET reservation_type = CASE
    WHEN (SELECT customer_type FROM beach_customers WHERE id = customer_id) = 'interno'
    THEN 'incluido'
    ELSE 'incluido'  -- Default all to 'incluido' for safety
END
WHERE reservation_type IS NULL;
```

#### Step 3: Seed Sample Data
```python
# In database/seed_pricing.py (new file)

sample_packages = [
    {
        "package_name": "Paquete Premium",
        "package_description": "2 hamacas + sombrilla + toallas + bebida de bienvenida",
        "base_price": 89.00,
        "price_type": "per_person",
        "min_people": 2,
        "standard_people": 2,
        "max_people": 4,
        "customer_type": "externo",
        "active": 1,
        "display_order": 1
    },
    # ... more samples
]

# Insert sample data
```

---

### Success Metrics

**Phase Completion Criteria:**
- ✅ All database migrations run successfully
- ✅ All unit tests pass (>90% coverage for pricing logic)
- ✅ All 3 reservation types can be created via UI
- ✅ Price calculation is accurate for all scenarios
- ✅ Config UI allows CRUD operations for packages and policies
- ✅ Reservation form shows pricing in real-time
- ✅ Existing reservations still work (backward compatibility)

**User Acceptance:**
- Staff can create packages in <2 minutes
- Reservation creation with package adds <10 seconds to workflow
- Zero calculation errors in production (first month)
- Positive feedback from staff on pricing clarity

---

## Insights & Analytics Planning

### Overview
Business intelligence and analytics module to provide actionable insights for beach club operations, revenue optimization, and customer experience enhancement.

### Available Data Sources

Based on existing database schema:

**Operational Data:**
- `beach_reservations` - Booking history, dates, pricing
- `beach_reservation_furniture` - Daily furniture assignments
- `beach_reservation_daily_states` - State transitions per day
- `beach_reservation_states` - State definitions

**Customer Data:**
- `beach_customers` - Customer profiles (interno/externo)
- `hotel_guests` - PMS integration data
- `beach_customer_preferences` - Preference mappings
- `beach_customer_tags` - Segmentation tags

**Infrastructure Data:**
- `beach_furniture` - Furniture inventory with positions
- `beach_furniture_types` - Hamaca, balinesa, etc.
- `beach_zones` - Zone hierarchy
- `beach_furniture_blocks` - Decorative furniture

**Financial Data:**
- `beach_price_catalog` - Pricing rules by type/customer
- `beach_minimum_consumption_policies` - Minimum spend rules

**System Data:**
- `audit_log` - User actions and changes

---

### Insight Categories

#### 1. Occupancy & Capacity Analytics
**Business Value:** Optimize furniture placement, staffing, and capacity planning

**Key Metrics:**
- Daily/weekly/monthly occupancy rate (%)
- Peak vs. off-peak utilization
- Occupancy by zone
- Occupancy by furniture type
- Average booking lead time
- No-show rate by customer type

**Visualizations:**
- Heatmap: Occupancy by day of week × hour
- Line chart: Occupancy trends over time
- Bar chart: Zone comparison
- Donut chart: Furniture type distribution

**Data Queries:**
```sql
-- Occupancy rate by date
SELECT
    assignment_date,
    COUNT(DISTINCT furniture_id) as occupied_count,
    (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1) as total_furniture,
    ROUND(COUNT(DISTINCT furniture_id) * 100.0 /
          (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1), 2) as occupancy_rate
FROM beach_reservation_furniture
WHERE assignment_date BETWEEN ? AND ?
GROUP BY assignment_date
```

---

#### 2. Revenue Analytics
**Business Value:** Track revenue performance, identify high-value segments

**Key Metrics:**
- Daily/weekly/monthly revenue
- Revenue by customer type (interno vs externo)
- Revenue by zone
- Revenue by furniture type
- Average revenue per reservation
- Revenue per available furniture unit (RevPAR equivalent)

**Visualizations:**
- Stacked area chart: Revenue breakdown by customer type
- Bar chart: Revenue by zone
- KPI cards: Total revenue, RevPAR, avg. booking value
- Comparison: Current period vs. previous period

**Data Queries:**
```sql
-- Revenue by customer type
SELECT
    c.customer_type,
    COUNT(r.id) as reservation_count,
    SUM(r.total_price) as total_revenue,
    AVG(r.total_price) as avg_revenue_per_reservation
FROM beach_reservations r
JOIN beach_customers c ON r.customer_id = c.id
WHERE r.start_date BETWEEN ? AND ?
    AND r.state_id NOT IN (SELECT id FROM beach_reservation_states WHERE is_availability_releasing = 1)
GROUP BY c.customer_type
```

---

#### 3. Customer Behavior Analytics
**Business Value:** Improve customer experience, personalization, and retention

**Key Metrics:**
- Customer segmentation (new vs. returning)
- Booking frequency per customer
- Average party size
- Preferred zones/furniture types
- Preference utilization rate
- Tag distribution

**Visualizations:**
- Pie chart: Customer type breakdown
- Histogram: Booking frequency distribution
- Tag cloud: Popular tags
- Table: Top customers by booking count/revenue

**Data Queries:**
```sql
-- Customer segmentation
SELECT
    customer_type,
    CASE
        WHEN booking_count = 1 THEN 'New'
        WHEN booking_count BETWEEN 2 AND 5 THEN 'Regular'
        ELSE 'VIP'
    END as segment,
    COUNT(*) as customer_count
FROM (
    SELECT c.id, c.customer_type, COUNT(r.id) as booking_count
    FROM beach_customers c
    LEFT JOIN beach_reservations r ON c.id = r.customer_id
    GROUP BY c.id, c.customer_type
)
GROUP BY customer_type, segment
```

---

#### 4. Booking Patterns & Trends
**Business Value:** Forecast demand, optimize pricing strategies

**Key Metrics:**
- Booking lead time distribution
- Cancellation rate by lead time
- Multi-day vs. single-day booking ratio
- Booking source analysis (if tracked)
- Seasonal trends
- Day-of-week patterns

**Visualizations:**
- Line chart: Bookings over time with trend line
- Histogram: Lead time distribution
- Heatmap: Bookings by month × day of week
- Funnel chart: Booking state transitions

---

#### 5. Operational Efficiency
**Business Value:** Streamline operations, reduce manual work

**Key Metrics:**
- State transition times (Pendiente → Confirmada → Check-in)
- Average check-in/check-out duration
- Cancellation rate by state
- Furniture change frequency (reassignments)
- User activity (from audit_log)

**Visualizations:**
- Sankey diagram: State flow
- Bar chart: Cancellation reasons (if tracked)
- Table: User activity summary

---

### Implementation Roadmap

#### Phase 1: Foundation (Week 1-2)
**Goal:** Basic analytics infrastructure

- [ ] Create `blueprints/beach/routes/insights.py` - Main insights routes
- [ ] Create `blueprints/beach/routes/api/insights.py` - API endpoints
- [ ] Create `models/insights.py` - Analytics queries
- [ ] Create base template `templates/beach/insights/dashboard.html`
- [ ] Add permission: `beach.insights.view`
- [ ] Navigation menu item for "Analíticas" / "Insights"

**Technical Decisions:**
- Use Chart.js for visualizations (already in stack, lightweight)
- Date range selector: Default to last 30 days
- Caching: 15-minute TTL for expensive queries
- Export: JSON API for all charts (future Excel/PDF export)

---

#### Phase 2: Core Metrics (Week 3-4)
**Goal:** Implement occupancy and revenue analytics

- [ ] Occupancy dashboard with date range filter
  - [ ] Occupancy rate KPI card
  - [ ] Occupancy by zone chart
  - [ ] Occupancy trend line
  - [ ] Occupancy heatmap (day × time)
- [ ] Revenue dashboard
  - [ ] Revenue KPI cards (total, RevPAR, avg booking)
  - [ ] Revenue by customer type chart
  - [ ] Revenue by zone chart
  - [ ] Period comparison (vs. previous period)

**Queries to implement:**
```python
# In models/insights.py
def get_occupancy_stats(start_date, end_date, zone_id=None)
def get_revenue_stats(start_date, end_date, group_by='day')
def get_revenue_by_customer_type(start_date, end_date)
def get_revenue_by_zone(start_date, end_date)
```

---

#### Phase 3: Customer Analytics (Week 5-6)
**Goal:** Customer segmentation and behavior insights

- [ ] Customer analytics dashboard
  - [ ] Customer segmentation chart
  - [ ] Top customers table (sortable)
  - [ ] Preference utilization stats
  - [ ] Tag distribution chart
- [ ] Customer detail insights (individual customer view)
  - [ ] Booking history timeline
  - [ ] Preference match rate
  - [ ] Revenue contribution

---

#### Phase 4: Advanced Analytics (Week 7-8)
**Goal:** Predictive insights and operational metrics

- [ ] Booking patterns dashboard
  - [ ] Lead time distribution
  - [ ] Seasonal trends
  - [ ] Day-of-week patterns
  - [ ] State transition funnel
- [ ] Operational dashboard
  - [ ] State transition times
  - [ ] Cancellation analysis
  - [ ] User activity summary
- [ ] Basic forecasting (moving average for demand prediction)

---

#### Phase 5: Reporting & Export (Week 9-10)
**Goal:** Shareable reports and data export

- [ ] Report builder interface
  - [ ] Select metrics and date ranges
  - [ ] Save custom report templates
  - [ ] Schedule reports (future: email delivery)
- [ ] Export functionality
  - [ ] Excel export (openpyxl)
  - [ ] PDF reports (ReportLab)
  - [ ] CSV data export
- [ ] Report templates
  - [ ] Daily operations summary
  - [ ] Weekly performance report
  - [ ] Monthly financial summary

---

### Design Considerations

**UI/UX:**
- Dashboard cards with clear KPIs and trend indicators (↑↓)
- Consistent color scheme: Gold (#D4AF37) for primary metrics
- Responsive charts (mobile-friendly)
- Loading states for async data fetching
- Empty states with helpful messages

**Performance:**
- Index optimization for date range queries
- Materialized views for complex aggregations (consider if needed)
- Pagination for large result sets
- Client-side chart rendering (reduce server load)

**Accessibility:**
- Screen reader support for charts (data tables as fallback)
- Keyboard navigation
- High contrast mode support

---

### Data Dictionary for Insights

**Key Calculated Fields:**

| Field | Formula | Description |
|-------|---------|-------------|
| `occupancy_rate` | `(occupied_furniture / total_active_furniture) × 100` | Percentage of furniture occupied |
| `revpar` | `total_revenue / total_active_furniture` | Revenue per available furniture unit |
| `no_show_rate` | `(no_show_count / total_reservations) × 100` | Percentage of no-shows |
| `cancellation_rate` | `(cancelled_count / total_reservations) × 100` | Percentage of cancellations |
| `avg_lead_time` | `AVG(start_date - created_at)` | Average booking advance notice |
| `avg_party_size` | `AVG(number_of_people)` | Average guests per reservation |
| `preference_match_rate` | `(preferences_matched / total_preferences) × 100` | How often preferences are met |

---

### Questions to Consider

**Business Questions:**
1. What are the 3 most important metrics for daily operations?
2. Who is the primary audience? (Manager, staff, admin, owner)
3. Should insights be role-based? (Different dashboards for different roles)
4. Are there specific benchmarks or targets to track against?
5. What time ranges are most important? (Daily, weekly, monthly, seasonal)

**Technical Questions:**
1. Should we implement real-time updates (WebSocket) or is periodic refresh sufficient?
2. Do we need drill-down capabilities? (Click chart → detailed view)
3. Should we track user interactions with insights? (Most viewed, most exported)
4. Data retention: How far back should analytics go?
5. Should we implement data warehouse/OLAP for historical analysis?

---

### Future Enhancements

**Advanced Analytics:**
- Machine learning for demand forecasting
- Anomaly detection (unusual booking patterns)
- Customer lifetime value (CLV) prediction
- Churn prediction for returning customers
- Dynamic pricing recommendations

**Integrations:**
- Google Analytics integration (if web bookings exist)
- Weather data correlation (occupancy vs. weather)
- Competitive benchmarking (if industry data available)
- Social media sentiment analysis

**Visualizations:**
- Interactive map overlay with occupancy heatmap
- 3D furniture layout with utilization stats
- Gantt chart for reservation timeline
- Network graph for customer relationships

---

## Technical Decisions

### Analytics Architecture

**Choice: Embedded analytics vs. Separate BI tool**
- **Decision:** Embedded analytics within Flask app
- **Rationale:**
  - Full control over UI/UX
  - No additional licensing costs
  - Tight integration with existing auth/permissions
  - Simpler deployment
- **Trade-offs:** More development work vs. using pre-built BI tool

**Query Strategy:**
- **Decision:** SQL queries in models layer, cached results
- **Rationale:**
  - Leverage SQLite's excellent read performance
  - WAL mode supports concurrent reads
  - Simple caching strategy (TTL-based)
- **Trade-offs:** May need optimization for large datasets (>100k reservations)

**Charting Library:**
- **Decision:** Chart.js
- **Rationale:**
  - Open source, MIT license
  - Responsive out of the box
  - Good documentation
  - Matches design system colors
- **Alternatives considered:** D3.js (too complex), Plotly (heavier)

---

## Completed Items

### Core System (Completed)
- ✅ Database schema with 22 tables
- ✅ User authentication and role-based permissions
- ✅ Reservation management (single and multi-day)
- ✅ Customer management (interno/externo)
- ✅ Interactive map with drag-and-drop
- ✅ Furniture and zone configuration
- ✅ State management with configurable states
- ✅ Pricing catalog
- ✅ Hotel guest import (Excel)
- ✅ Audit logging

---

## Notes & Discoveries

**Date:** 2025-12-25
**Topic:** Payment & Pricing System Planning
**Notes:**
- Created comprehensive 5-phase implementation plan (5 weeks)
- Designed 3 reservation types: Incluido, Paquete, Consumo Mínimo
- Schema includes new `beach_packages` table + updates to existing tables
- Pricing logic: per-package vs per-person, with capacity validation
- Minimum consumption with priority-based policy matching
- Real-time price calculation via AJAX during reservation creation
- Backward compatible with existing reservations (all default to 'incluido')
- Questions to resolve: manual price override, package deactivation handling, multi-day package logic

**Date:** 2025-12-25
**Topic:** Initial insights planning
**Notes:**
- No existing analytics or reports module
- Rich data available across 22 tables
- Good foundation for comprehensive analytics
- Need to clarify business priorities before implementation

---

## Next Steps

### Payment & Pricing System (Priority 1)
1. **Review and answer business questions** in "Questions to Resolve" section
2. **Confirm technical approach** for all 4 decisions documented
3. **Begin Phase 1:** Database migrations and model creation
4. **Set up test data** with 3-5 sample packages and 2-3 policies
5. **Validate migration strategy** on test database copy

### Insights & Analytics (On Hold)
1. **Review this plan** and prioritize insight categories
2. **Answer business questions** in "Questions to Consider" section
3. **Begin Phase 1** implementation (if approved)
4. **Create wireframes/mockups** for dashboard layout

---

**How to use this document:**
- Update after each work session
- Mark items with ✅ when completed
- Add new discoveries in "Notes & Discoveries"
- Keep "Next Steps" current
- Reference this before starting any new feature
