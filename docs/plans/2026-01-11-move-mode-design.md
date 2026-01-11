# Move Mode Design

## Overview

A special map mode for reorganizing reservation furniture assignments. Staff can "pick up" reservations from their current furniture (sending them to a pool), then reassign them to different furniture - all while seeing visual guidance based on preferences.

### Primary Use Cases

1. **During-day conflicts** (primary) - A specific reservation needs to move, affecting others like dominoes
2. **Start of day setup** - Staff reorganizes based on actual conditions (weather, VIP requests, etc.)

## Entry Points

### 1. Map Toolbar Button

- New "Modo Mover" button in the map toolbar (next to existing edit mode button)
- Click to enter move mode
- Button changes to "Salir del Modo Mover" when active

### 2. Reservation Edit Modal

- In the furniture assignment section of the edit modal
- New button: "Reorganizar en mapa"
- Clicking this:
  - Closes the modal
  - Enters move mode
  - Automatically unassigns that reservation's furniture (sends to pool)
  - Selects it in the pool, ready for placement

### Visual Indication

When in move mode:
- Map gets a subtle visual change (e.g., blue tinted border or header bar saying "Modo Mover")
- Toolbar button is highlighted/active
- Side panel appears with the reservation pool

## Reservation Pool Panel

### Panel Location & Layout

- **Position:** Right side panel (similar to existing reservation panel pattern)
- **Width:** ~320px, collapsible
- **Header:** "Reservas sin asignar" with count badge (e.g., "3")

### Reservation Cards (Collapsed - Default)

```
┌─────────────────────────────────┐
│ 🏠 Hab. 123 - García López      │
│ 👥 3 personas  ●●○ 2 prefs      │
│ 📍 Era: H01, H02, H03           │
└─────────────────────────────────┘
```

- Room/name as header
- People count + preference count indicator (filled/empty dots)
- "Era:" showing original furniture (helps staff remember where they were)

### Reservation Cards (Expanded - On Click)

```
┌─────────────────────────────────────┐
│ 🏠 Hab. 123 - García López      ▼   │
│ 👥 3 personas                       │
│ 📍 Era: H01, H02, H03               │
├─────────────────────────────────────┤
│ Preferencias:                       │
│  ☀️ Primera línea                   │
│  🌴 Cerca de palmeras               │
│ Notas: Cliente VIP, cumpleaños      │
│                                     │
│ [Restaurar posición original]       │
└─────────────────────────────────────┘
```

- Full preference list with icons
- Notes from reservation
- Quick action to restore to original position

### Selection State

- Selected card has gold border highlight
- Only one reservation can be selected at a time
- Click another card to switch selection

## Map Interactions

### Unassigning Furniture (Furniture → Pool)

**Normal Click on occupied furniture:**
- Entire reservation group is unassigned
- All furniture for that reservation becomes "available" visually
- Reservation card appears in pool panel
- Auto-save: API call removes furniture assignments immediately

**Ctrl+Click on occupied furniture:**
- Only that specific furniture is unassigned
- Reservation stays partially assigned (other furniture keeps assignment)
- Pool card shows reduced count (e.g., "2 de 3 asignados")
- Warning badge on card indicates incomplete assignment

### Visual Feedback on Unassign

- Brief animation: furniture "releases" (subtle pulse/fade)
- Card slides into pool panel from the map
- Undo toast appears: "H01 liberada - [Deshacer]" (3 second timeout)

### Assigning Furniture (Pool → Furniture)

**With reservation selected in pool:**
1. Compatible empty furniture highlights (gold glow based on preferences)
2. Incompatible furniture dims slightly (still clickable)
3. Click empty furniture to assign
4. If group needs more furniture, keep clicking until complete
5. Progress shown on pool card: "1 de 3 asignados ✓✓○"

**Completion:**
- When all people have furniture, card shows green checkmark
- Card remains in panel until fully assigned, then auto-removes
- Success toast: "Hab. 123 asignada a H05, H06, H07"

## Preference Highlighting & Guidance

### How Preferences Map to Furniture

The system uses `beach_preferences.maps_to_feature` to link preferences to furniture features:

| Preference | Maps to Feature | Furniture Match |
|------------|-----------------|-----------------|
| Primera línea | `first_row` | Zone or furniture tag |
| Sombra | `shaded` | Furniture near umbrellas/trees |
| Cerca del bar | `near_bar` | Proximity to bar zone |
| VIP | `vip_area` | VIP zone furniture |

### Visual Highlighting When Placing

**When a reservation is selected in the pool:**

