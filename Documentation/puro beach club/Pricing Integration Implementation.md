# Pricing System Integration - Implementation Plan

**Project**: Integrate pricing system (packages + minimum consumption) with reservation system
**Date**: 2025-12-26
**Status**: Planning

---

## Overview

Integrate the existing pricing system with the reservation workflow to enable seamless, restriction-aware pricing during reservation creation. The system will support payment tracking via PMS/POS ticket numbers.

### Key Requirements

1. **Dynamic Pricing Selection**: Employees choose packages OR minimum consumption based on automatic restriction filtering
2. **Payment Tracking**: New field `payment_ticket_number` for PMS/POS ticket (separate from reservation ticket YYMMDDRR)
3. **Multi-Day Pricing**: **Same package/price for ALL linked reservations** (replicated across all days)
4. **Price Override**: Employees can always manually adjust calculated prices
5. **Restriction-Aware Filtering**: Packages automatically filtered by:
   - Customer type (interno/externo)
   - Selected furniture types
   - Zone
   - Date validity
   - Number of people (min/max range)

### Multi-Day Clarification

**Example**: Guest books 3 days with "Classic Package 30€/person"
- Day 1 (parent): Classic Package, 30€/person, 4 people = 120€
- Day 2 (child): Classic Package, 30€/person, 4 people = 120€
- Day 3 (child): Classic Package, 30€/person, 4 people = 120€

**All reservations get the SAME package and pricing.**

---

## Current System Analysis

### ✅ Already Implemented
- Pricing tables: `beach_packages`, `beach_minimum_consumption_policies`
- Package CRUD: Full admin UI at `/beach/config/pricing`
- Minimum consumption: Complete with priority-based matching
- Reservation pricing fields: `price`, `final_price`, `paid`, `charge_to_room`, `minimum_consumption_amount`, `minimum_consumption_policy_id`

### ❌ Missing
- `package_id` FK in `beach_reservations`
- `payment_ticket_number` field in `beach_reservations`
- Pricing calculation service
- Reservation form pricing UI section
- AJAX endpoints for real-time price calculation
- Reservation form template is TOO LARGE (27050 tokens) - needs splitting

---

## Implementation Phases

### Phase 1: Database Schema Changes

**File**: `database/migrations/pricing_integration.py` (NEW)

```sql
-- Add package_id foreign key
ALTER TABLE beach_reservations
ADD COLUMN package_id INTEGER REFERENCES beach_packages(id);

-- Add payment ticket number (PMS/POS ticket)
ALTER TABLE beach_reservations
ADD COLUMN payment_ticket_number TEXT;

-- Create indexes
CREATE INDEX idx_reservations_package ON beach_reservations(package_id);
CREATE INDEX idx_reservations_payment_ticket ON beach_reservations(payment_ticket_number)
    WHERE payment_ticket_number IS NOT NULL;
```

**Data Migration**:
```python
# Backfill: paid=1 if payment_status='SI', else paid=0
# Backfill: final_price = price where final_price IS NULL
```

**Status**: ⏳ Not Started

---

### Phase 2: Pricing Service Layer

**File**: `blueprints/beach/services/pricing_service.py` (NEW, ~350 lines)

**Purpose**: Centralize all pricing calculation logic

**Key Functions**:

#### 1. `get_eligible_packages(customer_type, furniture_ids, reservation_date, num_people)`
Filters packages by all restrictions and returns eligible list.

#### 2. `calculate_package_price(package_id, num_people)`
Calculates price:
- `per_package`: base_price (fixed)
- `per_person`: base_price × num_people

#### 3. `calculate_minimum_consumption(furniture_ids, customer_type, num_people)`
Uses priority-based matching to find applicable policy and calculates amount.

#### 4. `calculate_reservation_pricing(customer_type, furniture_ids, reservation_date, num_people, package_id=None)`
Main pricing calculation:
- Get eligible packages
- Calculate minimum consumption
- If package_id provided → package price
- Else → minimum consumption

