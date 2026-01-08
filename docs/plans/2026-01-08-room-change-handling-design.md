# Room Change Handling for Hotel Guests

**Date:** 2026-01-08
**Status:** Approved
**Author:** Claude Code

---

## Problem

When hotel guests change rooms during their stay, the PMS exports an Excel file with the same `booking_reference` but a different `room_number`. The current import logic matches by `(room_number, arrival_date, guest_name)`, which creates duplicate records instead of updating the existing guest.

This causes:
- Duplicate hotel_guest records
- beach_customer records with outdated room numbers
- Staff confusion when looking up guests

---

## Solution

Use `booking_reference` (reservation number) as the primary matching identifier. When a room change is detected:
1. Update the `hotel_guests` record with the new room
2. Update the linked `beach_customers` record
3. Update current and future `beach_reservations`
4. Show a summary of room changes in the import results

---

## Matching Logic

```
1. If booking_reference exists in Excel row:
   → Match by (booking_reference + guest_name)
   → If found: UPDATE (including room_number if changed)
   → If not found: CREATE new record

2. If booking_reference is missing:
   → Fallback to current logic: (room_number + arrival_date + guest_name)
```

### Why booking_reference + guest_name?

The same booking can have multiple guests (family). Using both fields ensures:
- Each guest tracked individually
- Room changes apply to all guests in the booking
- No accidental merging of different people

---

## Data Flow

```
Excel Import
    │
    ▼
Match by booking_reference + guest_name
    │
    ▼
Room changed? ──No──► Normal update (dates, etc.)
    │
   Yes
    │
    ▼
Update hotel_guest.room_number
    │
    ▼
Find linked beach_customer (interno + old room + name match)
    │
    ▼
Update beach_customer.room_number
    │
    ▼
Mark future reservations as updated (start_date >= today)
```

---

## Implementation Details

### 1. Modified Function: `upsert_hotel_guest()`

**File:** `models/hotel_guest.py`

**Changes:**
- Accept `booking_reference` as parameter for matching
- First try to match by `(booking_reference, guest_name)` if booking_reference provided
- Fallback to `(room_number, arrival_date, guest_name)` if not
- Return `room_changed`, `old_room`, `new_room` in result dict

**Return value:**
```python
{
    'id': int,
    'action': 'created' | 'updated',
    'is_main_guest': int,
    'room_changed': bool,      # NEW
    'old_room': str | None,    # NEW
    'new_room': str | None     # NEW
}
```

### 2. New Function: `propagate_room_change()`

**File:** `models/hotel_guest.py`

**Signature:**
```python
def propagate_room_change(
    guest_name: str,
    old_room: str,
    new_room: str
) -> Dict[str, Any]
```

**Logic:**
1. Find `beach_customers` with `customer_type='interno'`, `room_number=old_room`, and name match
2. Update customer's `room_number` to new value
3. Update `beach_reservations` where `customer_id` matches and `start_date >= today`
4. Return summary of what was updated

**Return value:**
```python
{
    'customer_updated': bool,
    'customer_id': int | None,
    'reservations_updated': int
}
```

### 3. Import Service Changes

**File:** `blueprints/admin/services.py`

**Enhanced result structure:**
```python
result = {
    'created': 0,
    'updated': 0,
    'errors': [],
    'total': 0,
    'room_changes': []  # NEW
}
```

**Room change entry:**
```python
{
    'guest_name': str,
    'old_room': str,
    'new_room': str,
    'customer_updated': bool,
    'reservations_updated': int
}
```

### 4. UI Changes

**File:** `templates/admin/hotel_guests/import_result.html`

New section displayed when `room_changes` is not empty:

```
┌─ Cambios de Habitación Detectados (3) ─────────────────────┐
│                                                             │
│  • Juan Pérez: 101 → 205                                   │
│    ✓ Cliente actualizado, 2 reservas actualizadas          │
│                                                             │
│  • María García: 302 → 310                                 │
│    ✓ Cliente actualizado, 0 reservas actualizadas          │
│                                                             │
│  • Pedro López: 415 → 420                                  │
│    ⚠ Cliente no encontrado (sin reservas previas)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No booking_reference in Excel | Falls back to (room + date + name) matching |
| Room change but no beach_customer | Only hotel_guest updated, shows warning |
| Multiple guests same booking | Each processed individually |
| Past reservations | Unchanged (only start_date >= today updated) |
| Same data re-imported | No change detected, normal update |

---

## Files Modified

1. `models/hotel_guest.py` - Enhanced `upsert_hotel_guest()` + new `propagate_room_change()`
2. `blueprints/admin/services.py` - Import function integration
3. `templates/admin/hotel_guests/import_result.html` - Room changes display

---

## Testing

1. Import Excel with existing guest, same room → Normal update
2. Import Excel with existing guest, different room → Room change detected
3. Import Excel without booking_reference → Fallback matching works
4. Room change with existing beach_customer → Customer updated
5. Room change without beach_customer → Warning shown
6. Room change with future reservations → Reservations marked updated
