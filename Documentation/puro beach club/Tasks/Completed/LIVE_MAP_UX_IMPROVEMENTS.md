# Live Map UX Improvements for Day-to-Day Operations

> **Status**: Completed
> **Created**: 2025-12-23
> **Target**: Tablet-first (phone secondary)

## Overview

Improve the live map experience for tablet/phone users to handle all daily beach club operations with minimal clicks: **create reservations, mark seated, cancel/release, change furniture positions**.

---

## Key Requirements

| Requirement | Solution |
|-------------|----------|
| Create reservations (single + multi-day) | Enhanced bottom sheet with calendar picker |
| Mark as seated (Sentada) | Quick action button in action sheet |
| Cancel/release furniture | Cancelar button in action sheet |
| Change positions (reassign furniture) | "Cambiar Mobiliario" flow in action sheet |
| Visual identification | Room# (internos) or Name (externos) on furniture |
| Staff address guests by name | Hover tooltip shows full customer name |
| Touch-friendly | Long-press opens action sheet |

---

## Implementation Phases

### Phase 1: Visual Furniture Labels + Hover Tooltips

**Goal**: Show room number or customer name on occupied furniture, hover for full name.

**Files to modify:**
- `static/js/map.js` - Enhance `renderFurniture()` to add text labels and hover handlers
- `templates/beach/map.html` - Add tooltip HTML element

**Changes:**
1. Add text element inside furniture SVG showing:
   - **Internos**: Room number (e.g., "301")
   - **Externos**: First name truncated (e.g., "Juan")
2. Add hover event that shows tooltip with full customer name
3. Tooltip positioned near cursor, disappears on mouse leave
4. On touch devices: tooltip shows briefly on tap, then fades

**API data needed** (already available in `/beach/api/map/data`):
```javascript
availability[furniture_id] = {
    customer_name: "Juan Garcia",
    room_number: "301",  // null if externo
    customer_type: "interno"  // or "externo"
}
```

---

### Phase 2: Long-Press Detection + Action Sheet Component

**Goal**: Long-press (500ms) on occupied furniture opens action sheet with reservation details.

**New files:**
- `static/js/map/touch-handler.js` - Touch gesture detection (~100 lines)
- `static/js/map/action-sheet.js` - Reusable bottom sheet component (~150 lines)

**Files to modify:**
- `static/js/map.js` - Integrate touch handler, action sheet
- `templates/beach/map.html` - Add action sheet HTML structure

**Action Sheet Features:**
- Drag handle at top
- Swipe down to dismiss
- Backdrop click to dismiss
- Animates from bottom
- Max height 85vh, scrollable content

---

### Phase 3: Reservation Details Action Sheet

**Goal**: Show reservation info with quick action buttons when long-pressing occupied furniture.

**Files to modify:**
- `static/js/map.js` - `showReservationDetails(furnitureId)` method
- `templates/beach/map.html` - Details sheet content template

**Content Layout:**
```
+------------------------------------------+
|  [X]  Reserva #25122301         Ticket   |
+------------------------------------------+
|  Juan Garcia Perez                       |
|  [INTERNO]  Hab. 301                     |
|  [VIP] si aplica                         |
+------------------------------------------+
|  Estado: [====== CONFIRMADA ======]      |
+------------------------------------------+
|  2 personas  |  Todo el dia  |  23 Dic   |
+------------------------------------------+
|  Mobiliario: [H5] [H6] [H7]              |
+------------------------------------------+
|  Notas: Prefiere sombra, cerca piscina   |
+------------------------------------------+
|                                          |
|  [ SENTAR ] (primary gold, 56px height)  |
|                                          |
|  [Cambiar Mobiliario]  [Ver Detalle]     |
|                                          |
|  [Cancelar Reserva] (danger outlined)    |
+------------------------------------------+
```

**Quick Actions:**
| Button | Action | API |
|--------|--------|-----|
| Sentar | Add "Sentada" state | `POST /api/reservations/{id}/toggle-state` |
| Cambiar Mobiliario | Opens furniture reassignment flow | See Phase 5 |
| Ver Detalle | Navigate to full detail page | `/beach/reservations/{id}` |
| Cancelar Reserva | Add "Cancelada" state with confirmation | `POST /api/reservations/{id}/toggle-state` |

**State-dependent button:**
- If state=Confirmada: Show "Sentar"
- If state=Sentada: Show "Completar" (or hide if not needed)

---

### Phase 4: Enhanced Quick Reservation Sheet (Multi-day)

**Goal**: Add multi-day calendar and preferences to the existing reservation bottom sheet.

**Files to modify:**
- `templates/beach/map.html` - Enhance reservation sheet form
- `static/js/map.js` - Handle calendar and new fields
- `blueprints/beach/routes/api/map_reservations.py` - Support multi-day creation

