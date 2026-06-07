# Backlog (ideas futuras)

> Registro local de ideas/funcionalidades futuras. (El servidor no tiene `gh`/token,
> así que no se pueden crear GitHub Issues automáticamente; pasar a Issues cuando se pueda.)

## Lista de espera: detectar duplicados contra reservas reales
**Prioridad:** futuro · **Etiquetas sugeridas:** feature, planning, reservations · **Reportado:** 2026-06-07 (usuaria)

La lista de espera debería **monitorizar las reservas efectivas** y avisar cuando se intente
crear una entrada para un cliente/habitación que **ya tiene una reserva real**.

**Ejemplo:** creo una entrada en lista de espera para la **Hab. 8005**, pero ya existe una
**reserva efectiva** (activa, no liberada) para esa misma habitación/huésped → avisar del
posible duplicado (como el aviso de duplicados al crear una reserva normal).

**Notas de diseño:**
- Identidad preferente por **nº de reserva** (`booking_reference`), habitación como respaldo.
- Considerar solape de **fechas** (sólo avisar si la reserva efectiva solapa la fecha de la entrada).
- Comparar contra estados **no liberadores** (Pendiente/Confirmada/Check-in/Activa…), ignorando Cancelada/No-Show/Liberada.
- UX: aviso **no bloqueante** (permitir continuar si el personal confirma), mostrando la reserva existente (ticket, hab., fecha).
