# Waiting List Feature Design

**Date:** 2026-01-08
**Status:** Approved
**Phase:** 7a - Live Map Enhancements

---

## Overview

Interest registration system for beach club. When fully booked, customers can leave their contact info and preferences. Staff manually contacts them when spots open up (cancellations/no-shows).

### Key Decisions

- **Approach:** Interest registration (not automated queue)
- **Access:** Toolbar button on live map with slide-out panel
- **Alert:** Badge counter showing waiting entries for selected date
- **Workflow:** Convert to reservation (pre-fill) OR manual close with status
- **History:** Auto-expire after date passes, keep for reporting

---

## Data Model

### New Table: `beach_waitlist`

```sql
CREATE TABLE beach_waitlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES beach_customers(id),
    requested_date DATE NOT NULL,
    num_people INTEGER NOT NULL DEFAULT 1,
    preferred_zone_id INTEGER REFERENCES beach_zones(id),
    preferred_furniture_type_id INTEGER REFERENCES beach_furniture_types(id),
    time_preference TEXT CHECK(time_preference IN ('morning', 'afternoon', 'all_day')),
    reservation_type TEXT DEFAULT 'incluido' CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo')),
    package_id INTEGER REFERENCES beach_packages(id),
    notes TEXT,
    status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'contacted', 'converted', 'declined', 'no_answer', 'expired')),
    converted_reservation_id INTEGER REFERENCES beach_reservations(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_waitlist_date_status ON beach_waitlist(requested_date, status);
CREATE INDEX idx_waitlist_customer ON beach_waitlist(customer_id);
```

### Field Reference

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `customer_id` | INTEGER FK | Links to `beach_customers` |
| `requested_date` | DATE | Date they want a spot |
| `num_people` | INTEGER | Party size (1-20) |
| `preferred_zone_id` | INTEGER FK | Optional zone preference |
| `preferred_furniture_type_id` | INTEGER FK | Optional furniture type |
| `time_preference` | TEXT | 'morning' / 'afternoon' / 'all_day' / NULL |
| `reservation_type` | TEXT | 'incluido' / 'paquete' / 'consumo_minimo' |
| `package_id` | INTEGER FK | If reservation_type = 'paquete' |
| `notes` | TEXT | Staff notes |
| `status` | TEXT | Current status (see transitions) |
| `converted_reservation_id` | INTEGER FK | Links to created reservation |
| `created_at` | TIMESTAMP | When added |
| `updated_at` | TIMESTAMP | Last status change |
| `created_by` | INTEGER FK | Staff user who added |

---

## UI Components

### Toolbar Button

