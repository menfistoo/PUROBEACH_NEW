# LiveMap Reservation Safeguards Plan

## Overview
This document tracks the implementation of validation safeguards to prevent human errors when creating reservations from the LiveMap. These safeguards show warnings/confirmations before allowing potentially problematic reservations.

## Implementation Status

### Phase 1: High Priority (Critical Business Logic)

| ID | Safeguard | Status | Frontend | Backend |
|----|-----------|--------|----------|---------|
| SG-01 | Duplicate Reservation Detection | `[x]` Done | `[x]` | `[x]` |
| SG-02 | Furniture Availability (Real-time) | `[x]` Done | `[x]` | `[x]` Exists |
| SG-03 | Hotel Stay Date Validation | `[x]` Done | `[x]` | `[ ]` Frontend only |

### Phase 2: Medium Priority (Data Integrity)

| ID | Safeguard | Status | Frontend | Backend |
|----|-----------|--------|----------|---------|
| SG-04 | Capacity Mismatch Warning | `[x]` Done | `[x]` | `[ ]` Frontend only |
| SG-05 | Past Date Prevention | `[x]` Done | `[x]` | `[ ]` Frontend only |
| SG-06 | Customer Type Validation | `[x]` Done | `[x]` | `[x]` |

### Phase 3: Low Priority (UX Enhancement)

| ID | Safeguard | Status | Frontend | Backend |
|----|-----------|--------|----------|---------|
| SG-07 | Non-contiguous Furniture Warning | `[x]` Done | `[x]` | `[x]` Exists |

---

## Detailed Specifications

### SG-01: Duplicate Reservation Detection

**Problem**: User creates a second reservation for the same customer on the same date.

**Trigger**: When customer is selected AND dates are confirmed.

**Check**: Query existing reservations for customer_id + selected dates.

**Warning Message**:
```
"Este cliente ya tiene una reserva para el [DATE]:
- Ticket #[TICKET] - [FURNITURE_LIST]
- Estado: [STATE]

¿Deseas crear otra reserva de todas formas?"
```

**User Options**:
- "Crear de todas formas" - Proceed with new reservation
- "Ver reserva existente" - Open existing reservation in panel
- "Cancelar" - Cancel creation

**Implementation**:
- Frontend: `new-reservation-panel.js` - Add check in `createReservation()` before submit
- Backend: Use existing `/beach/api/reservations/check-duplicate` endpoint
- Files to modify:
  - `static/js/map/new-reservation-panel.js`
  - `blueprints/beach/routes/api/map_reservations.py` (if endpoint changes needed)

---

### SG-02: Furniture Availability (Real-time Feedback)

**Problem**: User selects furniture that's already booked for selected dates.

**Trigger**: When furniture selection OR dates change.

**Check**: Query furniture availability for selected furniture + dates.

**Warning Message**:
```
"Mobiliario no disponible:
- [FURNITURE_NUM] ocupado el [DATE] (Reserva #[TICKET] - [CUSTOMER_NAME])

Selecciona otro mobiliario o cambia las fechas."
```

**User Options**:
- Deselect conflicted furniture
- Change dates
- Cannot proceed with conflicted selection

**Implementation**:
- Frontend: `new-reservation-panel.js` - Add availability check on furniture/date change
- Backend: Use existing `check_furniture_availability_bulk()` function
- Files to modify:
  - `static/js/map/new-reservation-panel.js`

---

### SG-03: Hotel Stay Date Validation

**Problem**: User books a hotel guest (interno) for dates outside their check-in/check-out window.

**Trigger**: When hotel guest is selected AND dates are set.

**Check**: Compare selected dates against guest's arrival_date and departure_date.

**Warning Message**:
```
"Fechas fuera de la estadia del huesped:
- Check-in: [ARRIVAL_DATE]
- Check-out: [DEPARTURE_DATE]
- Fechas seleccionadas fuera de rango: [OUT_OF_RANGE_DATES]

¿Continuar de todas formas?"
```

**User Options**:
- "Continuar" - Proceed anyway (maybe late checkout, etc.)
- "Ajustar fechas" - Go back and fix dates
- "Cancelar" - Cancel creation

**Implementation**:
- Frontend: `new-reservation-panel.js` - Validate on date change if hotel guest selected
- Backend: Add validation in `quick_reservation()` endpoint
- Files to modify:
  - `static/js/map/new-reservation-panel.js`
  - `blueprints/beach/routes/api/map_reservations.py`

---

### SG-04: Capacity Mismatch Warning

**Problem**: User sets num_people higher than total furniture capacity.

**Trigger**: When num_people input changes OR furniture selection changes.

**Check**: Compare num_people with sum of furniture capacities.

**Warning Message**:
```
"El numero de personas ([NUM]) excede la capacidad del mobiliario seleccionado ([CAPACITY]).

¿Ajustar a [CAPACITY] personas?"
```

**User Options**:
- "Ajustar" - Set num_people to capacity
- "Mantener" - Keep original value (data entry, not actual capacity)
- "Seleccionar mas mobiliario" - Add more furniture

**Implementation**:
- Frontend: `new-reservation-panel.js` - Show warning instead of silent truncation
- Files to modify:
  - `static/js/map/new-reservation-panel.js`

---

### SG-05: Past Date Prevention