1. **Strong match (all preferences):** Gold glow + preference icons appear on furniture
2. **Partial match (some preferences):** Lighter gold highlight
3. **No match:** Slightly dimmed (40% opacity), still clickable
4. **Occupied furniture:** Normal state (no highlight), not clickable

### Preference Legend

Small floating legend appears near selected pool card:
```
┌─────────────────────────┐
│ Buscando:               │
│ ☀️ Primera línea        │
│ 🌴 Cerca de palmeras    │
└─────────────────────────┘
```

### Override Behavior

Staff can always click non-highlighted furniture - system trusts their judgment. No blocking, just guidance.

## Multi-Day Reservations

### Identifying Multi-Day Reservations

Pool cards show a badge when reservation spans multiple days:
```
┌─────────────────────────────────┐
│ 🏠 Hab. 123 - García López  📅3 │
│ 👥 3 personas  ●●○ 2 prefs      │
│ 📍 Era: H01, H02, H03           │
└─────────────────────────────────┘
```

The `📅3` badge indicates 3-day reservation.

### Warning on Unassign

When clicking furniture that belongs to a multi-day reservation:
- Toast warning appears: "⚠️ Reserva de 3 días - cambios solo afectan hoy"
- Warning is informational only, action proceeds
- Shown once per reservation (not on every furniture click for same group)

### Warning on Assign

When placing a multi-day reservation on new furniture:
- Similar toast: "⚠️ Asignando solo para hoy - otros días mantienen H01, H02, H03"
- Staff knows tomorrow's assignment is different

### Expanded Card Shows Day Context

```
┌─────────────────────────────────────┐
│ 🏠 Hab. 123 - García López  📅3  ▼  │
│ ...                                 │
├─────────────────────────────────────┤
│ Días de reserva:                    │
│  11 Ene: H01, H02, H03 (hoy)       │
│  12 Ene: H01, H02, H03             │
│  13 Ene: H01, H02, H03             │
└─────────────────────────────────────┘
```

## Undo, Saving & Exit

### Auto-Save Behavior

Every action saves immediately via API:
- Unassign: Removes furniture assignment for the date
- Assign: Creates furniture assignment for the date

### Undo System

**Undo Stack:**
- Each action pushed to local undo stack
- Maximum 20 actions remembered
- Stack clears when exiting move mode

**Undo UI:**
- Toast with "Deshacer" button (3 seconds visible)
- Keyboard shortcut: Ctrl+Z
- Undo button in move mode toolbar for last action

**Undo Action:**
- Reverses the API call
- Animates furniture/card back to previous state
- Toast confirms: "Acción deshecha"

### Exit Behavior

**Exit Blocked When Pool Not Empty:**
- "Salir" button disabled while reservations in pool
- Tooltip: "Asigna todas las reservas antes de salir"
- Pool header pulses briefly to draw attention

**Exit When Pool Empty:**
- Click "Salir del Modo Mover" or press Escape
- Move mode deactivates
- Side panel closes
- Map returns to normal state
- Undo stack clears

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Click | Unassign single furniture (not whole group) |
| Ctrl+Z | Undo last action |
| Escape | Exit move mode (if pool empty) |

## Technical Implementation

### New Backend Endpoints

```
POST   /beach/api/map/move-mode/unassign
       Body: {reservation_id, furniture_ids[], date}
       → Removes furniture assignments for date

POST   /beach/api/map/move-mode/assign
       Body: {reservation_id, furniture_ids[], date}
       → Creates furniture assignments for date

GET    /beach/api/map/move-mode/preferences-match
       Query: ?preference_codes=X,Y&date=YYYY-MM-DD
       → Returns furniture IDs with match scores
```

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `MoveMode` class | Main controller, manages state & mode toggle |
| `ReservationPool` | Side panel with card list |
| `ReservationCard` | Individual expandable card |
| `PreferenceHighlighter` | Applies highlights to map furniture |
| `UndoManager` | Tracks actions, handles Ctrl+Z |

### State Management

```javascript
moveMode: {
  active: boolean,
  pool: [{ reservation, originalFurniture[], assignedCount }],
  selectedReservationId: number | null,
  undoStack: [{ type, data }],
  currentDate: string
}
```

### Integration Points

- **Map renderer:** Add move mode visual layer
- **Selection manager:** Modify click behavior in move mode
- **Reservation modal:** Add "Reorganizar en mapa" button
- **Map toolbar:** Add "Modo Mover" toggle button

## UI/UX Notes

- Must follow `/frontend-design` guidelines for all UI implementation
- Use design system colors (Primary Gold: #D4AF37, Deep Ocean: #1A3A5C)
- Consistent with existing map interaction patterns