Returns:
```python
{
    'pricing_mode': 'package' | 'minimum_consumption' | 'free',
    'package': {...} or None,
    'minimum_consumption': {...},
    'calculated_price': float,
    'eligible_packages': [...]
}
```

**Status**: ⏳ Not Started

---

### Phase 3: API Endpoints

**File**: `blueprints/beach/routes/api/pricing.py` (NEW, ~200 lines)

#### Endpoint 1: `POST /beach/api/pricing/calculate`
Real-time price calculation

**Request**:
```json
{
    "customer_type": "interno",
    "furniture_ids": [1, 2],
    "reservation_date": "2025-01-15",
    "num_people": 4,
    "package_id": 5
}
```

**Response**: Pricing object with calculated_price, package, minimum_consumption, eligible_packages

#### Endpoint 2: `GET /beach/api/pricing/packages/available`
Get eligible packages for dropdown population

**Status**: ⏳ Not Started

---

### Phase 4: Split Reservation Form Template

**Problem**: Current `reservation_form.html` is 27050 tokens (too large)

**Solution**: Split into focused partials

#### New Structure:

**Main**: `templates/beach/reservation_form.html` (~200 lines)
```html
{% extends "base.html" %}
{% block content %}
<form id="reservationForm">
    {% include 'beach/reservation_form/_step1_customer.html' %}
    {% include 'beach/reservation_form/_step2_details.html' %}
    {% include 'beach/reservation_form/_step3_pricing.html' %}
    {% include 'beach/reservation_form/_step4_confirm.html' %}
</form>
{% endblock %}
```

**Partial Files** (NEW):
1. `templates/beach/reservation_form/_step1_customer.html` - Customer selection (unified search)
2. `templates/beach/reservation_form/_step2_details.html` - Date, furniture, preferences, notes
3. `templates/beach/reservation_form/_step3_pricing.html` - **NEW** Pricing section
4. `templates/beach/reservation_form/_step4_confirm.html` - Review and submit

**Benefits**:
- Each file <500 lines
- Easier to maintain
- Clear separation of concerns
- Can reuse partials in edit mode

**Status**: ⏳ Not Started

---

### Phase 5: Pricing Section UI

**File**: `templates/beach/reservation_form/_step3_pricing.html` (NEW)

**UI Components**:

1. **Package Selector**
```html
<div class="form-group">
    <label>Paquete <small class="text-muted">(opcional)</small></label>
    <select id="packageSelect" name="package_id" class="form-select">
        <option value="">Sin paquete - Consumo mínimo</option>
        <!-- Populated via AJAX -->
    </select>
</div>
```

2. **Minimum Consumption Display**
```html
<div class="pricing-display">
    <label>Consumo Mínimo</label>
    <div class="amount">€<span id="minConsumptionAmount">0.00</span></div>
    <small id="minConsumptionPolicy" class="text-muted"></small>
</div>
```

3. **Price Calculation & Override**
```html
<div class="row">
    <div class="col-md-6">
        <label>Precio Calculado</label>
        <div id="calculatedPriceDisplay" class="h5">€0.00</div>
        <small id="priceBreakdown"></small>
    </div>
    <div class="col-md-6">
        <label for="finalPrice">Precio Final (editable)</label>
        <div class="input-group">
            <span class="input-group-text">€</span>
            <input type="number" id="finalPrice" name="final_price"
                   class="form-control" step="0.01" min="0" value="0.00">
        </div>
        <small class="text-muted">Puedes ajustar el precio</small>
    </div>
</div>
```