**New Form Fields:**
```
+------------------------------------------+
|  Mobiliario: [H5] [H6] +2 pax            |
+------------------------------------------+
|  Buscar cliente: [____________] [search] |
|  > Juan Garcia - Hab 301                 |
+------------------------------------------+
|  Personas: [ 2 ] [-] [+]                 |
+------------------------------------------+
|  Fechas: [23 Dic]  [+ Agregar dias]      |
|  > Calendario picker (collapsible)       |
|  > Selected: 23, 24, 25 Dic (3 dias)     |
+------------------------------------------+
|  Horario: [Todo el dia] [Manana] [Tarde] |
+------------------------------------------+
|  Preferencias: (toggle chips)            |
|  [Sombra] [Primera linea] [Cerca bar]    |
+------------------------------------------+
|  > Notas (collapsible)                   |
+------------------------------------------+
|  [Crear Reserva] (primary gold)          |
+------------------------------------------+
```

**API Change:**
```python
# Enhanced POST /beach/api/map/quick-reservation
{
    "customer_id": 123,
    "furniture_ids": [5, 6],
    "dates": ["2025-12-23", "2025-12-24"],  # Array for multi-day
    "num_people": 2,
    "time_slot": "all_day",  # NEW
    "preferences": ["pref_sombra", "pref_primera_linea"],  # NEW
    "notes": "..."
}
```

For multi-day: Call existing `create_linked_multiday_reservations()` from `models/reservation_multiday.py`

---

### Phase 5: Change Furniture Position Flow

**Goal**: Allow staff to reassign furniture to an existing reservation directly from the map.

**Flow:**
1. Long-press occupied furniture → Action sheet opens
2. Tap "Cambiar Mobiliario"
3. Sheet shows current furniture highlighted on map
4. User taps new furniture to add/remove from selection
5. "Guardar Cambios" button updates reservation

**Files to modify:**
- `static/js/map.js` - Add "reassignment mode" state
- `templates/beach/map.html` - Reassignment UI in action sheet
- `blueprints/beach/routes/api/map_reservations.py` - Add reassignment endpoint

**New API:**
```python
# POST /beach/api/reservations/{id}/reassign-furniture
{
    "furniture_ids": [7, 8, 9],  # New furniture selection
    "date": "2025-12-23"  # For multi-day, which day to update
}
```

**Backend Logic:**
1. Check availability of new furniture for the date
2. Release old furniture assignments
3. Create new assignments in `beach_reservation_furniture`
4. Return success with updated reservation

---

### Phase 6: Selection Bar for Occupied Furniture

**Goal**: When selecting occupied furniture, show relevant actions instead of "Reservar".

**Current behavior**: Bottom bar always shows "Reservar" button
**New behavior**:
- If ALL selected furniture is available → Show "Reservar"
- If ANY selected furniture is occupied → Show "Ver Reserva" (if single) or multi-select actions

**Files to modify:**
- `static/js/map.js` - `updateSelectionBar()` method
- `templates/beach/map.html` - Alternative action bar content

**Selection scenarios:**
| Selection | Bottom Bar Actions |
|-----------|-------------------|
| 1 available | "Reservar" |
| N available | "Reservar" (shows total capacity) |
| 1 occupied | "Ver Reserva" → opens action sheet |
| N occupied (same reservation) | "Ver Reserva" |
| N occupied (different reservations) | "Ver Reservas" → list view |
| Mixed (available + occupied) | "Reservar Disponibles" (ignores occupied) |

---

## File Summary

### New Files
| File | Purpose | Lines (est) |
|------|---------|-------------|
| `static/js/map/touch-handler.js` | Long-press detection | ~100 |
| `static/js/map/action-sheet.js` | Reusable bottom sheet | ~150 |

### Modified Files
| File | Changes |
|------|---------|
| `static/js/map.js` | Add labels, tooltips, long-press, action sheet integration, reassignment mode |
| `templates/beach/map.html` | Action sheet HTML, enhanced reservation form, tooltip element |
| `blueprints/beach/routes/api/map_reservations.py` | Multi-day support, reassign endpoint |
| `blueprints/beach/routes/api/map_data.py` | Ensure customer_name, room_number, customer_type in availability |

### API Endpoints
| Endpoint | Status | Purpose |
|----------|--------|---------|
| `GET /api/map/data` | Modify | Add customer info to availability |
| `POST /api/map/quick-reservation` | Modify | Support multi-day, time_slot, preferences |
| `POST /api/reservations/{id}/toggle-state` | Exists | State changes (Sentar, Cancelar) |
| `POST /api/reservations/{id}/reassign-furniture` | New | Change furniture positions |
| `GET /api/map/furniture/{id}/details` | Exists | Get full reservation details |

---

## UI Specifications

### Touch Targets
- All buttons: minimum 44px height (Apple HIG)
- Primary action buttons: 56px height
- Furniture on map: minimum 40x40px tap area