**Problem**: User tries to create reservation for a past date.

**Trigger**: When dates are selected.

**Check**: Compare each selected date against today's date.

**Warning Message**:
```
"No se pueden crear reservas para fechas pasadas:
- [PAST_DATES]

Por favor selecciona fechas validas."
```

**User Options**:
- "Entendido" - Close warning, fix dates

**Implementation**:
- Frontend: `new-reservation-panel.js` - Block past dates in DatePicker + validate before submit
- Backend: Add validation in `quick_reservation()` endpoint
- Files to modify:
  - `static/js/map/new-reservation-panel.js`
  - `static/js/date-picker.js` (configure minDate)
  - `blueprints/beach/routes/api/map_reservations.py`

---

### SG-06: Customer Type Validation

**Problem**: Trying to charge external customer to room.

**Trigger**: When charge_to_room option is selected with external customer.

**Check**: Verify customer_type is 'interno' if charge_to_room is enabled.

**Warning Message**:
```
"Los clientes externos no se pueden cargar a habitacion.

Selecciona un huesped del hotel o desactiva 'Cargar a habitacion'."
```

**Implementation**:
- Frontend: Disable charge_to_room option for external customers
- Files to modify:
  - `static/js/map/new-reservation-panel.js` (if charge_to_room UI exists)

---

### SG-07: Non-contiguous Furniture Warning

**Problem**: User selects scattered furniture instead of grouped seating.

**Trigger**: When multiple furniture items are selected.

**Check**: Validate furniture positions form a contiguous cluster.

**Warning Message**:
```
"El mobiliario seleccionado no esta agrupado.
Esto puede resultar en una experiencia fragmentada para el cliente.

¿Continuar con esta seleccion?"
```

**User Options**:
- "Continuar" - Accept scattered selection
- "Ver sugerencias" - Show suggested contiguous alternatives

**Implementation**:
- Frontend: `new-reservation-panel.js` - Call contiguity validation before submit
- Backend: Use existing `/beach/api/reservations/validate-contiguity` endpoint
- Files to modify:
  - `static/js/map/new-reservation-panel.js`

---

## Shared Components

### Warning Modal Component

Create a reusable warning modal for safeguard messages:

```javascript
// static/js/map/safeguard-modal.js
class SafeguardModal {
    static async show(options) {
        // options: { title, message, type, buttons }
        // type: 'warning', 'error', 'info'
        // buttons: [{ label, action, style }]
        // Returns: button action or null if dismissed
    }
}
```

### Safeguard Check API

Unified endpoint for pre-flight validation:

```
POST /beach/api/reservations/validate
{
    "customer_id": 123,
    "dates": ["2024-12-24", "2024-12-25"],
    "furniture_ids": [1, 2, 3],
    "num_people": 4
}

Response:
{
    "valid": false,
    "warnings": [
        {
            "code": "SG-01",
            "type": "duplicate",
            "message": "...",
            "data": { existing_reservation: {...} }
        },
        {
            "code": "SG-03",
            "type": "date_outside_stay",
            "message": "...",
            "data": { out_of_range_dates: [...] }
        }
    ]
}
```

---

## Testing Checklist

### SG-01: Duplicate Reservation
- [ ] Create reservation for customer A on date X
- [ ] Try to create another reservation for customer A on date X
- [ ] Verify warning appears with existing reservation details
- [ ] Test "Create anyway" proceeds successfully
- [ ] Test "View existing" opens correct reservation

### SG-02: Furniture Availability
- [ ] Select furniture that's already booked
- [ ] Verify warning shows which dates are conflicted
- [ ] Verify cannot proceed with conflicted selection

### SG-03: Hotel Stay Dates
- [ ] Select hotel guest with check-in 24/12, check-out 26/12
- [ ] Try to book for 27/12
- [ ] Verify warning shows date is outside stay
- [ ] Test "Continue anyway" proceeds

### SG-04: Capacity Mismatch
- [ ] Select 1 hamaca (capacity 2)
- [ ] Enter num_people = 5
- [ ] Verify warning shows capacity exceeded
- [ ] Test "Adjust" sets to 2

### SG-05: Past Dates
- [ ] Try to select yesterday's date
- [ ] Verify date is blocked or warning appears
- [ ] Verify cannot proceed with past date

### SG-06: Customer Type
- [ ] Select external customer
- [ ] Verify charge_to_room option is disabled/hidden

### SG-07: Non-contiguous
- [ ] Select H1 and H10 (far apart)
- [ ] Verify warning about scattered selection
- [ ] Test "Continue" proceeds

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-24 | 0.1 | Initial plan created |
| 2024-12-24 | 1.0 | Implemented SG-01, SG-03, SG-04, SG-05 (frontend) |
| 2024-12-24 | 1.1 | Fixed SG-01 SQL query (furniture type join), implemented SG-02 frontend |
| 2024-12-24 | 1.2 | Implemented SG-06: charge_to_room option with customer type validation |
| 2024-12-24 | 1.3 | Implemented SG-07: Non-contiguous furniture warning (frontend) |

---

## Notes

- All warnings should be dismissable - staff may have valid reasons to override
- Log overridden warnings for audit purposes
- Consider adding "Don't show again this session" for experienced users
- Mobile-friendly modal design required