4. **Payment Section**
```html
<div class="payment-section">
    <h6>Información de Pago</h6>

    <!-- Paid checkbox -->
    <div class="form-check form-switch">
        <input type="checkbox" id="paidCheckbox" name="paid" value="1">
        <label for="paidCheckbox"><strong>Marcar como pagado</strong></label>
    </div>

    <!-- Payment ticket (PMS/POS) -->
    <div class="mb-3">
        <label for="paymentTicket">
            Número de Ticket PMS/POS
            <span id="ticketRequired" class="text-danger" style="display:none;">*</span>
        </label>
        <input type="text" id="paymentTicket" name="payment_ticket_number"
               class="form-control" placeholder="Ej: TPV12345" disabled>
        <small class="text-muted">
            <i class="fas fa-info-circle"></i>
            Diferente del ticket de reserva (YYMMDDRR)
        </small>
    </div>

    <!-- Charge to room (only for internos) -->
    <div class="row">
        <div class="col-md-6">
            <div class="form-check form-switch">
                <input type="checkbox" id="chargeToRoom" name="charge_to_room" value="1">
                <label for="chargeToRoom">Cargar a habitación</label>
            </div>
        </div>
        <div class="col-md-6">
            <input type="text" id="chargeReference" name="charge_reference"
                   class="form-control" placeholder="Referencia" disabled>
        </div>
    </div>
</div>

<!-- Hidden fields -->
<input type="hidden" id="calculatedPrice" name="price">
<input type="hidden" id="minConsumptionAmountField" name="minimum_consumption_amount">
<input type="hidden" id="minConsumptionPolicyId" name="minimum_consumption_policy_id">
```

**Status**: ⏳ Not Started

---

### Phase 6: JavaScript for Real-Time Pricing

**File**: `static/js/reservation_form_pricing.js` (NEW, ~300 lines)

**Key Functions**:

```javascript
// Calculate pricing via AJAX
function calculatePricing() {
    const data = {
        customer_type: getSelectedCustomerType(),
        furniture_ids: getSelectedFurniture(),
        reservation_date: $('#reservationDate').val(),
        num_people: $('#numPeople').val(),
        package_id: $('#packageSelect').val()
    };

    $.post('/beach/api/pricing/calculate', data, function(result) {
        updatePricingDisplay(result.pricing);
    });
}

// Update UI with calculated prices
function updatePricingDisplay(pricing) {
    $('#calculatedPriceDisplay').text('€' + pricing.calculated_price.toFixed(2));
    $('#finalPrice').val(pricing.calculated_price.toFixed(2));
    $('#minConsumptionAmount').text(pricing.minimum_consumption.minimum_amount.toFixed(2));
    // ... update other fields
}

// Populate package dropdown with eligible options
function updatePackageOptions(packages) {
    const select = $('#packageSelect');
    select.find('option:not(:first)').remove();
    packages.forEach(pkg => {
        select.append(`<option value="${pkg.id}">${pkg.package_name} - €${pkg.base_price}</option>`);
    });
}

// Validate payment ticket before submission
function validatePayment() {
    if ($('#paidCheckbox').is(':checked')) {
        const ticket = $('#paymentTicket').val().trim();
        if (!ticket) {
            alert('Número de ticket de pago requerido');
            return false;
        }
    }
    return true;
}
```

**Event Bindings**:
```javascript
// Recalculate on changes
$('#customerSelect, #numPeople, #reservationDate, .furniture-checkbox').on('change', calculatePricing);

// Package selection
$('#packageSelect').on('change', function() {
    calculatePricing();
});

// Payment ticket field toggle
$('#paidCheckbox').on('change', function() {
    $('#paymentTicket').prop('disabled', !this.checked);
    $('#ticketRequired').toggle(this.checked);
});

// Charge to room toggle
$('#chargeToRoom').on('change', function() {
    $('#chargeReference').prop('disabled', !this.checked);
});

// Form validation
$('#reservationForm').on('submit', validatePayment);
```

**Status**: ⏳ Not Started

---

### Phase 7: Model Updates

**File**: `models/reservation_crud.py` (MODIFY)

#### Update `create_beach_reservation()`

**Add Parameters**:
```python
package_id: int = None,
payment_ticket_number: str = None
```

