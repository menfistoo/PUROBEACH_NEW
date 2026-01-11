# Características System Design

**Date:** 2026-01-11
**Status:** Approved
**Author:** Claude + User collaboration

## Overview

Replace the hardcoded preferences system with a unified, configurable "Características" system that can be applied to both furniture (what it HAS) and reservations (what they WANT), enabling automatic matching without code changes.

## Problem Statement

Current system has:
- `beach_preferences` table with 8 seeded preferences (configurable via admin UI)
- Furniture `features` column that is **never used** by matching algorithm
- Hardcoded `PREFERENCE_TO_FEATURE` Python dict that maps preferences to features
- Feature inference based on zone names (fragile, requires Spanish naming conventions)

**Result:** Adding new preferences requires code changes to the hardcoded mapping.

## Solution

Unified "Características" concept:
- One entity type that gets tagged on both furniture and reservations
- Direct database matching (no hardcoded mapping)
- Fully configurable via admin UI

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Relationship model | Unified concept | Same característica applies to furniture and reservations |
| Naming | "Características" | Neutral term, works for both furniture attributes and customer desires |
| Organization | Flat list | Keep it simple, no categories |
| Matching weight | Equal weight | Score = matched / total requested |
| Migration | Preserve data | Convert existing preferences and furniture features |
| Customer profile | Keep customer-level | Auto-populate reservations from customer defaults |

## Data Model

### New Tables

```sql
-- Main characteristics table
CREATE TABLE beach_characteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    color TEXT DEFAULT '#D4AF37',
    active INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- What furniture HAS
CREATE TABLE beach_furniture_characteristics (
    furniture_id INTEGER REFERENCES beach_furniture(id) ON DELETE CASCADE,
    characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
    PRIMARY KEY (furniture_id, characteristic_id)
);

-- What reservations WANT
CREATE TABLE beach_reservation_characteristics (
    reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
    characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
    PRIMARY KEY (reservation_id, characteristic_id)
);

-- Customer default characteristics
CREATE TABLE beach_customer_characteristics (
    customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
    characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
    PRIMARY KEY (customer_id, characteristic_id)
);
```

### Tables to Remove

- `beach_preferences`
- `beach_customer_preferences`

### Columns to Remove

- `beach_reservations.preferences` (TEXT/CSV)
- `beach_furniture.features` (TEXT/CSV)

## Migration Strategy

### Step 1: Create new tables
Create all 4 new tables without dropping old ones.

### Step 2: Migrate preferences → características
```python
INSERT INTO beach_characteristics (code, name, description, icon, active)
SELECT code, name, description, icon, active FROM beach_preferences;
```

### Step 3: Migrate customer preferences
```python
INSERT INTO beach_customer_characteristics (customer_id, characteristic_id)
SELECT cp.customer_id, c.id
FROM beach_customer_preferences cp
JOIN beach_preferences p ON cp.preference_id = p.id
JOIN beach_characteristics c ON c.code = p.code;
```

### Step 4: Migrate reservation preferences
```python
# Parse CSV from beach_reservations.preferences
# Match codes to beach_characteristics.code
# Insert into beach_reservation_characteristics
```

### Step 5: Migrate furniture features
```python
# Parse CSV from beach_furniture.features
# Match to characteristic codes (may need mapping for legacy values)
# Insert into beach_furniture_characteristics
```

### Step 6: Clean up
- Drop old tables and columns
- Remove old code files

## Admin UI

### Configuration Page: `/beach/config/characteristics`

**List View:**
- Table: code, name, icon (rendered), color (swatch), active (toggle)
- Drag-to-reorder (display_order)
- Edit/delete actions per row

**Form Fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Código | Text | Yes | Unique, snake_case |
| Nombre | Text | Yes | Max 50 chars |
| Descripción | Textarea | No | Max 200 chars |
| Icono | Icon picker | No | FontAwesome class |
| Color | Color picker | No | Hex color |
| Activo | Checkbox | No | Default: true |

