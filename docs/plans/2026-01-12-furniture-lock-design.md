# Furniture Lock Feature Design

**Date:** 2026-01-12
**Status:** Approved

## Overview

Add a "lock" feature for reservation furniture assignments. When a customer requests a specific piece of furniture (e.g., "I always want Balinesa #5"), staff can lock that assignment to prevent accidental changes in move mode or reassignment flows.

## Requirements Summary

| Requirement | Decision |
|-------------|----------|
| Lock scope | Per-reservation (not per-customer or per-furniture) |
| Toggle location | Reservation panel (create & edit) |
| Visual feedback (normal) | Panel indicator only (map stays clean) |
| Visual feedback (move mode) | Lock icon overlay on locked furniture |
| Blocked action feedback | Shake animation + action prevented |
| Multi-day behavior | Lock all days together |
| Permissions | Anyone with reservation access can toggle |

## Data Model

Add single column to `beach_reservations` table:

```sql
ALTER TABLE beach_reservations
ADD COLUMN is_furniture_locked INTEGER DEFAULT 0;
```

- `0` = unlocked (default behavior)
- `1` = locked (furniture cannot be moved)

**Rationale:** Storing at reservation level (not furniture assignment level) is simpler and matches business logic - you lock "the reservation," not individual pieces.

## Backend API

### New Endpoint

```
PATCH /beach/api/map/reservations/<id>/toggle-lock
Request:  { "locked": true } or { "locked": false }
Response: { "success": true, "is_furniture_locked": true }
```

### Modified Endpoints

1. **Move mode unassign** (`POST /beach/api/move-mode/unassign`)
   - Check `is_furniture_locked` before unassigning
   - If locked: `{ "success": false, "error": "locked" }`

2. **Furniture reassignment** (`POST /beach/api/map/reservations/<id>/reassign-furniture`)
   - Check lock status before allowing reassignment
   - If locked: return error with message

3. **Reservation data endpoints**
   - Include `is_furniture_locked` in response payloads

### No Changes Needed

- Reservation creation (new reservations start unlocked)
- Date changes (lock protects furniture, not dates)
- State changes (can still cancel/complete locked reservations)

## UI Design

### Reservation Panel Toggle

Location: Furniture section header, next to "Mobiliario" title.

```html
<div class="furniture-section-header d-flex align-items-center justify-content-between">
    <h6 class="mb-0">Mobiliario</h6>
    <button class="btn-lock" id="toggle-furniture-lock"
            aria-label="Bloquear mobiliario"
            data-locked="false">
        <i class="fas fa-lock-open"></i>
    </button>
</div>
```

**Toggle States:**

| State | Icon | Color | Tooltip |
|-------|------|-------|---------|
| Unlocked | `fa-lock-open` | `#9CA3AF` (muted gray) | "Bloquear mobiliario" |
| Locked | `fa-lock` | `#D4AF37` (primary gold) | "Desbloquear mobiliario" |

**CSS:**

```css
.btn-lock {
    background: transparent;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    color: #9CA3AF;
    transition: all 0.2s ease;
}
.btn-lock:hover {
    background: rgba(212, 175, 55, 0.1);
    color: #D4AF37;
}
.btn-lock.locked {
    color: #D4AF37;
}
```

**When locked:**
- "Cambiar mobiliario" button: disabled, gray, tooltip "Mobiliario bloqueado"
- Move mode entry option: hidden or disabled

### Move Mode Lock Indicator

Lock icon overlay appears only when move mode is active:

```html
<g class="furniture locked">
    <rect ... />
    <g class="lock-indicator" transform="translate(X, Y)">
        <circle r="10" fill="#1A3A5C" opacity="0.9"/>
        <text class="fa-icon" fill="#D4AF37" font-size="10">&#xf023;</text>
    </g>
</g>
```

```css
.furniture .lock-indicator {
    display: none;
}
.move-mode-active .furniture.locked .lock-indicator {
    display: block;
}
```

### Shake Animation (Blocked Action)

```css
@keyframes shake-lock {
    0%, 100% { transform: translateX(0); }
    20%, 60% { transform: translateX(-3px); }
    40%, 80% { transform: translateX(3px); }
}
.furniture.shake {
    animation: shake-lock 0.4s ease;
}
```

```javascript
// In MoveMode.js
if (reservation.is_furniture_locked) {
    furnitureElement.classList.add('shake');
    setTimeout(() => furnitureElement.classList.remove('shake'), 400);
    return;
}
```

## Edge Cases

1. **Locking during move mode** - Disabled if reservation is in pool (unassigned)
2. **Multi-day with different furniture** - Lock applies to all days together
3. **State changes** - Lock doesn't affect state transitions
4. **Deleting reservation** - Allowed; lock only protects furniture assignments
5. **Audit trail** - Log lock/unlock in `audit_log` with action `reservation.lock`/`reservation.unlock`

## Files to Modify

| Layer | File | Change |
|-------|------|--------|
| Schema | `database/schema.py` | Add `is_furniture_locked` column |
| Migration | `migrations/` | ALTER TABLE script |
| Model | `models/reservation_crud.py` | Add toggle function |
| Model | `models/move_mode.py` | Check lock before unassign |
| API | `blueprints/beach/routes/api/` | New toggle endpoint |
| Template | `templates/beach/_reservation_panel.html` | Lock toggle button |
| JS | `static/js/map/reservation-panel-v2/` | Toggle handler |
| JS | `static/js/map/MoveMode.js` | Lock check + shake |
| CSS | `static/css/map.css` | Lock indicator styles |

## Testing Considerations

- Toggle lock on/off via panel
- Attempt move mode unassign on locked furniture (should shake, not unassign)
- Attempt reassign on locked furniture (should be blocked)
- Multi-day reservation lock behavior
- Lock state persists after page reload
- Audit log entries created correctly