**Add Validation**:
```python
# Validate payment ticket requirement
if paid and not payment_ticket_number:
    raise ValueError("Número de ticket de pago requerido para reservas pagadas")

# Validate package exists if provided
if package_id:
    from models.package import get_package_by_id
    package = get_package_by_id(package_id)
    if not package or not package['active']:
        raise ValueError("Paquete inválido o inactivo")
```

**Update INSERT**:
```sql
INSERT INTO beach_reservations (
    ..., package_id, payment_ticket_number, ...
) VALUES (..., ?, ?, ...)
```

#### Update `update_beach_reservation()`

Add to `allowed_fields`: `'package_id', 'payment_ticket_number'`

#### Update `get_beach_reservation_by_id()`

**Add JOINs**:
```sql
LEFT JOIN beach_packages p ON r.package_id = p.id
LEFT JOIN beach_minimum_consumption_policies mcp
    ON r.minimum_consumption_policy_id = mcp.id
```

**Add Columns**:
```sql
p.package_name,
p.base_price as package_base_price,
p.price_type as package_price_type,
mcp.policy_name as min_consumption_policy_name
```

**Status**: ⏳ Not Started

---

### Phase 8: Multi-Day Pricing Integration

**File**: `models/reservation_multiday.py` (MODIFY)

#### Update `create_linked_multiday_reservations()`

**Simplified Approach**: Apply same pricing to ALL linked reservations

**Add Parameters**:
```python
package_id: int = None,
payment_ticket_number: str = None,
price: float = 0.0,
final_price: float = 0.0,
paid: int = 0,
minimum_consumption_amount: float = 0.0,
minimum_consumption_policy_id: int = None
```

**Logic**:
```python
# Calculate pricing ONCE for the package/people count
pricing_data = {
    'package_id': package_id,
    'payment_ticket_number': payment_ticket_number,
    'price': price,
    'final_price': final_price,
    'paid': paid,
    'minimum_consumption_amount': minimum_consumption_amount,
    'minimum_consumption_policy_id': minimum_consumption_policy_id
}

for i, date in enumerate(dates):
    # Get furniture for this date
    date_furniture = furniture_by_date.get(date, furniture_ids) if furniture_by_date else furniture_ids

    # Create reservation with SAME pricing for all days
    if i == 0:
        # Parent
        parent_id, parent_ticket = create_beach_reservation(
            customer_id=customer_id,
            reservation_date=date,
            furniture_ids=date_furniture,
            # ... common fields ...
            **pricing_data  # SAME pricing for all
        )
    else:
        # Child
        child_id, child_ticket = create_beach_reservation(
            customer_id=customer_id,
            reservation_date=date,
            parent_reservation_id=parent_id,
            furniture_ids=date_furniture,
            # ... common fields ...
            **pricing_data  # SAME pricing for all
        )
```

**Example**:
- Guest selects "Classic Package 30€/person" for 3 days
- All 3 reservations (parent + 2 children) get `package_id=5`, `price=120`, `final_price=120`

**Status**: ⏳ Not Started

---

### Phase 9: Route Integration

**File**: `blueprints/beach/routes/reservations.py` (MODIFY)

#### Update `create()` POST Handler

**Extract Pricing Fields**:
```python
# NEW pricing fields
package_id = request.form.get('package_id', type=int) or None
payment_ticket_number = request.form.get('payment_ticket_number', '').strip() or None
price = request.form.get('price', 0.0, type=float)
final_price = request.form.get('final_price', 0.0, type=float)
paid = 1 if request.form.get('paid') else 0
minimum_consumption_amount = request.form.get('minimum_consumption_amount', 0.0, type=float)
minimum_consumption_policy_id = request.form.get('minimum_consumption_policy_id', type=int) or None
```

**Validate Payment**:
```python
if paid and not payment_ticket_number:
    flash('Número de ticket de pago requerido para reservas pagadas', 'error')
    return render_template(...)
```

