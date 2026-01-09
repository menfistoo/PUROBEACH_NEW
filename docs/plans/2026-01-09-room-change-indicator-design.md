# Room Change Visual Indicator Design

**Date:** 2026-01-09
**Status:** Approved

## Overview

Add a visual indicator on reservations to show when the guest's current room differs from the room they had when the reservation was created. This helps staff understand that a guest has changed rooms during their stay.

## Requirements

- Show indicator in **both** reservation list table and detail panel
- Store original room on reservation at creation time
- Display icon with tooltip showing the original room
- Only applies to "interno" (hotel guest) customers

## Database Schema

Add `original_room` column to `beach_reservations`:

```sql
ALTER TABLE beach_reservations
ADD COLUMN original_room VARCHAR(20);
```

**Behavior:**
- Populated when creating reservation for "interno" customer
- NULL for "externo" customers (no room)
- Existing reservations backfilled from current customer room

## Room Change Detection Logic

Show indicator when ALL conditions are true:
1. Customer is "interno" (has a room)
2. `original_room` is not NULL
3. `original_room` != customer's current `room_number`

**Query example:**
```sql
SELECT r.*, c.room_number as current_room,
       CASE WHEN r.original_room IS NOT NULL
            AND r.original_room != c.room_number
            THEN 1 ELSE 0 END as room_changed
FROM beach_reservations r
JOIN beach_customers c ON r.customer_id = c.id
```

## Visual Indicator

**Icon:** FontAwesome `fa-right-left`
**Color:** Orange/warning (`#E5A33D`)
**Interaction:** Tooltip on hover

### Reservation List
```html
<td>
  602
  <i class="fa-solid fa-right-left text-warning ms-1"
     data-bs-toggle="tooltip"
     title="Cambio de hab. 501"></i>
</td>
```

### Detail Panel
```html
<span class="value">
  602
  <i class="fa-solid fa-right-left text-warning ms-1"
     data-bs-toggle="tooltip"
     title="Habitacion original: 501"></i>
</span>
```

## Files to Modify

1. `database.py` - Add column migration
2. `models/reservation.py` or `blueprints/beach/services/reservation_service.py` - Store original_room on create
3. Reservation queries - Include room_changed flag
4. `templates/beach/reservations.html` - Add icon in list
5. `static/js/map.js` or panel component - Add icon in detail panel

## Migration Strategy

1. Add column with NULL default
2. Backfill existing reservations:
   ```sql
   UPDATE beach_reservations
   SET original_room = (
     SELECT room_number FROM beach_customers WHERE id = customer_id
   )
   WHERE customer_id IN (
     SELECT id FROM beach_customers WHERE customer_type = 'interno'
   )
   ```
3. New reservations automatically populated on creation
