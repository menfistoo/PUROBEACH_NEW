# Payment Tracking - Numero de Ticket y Forma de Pago

**Fecha:** 2025-12-28
**Estado:** Completado

## Objetivo
Agregar campos de **numero de ticket** y **forma de pago** a los formularios de reserva para auditoría.

## Requisitos
- **Formas de pago:** Efectivo, Tarjeta, Cargo habitación (fijas)
- **Visibilidad:** Siempre visibles en sección de pago (opcionales)
- **Workflow:** Al marcar pagado o por adelantado, registrar ticket + forma de pago

## Workflow del Usuario
1. Cliente llega con reserva confirmada
2. Trabajador cobra y sienta al cliente
3. Marca como "sentado" y registra número de ticket + forma de pago
4. O puede registrar el pago por adelantado

---

## Progreso de Implementación

### Fase 1: Base de Datos
- [x] Crear migración `add_payment_method.py`

### Fase 2: Modelos
- [x] `models/reservation_crud.py` - Agregar payment_method
- [x] `models/reservation_multiday.py` - Agregar payment_method

### Fase 3: APIs
- [x] `blueprints/beach/routes/api/map_res_create.py`
- [x] `blueprints/beach/routes/api/map_res_details.py`
- [x] `blueprints/beach/routes/api/map_res_edit.py`
- [x] `blueprints/beach/routes/api/reservations.py`

### Fase 4: Interfaz de Usuario
- [x] Panel edición (mapa): `_reservation_panel.html` + `reservation-panel.js`
- [x] Modal edición (lista): `reservations.html`
- [x] Panel creación (mapa): `_new_reservation_panel.html` + `panel-core.js`

### Fase 5: CSS
- [x] `static/css/reservation-panel.css`

---

## Archivos Modificados
| Archivo | Estado |
|---------|--------|
| `database/migrations/add_payment_method.py` | Completado |
| `models/reservation_crud.py` | Completado |
| `models/reservation_multiday.py` | Completado |
| `blueprints/beach/routes/api/map_res_create.py` | Completado |
| `blueprints/beach/routes/api/map_res_details.py` | Completado |
| `blueprints/beach/routes/api/map_res_edit.py` | Completado |
| `blueprints/beach/routes/api/reservations.py` | Completado |
| `templates/beach/_reservation_panel.html` | Completado |
| `static/js/map/reservation-panel.js` | Completado |
| `templates/beach/reservations.html` | Completado |
| `templates/beach/_new_reservation_panel.html` | Completado |
| `static/js/map/reservation-panel/panel-core.js` | Completado |
| `static/css/reservation-panel.css` | Completado |

---

## Notas Técnicas
- Campo `payment_ticket_number` ya existe en BD
- Solo falta agregar `payment_method` TEXT con CHECK constraint
- UI labels en español: "Número de ticket", "Forma de pago"
- Opciones: "Efectivo", "Tarjeta", "Cargo a habitación"