**Pass to Model**:
```python
reservation_id, ticket_number = create_beach_reservation(
    # ... existing params ...
    package_id=package_id,
    payment_ticket_number=payment_ticket_number,
    price=price,
    final_price=final_price,
    paid=paid,
    minimum_consumption_amount=minimum_consumption_amount,
    minimum_consumption_policy_id=minimum_consumption_policy_id
)
```

**Multi-Day**: Pass same pricing to `create_linked_multiday_reservations()`

**Status**: ⏳ Not Started

---

### Phase 10: Display Updates

#### File: `templates/beach/reservation_detail.html` (MODIFY)

**Add Pricing Card**:
```html
<div class="card mb-4">
    <div class="card-header">
        <h5><i class="fas fa-euro-sign me-2"></i>Información de Precio</h5>
    </div>
    <div class="card-body">
        <div class="row g-3">
            {% if reservation.package_id %}
            <div class="col-md-6">
                <strong>Paquete:</strong>
                <span class="badge" style="background-color: #D4AF37;">
                    {{ reservation.package_name }}
                </span>
                <small class="text-muted">
                    €{{ reservation.package_base_price }}
                    {% if reservation.package_price_type == 'per_person' %}por persona{% endif %}
                </small>
            </div>
            {% endif %}

            {% if reservation.minimum_consumption_amount > 0 %}
            <div class="col-md-6">
                <strong>Consumo Mínimo:</strong>
                <div class="h6 text-info">€{{ reservation.minimum_consumption_amount }}</div>
                <small>{{ reservation.min_consumption_policy_name }}</small>
            </div>
            {% endif %}

            <div class="col-md-4">
                <strong>Precio Final:</strong>
                <div class="h5" style="color: #D4AF37;">€{{ reservation.final_price }}</div>
            </div>

            <div class="col-md-4">
                <strong>Estado de Pago:</strong>
                {% if reservation.paid %}
                <span class="badge bg-success">
                    <i class="fas fa-check-circle"></i> Pagado
                </span>
                {% if reservation.payment_ticket_number %}
                <br><small>Ticket: {{ reservation.payment_ticket_number }}</small>
                {% endif %}
                {% else %}
                <span class="badge bg-warning">
                    <i class="fas fa-clock"></i> Pendiente
                </span>
                {% endif %}
            </div>

            {% if reservation.charge_to_room %}
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="fas fa-hotel"></i> Cargo a habitación
                    {% if reservation.charge_reference %}- Ref: {{ reservation.charge_reference }}{% endif %}
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>
```

#### File: `templates/beach/reservations.html` (MODIFY)

**Add Columns**:
```html
<th>Precio</th>
<th>Pago</th>

<!-- In tbody -->
<td>
    {% if reservation.final_price > 0 %}
    <strong style="color: #D4AF37;">€{{ reservation.final_price }}</strong>
    {% if reservation.package_id %}
    <br><small><i class="fas fa-box"></i> Paquete</small>
    {% endif %}
    {% else %}
    <span class="text-muted">—</span>
    {% endif %}
</td>
<td>
    {% if reservation.paid %}
    <span class="badge bg-success"><i class="fas fa-check"></i> Pagado</span>
    {% else %}
    <span class="badge bg-warning"><i class="fas fa-clock"></i> Pendiente</span>
    {% endif %}
</td>
```

**Status**: ⏳ Not Started

---

### Phase 11: Testing

#### Unit Tests: `tests/unit/test_pricing_service.py` (NEW)
- ✅ Package price calculation (per_package vs per_person)
- ✅ Minimum consumption calculation
- ✅ Package eligibility filtering
- ✅ Edge cases: invalid package, people out of range

#### Integration Tests: `tests/integration/test_reservation_pricing.py` (NEW)
- ✅ Create reservation with package
- ✅ Create reservation with minimum consumption only
- ✅ Multi-day with same pricing applied to all
- ✅ Validation: paid without ticket → fail

#### API Tests: `tests/api/test_pricing_api.py` (NEW)
- ✅ `/api/pricing/calculate` endpoint
- ✅ `/api/pricing/packages/available` endpoint
- ✅ Error handling

