# Bug: Sistema de Precios para Huéspedes de Hotel

**Fecha:** 2025-12-27
**Estado:** FIXED - PENDIENTE DE PRUEBAS
**Prioridad:** Alta

## Descripción

Dos problemas relacionados con el sistema de precios para huéspedes de hotel:

### Problema 1: Precios no se guardan ✅ CORREGIDO
- Al editar una reserva de un huésped de hotel
- Cambiar el precio final (ej: 60€)
- Al guardar, muestra "cambios guardados exitosamente"
- Al volver a abrir la reserva, el precio final aparece como 0€

### Problema 2: Filtro de paquetes incorrecto ⚠️ CONFIGURACIÓN DE DATOS
- Los huéspedes internos (del hotel) están viendo precios/paquetes que deberían ser exclusivos para clientes externos
- El filtro de tipo de cliente no se está aplicando correctamente

## Hallazgos de la Investigación (2025-12-27)

### Problema 1: Causa Raíz Identificada y Corregida

**Dos problemas encontrados:**

1. **API de actualización ignoraba campos de precio**
   - Archivo: `blueprints/beach/routes/api/map_res_edit.py`
   - El endpoint `/map/reservations/{id}/update` tenía una lista blanca de campos permitidos que NO incluía:
     - `price`, `final_price`, `package_id`
     - `minimum_consumption_amount`, `minimum_consumption_policy_id`
   - El frontend enviaba `total_price` pero el backend lo filtraba silenciosamente

2. **API de detalles no retornaba campos de precio**
   - Archivo: `blueprints/beach/routes/api/map_res_details.py`
   - El endpoint `/map/reservations/{id}/details` no incluía campos de precio en la respuesta
   - El frontend no podía mostrar ni comparar los precios existentes

3. **Frontend usaba nombre de campo incorrecto**
   - Archivo: `static/js/map/reservation-panel.js`
   - El código buscaba `total_price` pero la API devuelve `final_price`

**Correcciones aplicadas:**
- Agregado `price`, `final_price`, `package_id`, `minimum_consumption_amount`, `minimum_consumption_policy_id` a `allowed_fields`
- Agregado mapeo `total_price` → `final_price` en `field_mapping`
- Agregado validación para los nuevos campos de precio
- Actualizada respuesta de details API para incluir todos los campos de precio
- Actualizado frontend para usar `final_price` con fallback a `total_price`

### Problema 2: Análisis

**La lógica de filtrado está CORRECTA**

El query SQL en `models/package.py:get_active_packages_for_date()` filtra correctamente:
```sql
AND (customer_type = ? OR customer_type = 'both' OR customer_type IS NULL)
```

**El problema es de CONFIGURACIÓN DE DATOS:**

Estado actual de paquetes en la base de datos:
| ID | Nombre | customer_type |
|----|--------|---------------|
| 1 | VIP Package | both |
| 2 | Family Package | both |
| 3 | Classic Package | interno |
| 4 | Teste - externo | both |

**Observación:** No existe ningún paquete con `customer_type = 'externo'`

El paquete "Teste - externo" tiene `customer_type = 'both'` en lugar de `'externo'`.

**Solución:** Configurar correctamente el `customer_type` de cada paquete desde:
`/beach/config/packages` → Editar paquete → Campo "Cliente"

## Archivos Modificados

### Fix 1: Edición de reservas (precios no se guardaban)

1. `blueprints/beach/routes/api/map_res_edit.py`
   - Línea 188-194: Agregados campos de precio a allowed_fields
   - Línea 197-200: Agregado field_mapping para total_price
   - Línea 246-282: Agregada validación de campos de precio

2. `blueprints/beach/routes/api/map_res_details.py`
   - Línea 101-110: Agregados campos de precio a la respuesta

3. `static/js/map/reservation-panel.js`
   - Línea 927, 1412: Actualizado para usar final_price primero

### Fix 2: Creación de reservas (precios siempre 0)

4. `blueprints/beach/routes/api/map_res_create.py`
   - Línea 17: Agregado import de calculate_reservation_pricing
   - Línea 60-73: Lectura de package_id y price_override del request
   - Línea 159-191: Cálculo de precios usando pricing_service
   - Línea 207-214, 247-254: Uso de precios calculados en vez de hardcoded 0.0

## Campos de Precio en Reservas
- `price` - Precio base
- `final_price` - Precio final (editable)
- `paid` - Estado de pago (0/1)
- `payment_ticket_number` - Número de ticket
- `minimum_consumption_amount` - Consumo mínimo
- `package_id` - Paquete seleccionado

## Próximos Pasos

1. [ ] Probar guardado de precios en el navegador
2. [x] Verificar que el precio se mantiene después de recargar
3. [x] Configurar paquetes con customer_type correcto en `/beach/config/packages`