- **Location:** Map toolbar, alongside search/block/temp furniture buttons
- **Icon:** `fa-clock` with badge counter
- **Badge:** Gold (#D4AF37) background, shows count for selected date, hidden when 0
- **Styling:** Same as other toolbar buttons (`map-control-btn` class)

### Slide-out Panel

Follows `_new_reservation_panel.html` pattern:

```
┌─────────────────────────────────────────┐
│ [←] Lista de Espera    8 Ene 2026      │  ← Deep Ocean header
├─────────────────────────────────────────┤
│ [Pendientes (3)]  [Historial]          │  ← Tab navigation
├─────────────────────────────────────────┤
│                                         │
│  ┌─ Entry Card ───────────────────────┐ │
│  │ Juan García          [Interno]     │ │
│  │ Hab. 205 · 2 personas              │ │
│  │ ☎ +34 600 123 456                  │ │
│  │ Zona VIP · Balinesa · Mañana       │ │
│  │ [Paquete Premium]                  │ │
│  │ Hace 2 horas                       │ │
│  │                                    │ │
│  │ [Convertir]  [Estado ▼]            │ │
│  └────────────────────────────────────┘ │
│                                         │
│  [+ Añadir a Lista de Espera]          │  ← Secondary button
│                                         │
└─────────────────────────────────────────┘
```

### Add Entry Modal

Following design system modal pattern:

- **Header:** Deep Ocean gradient, "Añadir a Lista de Espera"
- **Sections:**
  - **Cliente** - Type toggle (Interno/Externo), room search with auto-fill from hotel guests, or customer search/create
  - **Detalles** - Date (defaults to map date), num_people, time preference (Mañana/Tarde/Todo el día)
  - **Preferencias** - Zone dropdown, furniture type dropdown
  - **Tipo de Reserva** - Radio buttons (Incluido/Paquete/Consumo Mínimo)
  - **Notas** - Textarea
- **Footer:** "Cancelar" (secondary) + "Añadir" (primary gold)

### Entry Card Styling

- White background, 12px border-radius, subtle shadow
- Customer type badge: Interno (blue `#DBEAFE`), Externo (gold `#FEF3C7`)
- Reservation type badge: Color-coded as in reservations list
- "Convertir" button: Primary gold gradient
- "Estado" dropdown: Secondary style with options (Contactado, Rechazado, Sin Respuesta)

---

## Backend Architecture

### New Files

| File | Purpose |
|------|---------|
| `models/waitlist.py` | CRUD operations |
| `blueprints/beach/routes/api/waitlist.py` | REST API endpoints |
| `templates/beach/_waitlist_panel.html` | Panel partial |
| `static/js/WaitlistManager.js` | Frontend module |
| `static/css/waitlist.css` | Panel styles |

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/beach/api/waitlist?date=YYYY-MM-DD` | List entries for date |
| `GET` | `/beach/api/waitlist/count?date=YYYY-MM-DD` | Badge count |
| `GET` | `/beach/api/waitlist/<id>` | Get single entry |
| `POST` | `/beach/api/waitlist` | Create entry |
| `PUT` | `/beach/api/waitlist/<id>` | Update status |
| `POST` | `/beach/api/waitlist/<id>/convert` | Convert to reservation |
| `GET` | `/beach/api/waitlist/history?date=YYYY-MM-DD` | Past entries |

### Model Functions

```python
# models/waitlist.py

def get_waitlist_by_date(date: str, status: str = 'waiting') -> list:
    """Get waitlist entries for a specific date."""

def get_waitlist_count(date: str) -> int:
    """Get count of waiting entries for badge."""

def get_waitlist_entry(entry_id: int) -> dict:
    """Get single entry with customer details."""

def create_waitlist_entry(data: dict, created_by: int) -> int:
    """Create new waitlist entry, returns ID."""

def update_waitlist_status(entry_id: int, status: str) -> bool:
    """Update entry status."""

def convert_to_reservation(entry_id: int, reservation_id: int) -> bool:
    """Mark as converted, link to reservation."""

def expire_old_entries() -> int:
    """Bulk expire past-date entries, returns count."""

def get_waitlist_history(date: str = None, customer_id: int = None) -> list:
    """Get non-waiting entries for reporting."""
```

### Permissions

| Permission | Description |
|------------|-------------|
| `beach.waitlist.view` | View waiting list |
| `beach.waitlist.create` | Add entries |
| `beach.waitlist.manage` | Update status, convert |

---

## Workflows

### Convert to Reservation Flow

1. Staff clicks "Convertir" on waitlist entry
2. System opens New Reservation panel pre-filled with:
   - Customer (already linked)
   - Date (from waitlist entry)
   - Number of people
   - Preferred zone (pre-selected if available)
   - Preferred furniture type (pre-selected if available)
   - Reservation type + package (if applicable)
   - Notes copied to observations
3. Staff selects available furniture on map
4. Staff submits reservation
5. On success:
   - Waitlist entry status → `converted`
   - `converted_reservation_id` linked
   - Badge count decrements

### Status Transitions

```
                    ┌──────────────┐
                    │   waiting    │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   contacted   │  │   converted   │  │    expired    │
└───────┬───────┘  └───────────────┘  └───────────────┘
        │                                    ▲
        ├──────────────────┐                 │
        ▼                  ▼                 │
┌───────────────┐  ┌───────────────┐         │
│   declined    │  │   no_answer   │─────────┘
└───────────────┘  └───────────────┘  (if date passes)
```

### Auto-Expire Logic

**Trigger:** App startup + daily at midnight + when viewing history

```sql
UPDATE beach_waitlist
SET status = 'expired', updated_at = CURRENT_TIMESTAMP
WHERE status IN ('waiting', 'contacted', 'no_answer')
  AND requested_date < date('now')
```

### Badge Count Query

```sql
SELECT COUNT(*)
FROM beach_waitlist
WHERE requested_date = ?
  AND status = 'waiting'
```

**Called when:**
- Map date changes
- Waitlist entry created/updated
- Panel opens

---

## Error Handling

### Validation Errors

| Field | Validation | Error Message |
|-------|------------|---------------|
| `customer_id` | Required, must exist | "Debe seleccionar un cliente" |
| `requested_date` | Required, not in past | "La fecha debe ser hoy o futura" |
| `num_people` | Required, 1-20 | "Número de personas debe ser entre 1 y 20" |
| `time_preference` | If provided, valid enum | "Preferencia de horario no válida" |
| `reservation_type` | If provided, valid enum | "Tipo de reserva no válido" |
| `package_id` | Required if type='paquete' | "Debe seleccionar un paquete" |

### API Error Responses

```python
# 400 Bad Request - Validation error
{"success": False, "error": "Debe seleccionar un cliente"}

# 404 Not Found - Entry doesn't exist
{"success": False, "error": "Entrada no encontrada"}

# 409 Conflict - Invalid state transition
{"success": False, "error": "No se puede convertir una entrada ya procesada"}

# 500 Server Error - Database/unexpected
{"success": False, "error": "Error del servidor. Intente de nuevo."}
```

### UI Error Display

- **Validation errors:** Inline below field (red `#C1444F`)
- **API errors:** Toast notification (error style)
- **Network errors:** Toast "Error de conexión. Verifique su conexión a internet."

### Edge Cases

| Scenario | Handling |
|----------|----------|
| Customer deleted after entry | Show "Cliente eliminado" warning, disable convert |
| Package deactivated after entry | Show warning badge, allow convert with different package |
| Double-click on convert | Disable button after first click, re-enable on error |
| Entry expired while viewing | Refresh panel, toast "Esta entrada ha expirado" |
| Concurrent status update | Last write wins, refresh panel after save |

### Conversion Error Recovery

If reservation creation fails:
1. Waitlist entry remains `waiting` (no change)
2. Error displayed in reservation panel
3. Staff can retry

---

## Testing

### Unit Tests (`tests/unit/test_waitlist.py`)

| Test | Description |
|------|-------------|
| `test_create_waitlist_entry` | Valid entry with all fields |
| `test_create_waitlist_entry_minimal` | Only required fields |
| `test_create_waitlist_entry_interno` | Auto-fill from hotel guest |
| `test_create_waitlist_entry_past_date` | Reject past dates |
| `test_update_status_valid_transitions` | waiting → contacted/converted/declined/no_answer |
| `test_update_status_invalid_transition` | expired → anything (fail) |
| `test_convert_to_reservation` | Links reservation, sets status |
| `test_expire_old_entries` | Bulk expire past dates |
| `test_get_waitlist_count` | Count only 'waiting' |
| `test_get_waitlist_by_date` | Filter by date/status |

### Integration Tests (`tests/integration/test_waitlist_flow.py`)

| Test | Description |
|------|-------------|
| `test_full_waitlist_to_reservation_flow` | Create → convert → verify |
| `test_waitlist_with_package` | Preserves pricing on convert |
| `test_badge_count_updates` | Count changes on create/update |
| `test_history_after_expiration` | Expired entries in history |

### API Tests (`tests/api/test_waitlist_api.py`)

| Test | Description |
|------|-------------|
| `test_get_waitlist_unauthorized` | 401 without login |
| `test_get_waitlist_no_permission` | 403 without permission |
| `test_post_waitlist_validation` | 400 with invalid data |
| `test_crud_operations` | Full create/read/update |
| `test_convert_endpoint` | Creates reservation link |

### Manual Testing Checklist

- [ ] Add interno customer via room number lookup
- [ ] Add externo customer via search
- [ ] Add externo customer via inline create
- [ ] Badge shows correct count on date change
- [ ] Convert pre-fills reservation panel correctly
- [ ] Status dropdown updates entry
- [ ] History tab shows past entries
- [ ] Expired entries appear in history automatically
- [ ] Panel responsive on tablet (1024px)

---

## Implementation Order

1. **Database** - Migration for `beach_waitlist` table
2. **Models** - `models/waitlist.py` with CRUD functions
3. **API** - REST endpoints with validation
4. **Permissions** - Add to permission system
5. **Panel Template** - `_waitlist_panel.html`
6. **JavaScript** - `WaitlistManager.js` module
7. **Toolbar Integration** - Button + badge in map
8. **Convert Flow** - Integration with reservation panel
9. **Auto-Expire** - Scheduled/on-demand expiration
10. **Tests** - Unit, integration, API tests