**Status**: ⏳ Not Started

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Create database migration
- [ ] Run migration (add package_id, payment_ticket_number)
- [ ] Create pricing_service.py
- [ ] Write unit tests for pricing service

### Week 2: API & Templates
- [ ] Create pricing API routes
- [ ] **Split reservation_form.html into partials**
- [ ] Create _step3_pricing.html partial
- [ ] Write API tests

### Week 3: Models
- [ ] Update reservation_crud.py (add params, validation, JOINs)
- [ ] Update reservation_multiday.py (same pricing for all days)
- [ ] Write integration tests

### Week 4: UI & JavaScript
- [ ] Create reservation_form_pricing.js
- [ ] Implement AJAX price calculation
- [ ] Add payment validation
- [ ] Test end-to-end pricing flow

### Week 5: Routes & Display
- [ ] Update reservations.py create() handler
- [ ] Update reservation_detail.html (pricing card)
- [ ] Update reservations.html (price/payment columns)
- [ ] Test multi-day same pricing

### Week 6: Polish
- [ ] Run data migration
- [ ] Test backward compatibility
- [ ] User acceptance testing
- [ ] Deploy

---

## Critical Files Summary

### Files to CREATE:
1. `database/migrations/pricing_integration.py` - Schema + data migration
2. `blueprints/beach/services/pricing_service.py` - Pricing calculations (~350 lines)
3. `blueprints/beach/routes/api/pricing.py` - AJAX endpoints (~200 lines)
4. `static/js/reservation_form_pricing.js` - Real-time UI (~300 lines)
5. `templates/beach/reservation_form/_step1_customer.html` - Customer selection partial
6. `templates/beach/reservation_form/_step2_details.html` - Details partial
7. `templates/beach/reservation_form/_step3_pricing.html` - **NEW** Pricing partial
8. `templates/beach/reservation_form/_step4_confirm.html` - Confirmation partial
9. `tests/unit/test_pricing_service.py`
10. `tests/integration/test_reservation_pricing.py`
11. `tests/api/test_pricing_api.py`

### Files to MODIFY:
1. `templates/beach/reservation_form.html` - Refactor to use partials (27050→~200 lines)
2. `models/reservation_crud.py` - Add pricing params and JOINs (533→~600 lines)
3. `models/reservation_multiday.py` - Add same pricing for all days
4. `blueprints/beach/routes/reservations.py` - Extract pricing fields
5. `templates/beach/reservation_detail.html` - Add pricing card
6. `templates/beach/reservations.html` - Add price/payment columns
7. `blueprints/beach/routes/api/__init__.py` - Register pricing routes

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Pricing Mode Detection** | Implicit (based on package_id presence) | Less redundancy, self-documenting |
| **Payment Ticket** | Separate field from reservation ticket | Different systems, different purposes |
| **Multi-Day Pricing** | **Same pricing for ALL linked reservations** | User requirement: replicate package across all days |
| **Price Override** | Always allowed | Business requirement for discounts |
| **Service Layer** | New pricing_service.py module | Centralize complex logic |
| **Template Splitting** | Partials for each wizard step | Maintainability, file size <500 lines |

---

## Notes

- **Reservation form is too large (27050 tokens)** - MUST split into partials
- **Multi-day simplified**: Same package/pricing applies to ALL linked reservations (not per-day different)
- Payment ticket validation: client-side AND server-side
- Pricing calculations: server-side only (never trust client)
- All AJAX endpoints: `@permission_required` decorator

---

## Follow-Up Questions

- [ ] Should we show price breakdown to employees? (e.g., "4 people × €30 = €120")
- [ ] Should there be a "Mark All Days Paid" button for multi-day reservations?
- [ ] Do we need audit trail for manual price adjustments?
- [ ] Should payment ticket number have a specific format validation?

---

## Progress Tracking

**Last Updated**: 2025-12-26
**Current Phase**: Planning Complete
**Next Step**: Start Phase 1 (Database Migration)
