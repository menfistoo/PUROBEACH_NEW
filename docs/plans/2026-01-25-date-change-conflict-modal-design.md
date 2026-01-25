# Date Change Conflict Modal Design

## Overview

When changing a reservation's date and furniture is unavailable on the new date, show a confirmation modal that allows the user to continue without furniture and enter move mode.

## Current Behavior

When furniture is unavailable, shows a toast "El mobiliario no está disponible. Usa Modo Mover para cambiar." and reverts the date.

## New Behavior

Show a modal with conflict details and options to cancel or continue.

## Modal UI

**Title:** "Mobiliario no disponible"

**Body:**
- Explanation: "El mobiliario actual no está disponible para el [fecha formateada]"
- List of conflicting furniture items (e.g., "H1, H2 - ocupado por María García")
- Info text: "Puedes continuar sin mobiliario y asignarlo con el Modo Mover"

**Actions:**
- Left (secondary): "Cancelar" - reverts date, closes modal
- Right (primary/gold): "Continuar" - executes the flow

**Styling:**
- Existing modal pattern (dark header, white body)
- Warning icon in header
- Max-width ~400px
- Mobile: full-width stacked buttons

## Flow When User Clicks "Continuar"

1. Close modal immediately
2. Call API `change-date` with `clear_furniture: true`
3. Close reservation panel
4. Navigate map to new date
5. Activate Move Mode with reservation in pool
6. Show toast: "Reserva movida al [fecha] - selecciona mobiliario"

## Error Handling

- **API error:** Show error toast, keep modal open for retry
- **Move mode fail:** Show warning, reservation already changed
- **Modal closed without action:** Treat as cancel, revert date

## Edge Cases

- All vs some furniture unavailable: Same flow, show all conflicts
- No furniture assigned: No conflicts, direct date change
- Multi-day reservations: Out of scope (single-day only)
- Move mode already active: Deactivate first, then activate new

## Implementation

**Files to modify:**

1. `save-mixin.js` - Show modal instead of toast, handle confirmation
2. `templates/beach/map.html` - Add modal HTML
3. `blueprints/beach/routes/api/map_res_edit.py` - Add `clear_furniture` parameter

**Estimated:** ~150 lines of code
