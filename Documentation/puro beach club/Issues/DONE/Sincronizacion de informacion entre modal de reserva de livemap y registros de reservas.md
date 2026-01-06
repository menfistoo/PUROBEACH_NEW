
Ni toda la informacion se está sincronizando entre el modal de reserva desde el live map y el registro de reserva en beach/reservations

Numero de ticket; forma de pago y notas

## Resolución (2026-01-06)

**Causa raíz:** El endpoint API `/api/reservations/<id>` en `blueprints/beach/routes/api/reservations.py` no incluía `payment_ticket_number` ni `payment_method` en la respuesta JSON.

**Corrección:** Se agregaron los campos faltantes al endpoint `reservation_detail`:
- `payment_ticket_number`
- `payment_method`

**Archivo modificado:** `blueprints/beach/routes/api/reservations.py` (líneas 55-56)

**Estado:** CORREGIDO - Mover a carpeta DONE