**Navigation:**
- Sidebar: "Configuración" → "Características"
- Icon: `fa-list-check`
- Order: after "Estados"

## Integration Points

### Furniture Form
- Add "Características" section
- Multi-select checkboxes with icons
- Saves to `beach_furniture_characteristics`

### Reservation Panel (Map)
- Replace "Preferencias" with "Características"
- Multi-select tag selector
- Auto-populated from customer profile
- Saves to `beach_reservation_characteristics`

### Customer Form
- Add "Características por defecto" section
- Multi-select checkboxes
- Used to auto-populate new reservations

### Suggestion Algorithm

**Old logic (to remove):**
```python
PREFERENCE_TO_FEATURE = {
    'pref_primera_linea': ['first_line', 'premium'],
    # ... hardcoded mapping
}

def get_furniture_features(furniture_id):
    # Infers from zone name and position
```

**New logic:**
```python
def score_characteristic_match(furniture_id: int, requested_ids: list[int]) -> float:
    """Direct database match. Score = matched / total requested."""
    furniture_char_ids = get_furniture_characteristic_ids(furniture_id)
    if not requested_ids:
        return 1.0  # No requirements = perfect match
    matched = len(set(furniture_char_ids) & set(requested_ids))
    return matched / len(requested_ids)

def get_furniture_characteristic_ids(furniture_id: int) -> list[int]:
    """Get characteristic IDs assigned to furniture."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT characteristic_id
            FROM beach_furniture_characteristics
            WHERE furniture_id = ?
        """, (furniture_id,)).fetchall()
        return [r['characteristic_id'] for r in rows]
```

## Files Summary

### New Files
```
models/characteristic.py
models/characteristic_assignments.py
blueprints/beach/routes/config/characteristics.py
templates/beach/config/characteristics.html
templates/beach/config/characteristic_form.html
```

### Modified Files
```
database/schema.py
database/seed.py
models/reservation_suggestions_scoring.py
blueprints/beach/routes/config/__init__.py
blueprints/beach/routes/config/furniture.py
templates/beach/config/furniture_form.html
templates/beach/map/_reservation_panel.html
static/js/map/reservation-panel-v2/ (rename preferences-mixin.js)
```

### Deleted Files
```
models/preference.py
models/reservation_preferences.py
blueprints/beach/routes/config/preferences.py
templates/beach/config/preferences.html
templates/beach/config/preference_form.html
```

## Permissions

| Code | Description |
|------|-------------|
| `beach.characteristics.view` | View characteristics list |
| `beach.characteristics.manage` | Create, edit, delete characteristics |

## Seed Data

Initial características (migrated from preferences):
```python
characteristics_data = [
    ('primera_linea', 'Primera Línea', 'Mobiliario en primera línea de playa', 'fa-water', '#1A3A5C'),
    ('sombra', 'Sombra', 'Zona con sombra', 'fa-umbrella', '#4A7C59'),
    ('cerca_mar', 'Cerca del Mar', 'Lo más cerca posible del mar', 'fa-anchor', '#1A3A5C'),
    ('tranquila', 'Zona Tranquila', 'Zona alejada y tranquila', 'fa-volume-off', '#6B7280'),
    ('vip', 'VIP', 'Zona premium', 'fa-star', '#D4AF37'),
    ('cerca_bar', 'Cerca del Bar', 'Cerca del bar o zona de servicio', 'fa-martini-glass', '#C1444F'),
    ('familia', 'Zona Familiar', 'Zona adecuada para familias', 'fa-children', '#E5A33D'),
    ('accesible', 'Acceso Fácil', 'Acceso fácil para movilidad reducida', 'fa-wheelchair', '#4A7C59'),
]
```

## Success Criteria

1. Admin can create/edit/delete características without code changes
2. Furniture can be tagged with características via admin form
3. Reservations can request características via reservation panel
4. Suggestion algorithm matches furniture to reservations by características
5. Customer profile stores default características that auto-populate reservations
6. All existing preference data is preserved through migration