### Action Sheet
- Max height: 85vh
- Border radius: 20px 20px 0 0
- Drag handle: 40px x 4px, centered, #DDD
- Backdrop: rgba(0,0,0,0.5)
- Animation: 300ms ease-out slide up

### Furniture Labels
- Font size: 10px (scales with zoom)
- Color: Dark text on light states, light text on dark states
- Truncate at 4 characters + ellipsis if needed

### Hover Tooltip
- Background: #1A3A5C (Deep Ocean)
- Text: White
- Padding: 8px 12px
- Border radius: 6px
- Max width: 200px
- Position: Above cursor, centered

---

## Implementation Order

1. **Phase 1** (Visual labels + tooltips) - Foundation for identification
2. **Phase 2** (Touch handler + action sheet) - Core interaction component
3. **Phase 3** (Reservation details sheet) - Enable Sentar/Cancelar actions
4. **Phase 4** (Enhanced reservation form) - Multi-day + preferences
5. **Phase 5** (Change positions) - Furniture reassignment
6. **Phase 6** (Selection bar logic) - Polish mixed selection scenarios

Estimated total: ~800-1000 lines of new/modified code across JS and templates.

---

## Progress Tracking

### Phase 1: Visual Labels + Tooltips
- [x] Modify map_data.py to include customer_name, room_number, customer_type
- [x] Add text labels to furniture SVG in renderFurniture()
- [x] Add tooltip HTML element to map.html
- [x] Implement hover handlers for desktop
- [x] Implement tap-to-show for touch devices

### Phase 2: Touch Handler + Action Sheet
- [x] Create touch-handler.js module
- [x] Create action-sheet.js module
- [x] Add action sheet HTML to map.html
- [x] Integrate long-press detection in map.js

### Phase 3: Reservation Details Sheet
- [x] Create details sheet content template
- [x] Implement showReservationDetails() method
- [x] Wire up Sentar button to toggle-state API
- [x] Wire up Cancelar button with confirmation
- [x] Add Ver Detalle navigation link

### Phase 4: Enhanced Reservation Form
- [x] Add calendar picker for multi-day selection
- [x] Add time slot toggle buttons
- [x] Add preferences chips
- [x] Modify API to handle multi-day creation

### Phase 5: Change Furniture Position
- [x] Add reassignment mode to map.js
- [x] Create reassignment UI in action sheet
- [x] Create reassign-furniture API endpoint
- [x] Implement availability check + update logic

### Phase 6: Selection Bar Logic
- [x] Detect occupied vs available in selection
- [x] Update action bar based on selection type
- [x] Handle mixed selection scenarios

---

## Phase 7: BottomSheet / ReservationForm Synchronization

**Goal**: Maximize code reuse between BottomSheetReservationModal and ReservationForm page.

**Completed Changes**:
1. **Unified Multi-day Selection**: Replaced simple date input + "Add Days" button with the shared `DatePicker` component (`static/js/date-picker.js`)
2. **Simplified Form Fields**: Horario field removed (hidden, defaults to "all_day")
3. **Auto-fill Customer Data**: Already implemented via `autoFillCustomerData()` function - auto-populates preferences and notes when customer is selected
4. **Deep Link with State**: "Más opciones" button now passes customer data to full reservation form via URL parameters

**Files Modified**:
- `templates/beach/map.html` - Replaced date input with DatePicker, added CSS/JS links, updated deep link logic
- `blueprints/beach/routes/reservations.py` - Added handling for `customer_id`, `hotel_guest_id`, and `dates` URL parameters
- `templates/beach/reservation_form.html` - Added initialization code to handle preselected customer/guest and multi-day dates

**URL Parameters for Deep Link**:
- `date` - First reservation date
- `furniture` - Comma-separated furniture IDs
- `customer_id` - Beach club customer ID (optional)
- `hotel_guest_id` - Hotel guest ID (optional, alternative to customer_id)
- `dates` - Comma-separated dates for multi-day (optional)

---

## Testing Checklist

- [ ] Tablet: iPad Safari - all interactions
- [ ] Tablet: Android Chrome - all interactions
- [ ] Phone: iPhone Safari - verify usable on smaller screen
- [ ] Desktop: Mouse hover shows tooltips
- [ ] Desktop: Right-click still works (fallback)
- [ ] Create single-day reservation
- [ ] Create multi-day reservation (3 consecutive days)
- [ ] Mark reservation as Sentada
- [ ] Cancel reservation
- [ ] Change furniture position
- [ ] Select mixed (available + occupied) furniture
- [ ] DatePicker: Click to expand calendar, select multiple dates
- [ ] DatePicker: Navigate months, deselect dates
- [ ] Deep link: Select customer then click "Más opciones" - customer should be pre-selected
- [ ] Deep link: Select hotel guest then click "Más opciones" - guest should be pre-selected
- [ ] Deep link: Select multiple dates then click "Más opciones" - dates should be pre-selected
- [ ] Auto-fill: Select customer with preferences - preferences should be auto-checked
