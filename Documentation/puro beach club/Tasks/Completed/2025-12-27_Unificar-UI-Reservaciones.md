# Unificar UI de Reservaciones - 27 December 2025

## Objetivo
Unificar la experiencia de vista y edición de reservas reutilizando el `ReservationPanel` del mapa (2,112 líneas) que ya tiene el 90% de la funcionalidad requerida.

**Priority:** High
**Status:** REVISED - FULL-SCREEN PAGE IMPLEMENTED

---

## Requerimientos del Usuario

1. **Unificar vista y edición** - No páginas separadas
2. **Sincronizar con Live Map panel** - Compartir código/datos
3. **Estados con colores dinámicos** desde configuración
4. **Selección de mobiliario** que navega al mapa y retorna
5. **Incluir preferencias y notas**
6. **Panel lateral** (consistencia con el mapa)
7. **Historial de estados** incluido en el panel

---

## Fases de Implementación

### Fase 1: API de Estados (Backend) ✅
- [x] Crear `blueprints/beach/routes/api/states.py`
- [x] Registrar en `blueprints/beach/routes/api/__init__.py`

### Fase 2: Adaptar ReservationPanel para Standalone ✅
- [x] Agregar opción `context: 'map' | 'standalone'`
- [x] Agregar método `setStates(states)` y `fetchStates()`
- [x] Agregar sección de historial de estados (colapsable)
- [x] Modificar `enterReassignmentMode()` para navegar al mapa

### Fase 3: Template y Lista de Reservaciones ✅
- [x] Reutilizar `templates/beach/_reservation_panel.html` existente
- [x] Modificar `templates/beach/reservations.html` - filas clickables
- [x] Crear `static/js/reservation-panel-standalone.js`

### Fase 4: CSS para Modo Standalone ✅
- [x] Agregar estilos `.reservation-panel.standalone` en `reservation-panel.css`
- [x] Agregar estilos para historial de estados

### Fase 5: Integración con Mapa ✅
- [x] Detectar params `mode=furniture_select` en map
- [x] Implementar flujo de retorno con mensaje de éxito

### Fase 6: Redirección de Rutas ✅
- [x] Modificar rutas detail/edit para redirigir a lista con panel

---

## Archivos Involucrados

**Crear:**
- `blueprints/beach/routes/api/states.py`
- `static/js/reservation-panel-standalone.js`
- `templates/beach/_unified_reservation_panel.html`

**Modificar:**
- `static/js/map/reservation-panel.js`
- `templates/beach/reservations.html`
- `static/css/reservation-panel.css`
- `blueprints/beach/routes/api/__init__.py`
- `blueprints/beach/routes/reservations.py`
- `templates/beach/map.html`

---

## Progress Log

### Session 1 - 27 Dec 2025
- Started implementation
- Plan approved by user
- **Completed all 6 phases:**
  1. Created `/beach/api/states` endpoint for dynamic state colors
  2. Extended ReservationPanel with standalone mode support
  3. Added state history section (collapsible)
  4. Modified reservations.html with clickable rows and panel integration
  5. Created reservation-panel-standalone.js wrapper
  6. Added CSS for standalone mode and history section
  7. Added furniture_select mode handling in map
  8. Redirected detail/edit routes to list with panel open

**Files Created:**
- `blueprints/beach/routes/api/states.py`
- `static/js/reservation-panel-standalone.js`

**Files Modified:**
- `blueprints/beach/routes/api/__init__.py`
- `static/js/map/reservation-panel.js`
- `templates/beach/_reservation_panel.html`
- `templates/beach/reservations.html`
- `templates/beach/map.html`
- `static/css/reservation-panel.css`
- `blueprints/beach/routes/reservations.py`

### Session 2 - 27 Dec 2025 (Revised Approach)
- User requested full-screen page instead of side panel
- Reason: Panel is for mobile/quick use on map; reservations tab for desktop, robust editing

**Changes Made:**
1. Reverted route redirections to render actual pages
2. Created unified full-screen template `reservation_unified.html`
3. Created dedicated CSS `reservation-unified.css`
4. Created JavaScript `reservation-unified.js` for inline editing
5. Updated `reservations.html` to link to unified page
6. Updated map furniture_select return handling

**New Files Created:**
- `templates/beach/reservation_unified.html` - Full-screen view/edit page
- `static/css/reservation-unified.css` - Unified page styles
- `static/js/reservation-unified.js` - Inline editing and state management

**Features:**
- 2-column layout (8-4 grid) following existing conventions
- Inline editing for num_people, observations, paid status
- State toggle buttons (immediate save via API)
- Preference checkboxes (batched save)
- "Cambiar Mobiliario" button navigates to map
- Unsaved changes warning on page leave
- Toast notifications for feedback

