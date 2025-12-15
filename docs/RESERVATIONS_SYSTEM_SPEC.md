# ESPECIFICACIÓN COMPLETA: Sistema de Reservas Beach Club

## Contexto del Proyecto

Sistema de gestión de reservas para Beach Club profesional. Este documento describe TODA la funcionalidad requerida para implementar el módulo de reservas.

---

## 1. ESQUEMA DE BASE DE DATOS

### 1.1 Tabla Principal: `beach_reservations`

```sql
CREATE TABLE beach_reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    ticket_number TEXT UNIQUE,           -- Formato: YYMMDDRR (ej: "25011601")
    reservation_date DATE NOT NULL,       -- Fecha de la reserva
    num_people INTEGER NOT NULL,
    time_slot TEXT DEFAULT 'all_day',     -- 'all_day', 'morning', 'afternoon'
    current_states TEXT DEFAULT '',       -- CSV de estados: "Confirmada, Sentada"
    current_state TEXT DEFAULT 'Confirmada',  -- Estado principal para display

    -- Campos de pricing
    payment_status TEXT DEFAULT 'NO',     -- 'SÍ' o 'NO'
    price REAL DEFAULT 0.0,
    final_price REAL DEFAULT 0.0,
    hamaca_included INTEGER DEFAULT 1,    -- 1 = incluida (gratis), 0 = con cargo
    price_catalog_id INTEGER,             -- FK a beach_price_catalog
    paid INTEGER DEFAULT 0,               -- 1 = pagado

    -- Campos de cargo a habitación
    charge_to_room INTEGER DEFAULT 0,
    charge_reference TEXT DEFAULT '',

    -- Consumo mínimo
    minimum_consumption_amount REAL DEFAULT 0.0,
    minimum_consumption_policy_id INTEGER,
    consumption_charged_to_pms INTEGER DEFAULT 0,
    consumption_charged_at TIMESTAMP,
    consumption_charged_by TEXT,

    -- Check-in/out del huésped
    check_in_date DATE,
    check_out_date DATE,

    -- Preferencias y observaciones
    preferences TEXT DEFAULT '',          -- CSV de preferencias
    observations TEXT DEFAULT '',

    -- Multi-día (parent/child)
    parent_reservation_id INTEGER,        -- NULL si es parent o single-day
    reservation_type TEXT DEFAULT 'normal' CHECK(reservation_type IN ('normal', 'bloqueo')),

    -- Auditoría
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES beach_customers(id),
    FOREIGN KEY (price_catalog_id) REFERENCES beach_price_catalog(id),
    FOREIGN KEY (parent_reservation_id) REFERENCES beach_reservations(id),
    FOREIGN KEY (minimum_consumption_policy_id) REFERENCES beach_minimum_consumption_policies(id)
);
```

### 1.2 Asignaciones de Mobiliario por Día: `beach_reservation_furniture`

```sql
CREATE TABLE beach_reservation_furniture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    furniture_id INTEGER NOT NULL,
    assignment_date DATE NOT NULL,        -- Fecha específica de asignación
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id) REFERENCES beach_reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (furniture_id) REFERENCES beach_furniture(id),
    UNIQUE(reservation_id, furniture_id, assignment_date)
);

-- Índice crítico para disponibilidad
CREATE INDEX idx_reservation_furniture_date
ON beach_reservation_furniture(assignment_date, furniture_id);
```

### 1.3 Estados Diarios: `beach_reservation_daily_states`

```sql
CREATE TABLE beach_reservation_daily_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    state_date DATE NOT NULL,
    states TEXT DEFAULT '',               -- CSV de estados para ese día
    notes TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,

    FOREIGN KEY (reservation_id) REFERENCES beach_reservations(id) ON DELETE CASCADE,
    UNIQUE(reservation_id, state_date)
);
```

### 1.4 Historial de Estados: `reservation_status_history`

```sql
CREATE TABLE reservation_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    status_type TEXT NOT NULL,            -- Nombre del estado
    action TEXT NOT NULL,                 -- 'added' o 'removed'
    changed_by TEXT NOT NULL,
    notes TEXT DEFAULT '',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id) REFERENCES beach_reservations(id) ON DELETE CASCADE
);
```

### 1.5 Configuración de Estados: `beach_reservation_states`

```sql
CREATE TABLE beach_reservation_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#CCCCCC',
    icon TEXT,
    display_order INTEGER DEFAULT 0,
    is_availability_releasing INTEGER DEFAULT 0,  -- 1 = libera disponibilidad
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Estados predeterminados con prioridades
INSERT INTO beach_reservation_states (name, color, icon, display_order, is_availability_releasing) VALUES
('Confirmada', '#28a745', 'fa-check-circle', 1, 0),
('Sentada', '#17a2b8', 'fa-chair', 2, 0),
('Cobrada', '#ffc107', 'fa-euro-sign', 3, 0),
('Cancelada', '#dc3545', 'fa-times-circle', 4, 1),
('No-Show', '#6c757d', 'fa-user-slash', 5, 1),
('Liberada', '#f8f9fa', 'fa-unlock', 6, 1);
```

### 1.6 Tags para Reservas: `beach_tags` y `beach_reservation_tags`

```sql
CREATE TABLE beach_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#6c757d',
    description TEXT DEFAULT '',
    display_order INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_by TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE beach_reservation_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    assigned_by TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (reservation_id) REFERENCES beach_reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES beach_tags(id),
    UNIQUE(reservation_id, tag_id)
);
```

### 1.7 Catálogo de Precios: `beach_price_catalog`

```sql
CREATE TABLE beach_price_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,              -- 'hamaca', 'balinesa', 'servicio', etc.
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price_interno REAL DEFAULT 0.0,       -- Precio para huéspedes internos
    price_externo REAL DEFAULT 0.0,       -- Precio para clientes externos
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.8 Políticas de Consumo Mínimo: `beach_minimum_consumption_policies`

```sql
CREATE TABLE beach_minimum_consumption_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_name TEXT NOT NULL UNIQUE,
    furniture_type TEXT,                  -- 'hamaca', 'balinesa', NULL para todos
    zone_id INTEGER,                      -- NULL para todas las zonas
    customer_type TEXT,                   -- 'interno', 'externo', NULL para todos
    minimum_amount REAL NOT NULL,
    applies_weekends_only INTEGER DEFAULT 0,
    applies_holidays_only INTEGER DEFAULT 0,
    start_date DATE,
    end_date DATE,
    priority INTEGER DEFAULT 0,           -- Mayor = más específico
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (zone_id) REFERENCES beach_zones(id)
);
```

---

## 2. NUMERACIÓN DE RESERVAS

### 2.1 Formato del Ticket Number

```
YYMMDDRR donde:
- YY = Año (2 dígitos)
- MM = Mes (2 dígitos)
- DD = Día (2 dígitos)
- RR = Secuencial del día (01-99)

Ejemplo: 25011601 = Primera reserva del 16 de enero 2025
```

### 2.2 Generación Atómica con Reintentos

```python
def generate_reservation_number(reservation_date=None, cursor=None, max_retries=5):
    """
    Genera número único con protección contra race conditions.

    Args:
        reservation_date: Fecha de reserva (default: hoy)
        cursor: Cursor de transacción activa
        max_retries: Intentos máximos ante colisión

    Returns:
        str: Número de reserva único (YYMMDDRR)

    Raises:
        ValueError: Si no se puede generar número único
    """
    if not reservation_date:
        reservation_date = datetime.now().strftime('%Y-%m-%d')

    date_obj = datetime.strptime(reservation_date, '%Y-%m-%d')
    date_prefix = date_obj.strftime('%y%m%d')  # YYMMDD

    for attempt in range(max_retries):
        # Buscar máximo secuencial del día
        cursor.execute('''
            SELECT MAX(CAST(SUBSTR(ticket_number, 7, 2) AS INTEGER)) as max_seq
            FROM beach_reservations
            WHERE ticket_number LIKE ?
        ''', (f'{date_prefix}%',))

        result = cursor.fetchone()
        next_seq = (result['max_seq'] or 0) + 1

        if next_seq > 99:
            raise ValueError(f"Máximo de reservas diarias alcanzado para {reservation_date}")

        ticket_number = f"{date_prefix}{next_seq:02d}"

        # Verificar unicidad
        cursor.execute('SELECT id FROM beach_reservations WHERE ticket_number = ?',
                      (ticket_number,))
        if not cursor.fetchone():
            return ticket_number

    raise ValueError("No se pudo generar número único después de varios intentos")
```

### 2.3 Numeración de Reservas Child (Multi-día)

```python
def generate_child_reservation_number(parent_number, child_index):
    """
    Genera número para reserva hija.

    Formato: YYMMDDRR-C donde C = índice (1,2,3...)
    Ejemplo: 25011601-1, 25011601-2
    """
    return f"{parent_number}-{child_index}"

def get_next_child_reservation_number(parent_reservation_id, parent_reservation_number, cursor=None):
    """
    Obtiene siguiente número child disponible.
    """
    cursor.execute('''
        SELECT COUNT(*) as child_count
        FROM beach_reservations
        WHERE parent_reservation_id = ?
    ''', (parent_reservation_id,))

    child_count = cursor.fetchone()['child_count']
    return generate_child_reservation_number(parent_reservation_number, child_count + 1)
```

---

## 3. CREACIÓN DE RESERVAS

### 3.1 Función Principal de Creación

```python
def create_beach_reservation(
    customer_id,
    reservation_date,
    num_people,
    furniture_ids,
    time_slot='all_day',
    payment_status='NO',
    charge_to_room=0,
    charge_reference='',
    price=0.0,
    preferences='',
    observations='',
    created_by=None,
    ticket_number=None,
    check_in_date=None,
    check_out_date=None,
    hamaca_included=1,
    price_catalog_id=None,
    final_price=0.0,
    paid=0,
    parent_reservation_id=None,
    minimum_consumption_policy_id=None,
    minimum_consumption_amount=0.0,
    cursor=None,
    conn=None
):
    """
    Crea una reserva completa con todas las validaciones.

    Returns:
        tuple: (reservation_id, ticket_number)

    Raises:
        ValueError: Si validaciones fallan
        sqlite3.IntegrityError: Si hay conflictos de datos
    """
```

### 3.2 Flujo de Creación

1. **Validaciones previas:**
   - Disponibilidad de mobiliario
   - Capacidad total >= num_people
   - Restricción de suites para balinesas
   - Detección de duplicados

2. **Transacción BEGIN IMMEDIATE:**
   - Generar ticket_number si no proporcionado
   - INSERT en beach_reservations
   - INSERT en beach_reservation_furniture por cada mueble
   - Sincronizar preferencias al perfil del cliente

3. **Post-creación:**
   - Agregar estado inicial "Confirmada"
   - Actualizar estadísticas del cliente
   - Log de auditoría

### 3.3 Creación de Reservas Multi-día Vinculadas

```python
def create_linked_multiday_reservations(
    customer_id,
    dates,                    # Lista de fechas ['2025-01-16', '2025-01-17', ...]
    num_people,
    furniture_ids=None,       # Mismo mobiliario todos los días
    furniture_by_date=None,   # Diferente mobiliario por día: {'2025-01-16': [1,2], ...}
    ...
):
    """
    Crea reservas vinculadas para múltiples días.

    Estrategia:
    - Primera fecha → reserva parent (ticket_number normal)
    - Fechas siguientes → reservas child (ticket_number con sufijo -1, -2, ...)
    - Todas vinculadas por parent_reservation_id
    """
```

---

## 4. SISTEMA DE ESTADOS

### 4.1 Estados Predefinidos y su Comportamiento

| Estado | Color | Libera Disponibilidad | Auto-acciones |
|--------|-------|----------------------|---------------|
| Confirmada | #28a745 | No | Estado inicial |
| Sentada | #17a2b8 | No | - |
| Cobrada | #ffc107 | No | - |
| Cancelada | #dc3545 | **Sí** | - |
| No-Show | #6c757d | **Sí** | Crea incidente automático |
| Liberada | #f8f9fa | **Sí** | - |

### 4.2 Prioridad de Display

```python
RESERVATION_STATE_DISPLAY_PRIORITY = {
    'Cobrada': 5,      # Máxima prioridad
    'Sentada': 4,
    'Confirmada': 3,
    'Cancelada': 2,
    'No-Show': 1,
    'Liberada': 0      # Mínima prioridad
}
```

### 4.3 Funciones de Gestión de Estados

```python
def add_reservation_state(reservation_id, state_type, changed_by, notes=''):
    """
    Agrega estado a reserva (acumulativo).

    Comportamiento:
    1. Añade al CSV de current_states
    2. Actualiza current_state al nuevo estado
    3. Registra en historial
    4. Si es No-Show: crea incidente automático
    5. Actualiza estadísticas del cliente
    """

def remove_reservation_state(reservation_id, state_type, changed_by, notes=''):
    """
    Remueve estado de reserva.

    Comportamiento:
    1. Elimina del CSV de current_states
    2. Recalcula current_state por prioridad
    3. Registra en historial
    4. Actualiza estadísticas del cliente
    """

def cancel_beach_reservation(reservation_id, cancelled_by, notes=''):
    """Atajo para agregar estado 'Cancelada'"""
    return add_reservation_state(reservation_id, 'Cancelada', cancelled_by, notes)
```

### 4.4 Cálculo de Color de Reserva

```python
def calculate_reservation_color(current_states_str):
    """
    Calcula color basado en estados actuales.

    Reglas:
    1. Si tiene Cobrada → color de Cobrada
    2. Si tiene Cancelada/No-Show → color respectivo
    3. Else → color del estado de mayor prioridad
    """
    states_list = [s.strip() for s in current_states_str.split(',') if s.strip()]

    # Prioridad de colores
    if 'Cobrada' in states_list:
        return get_state_color('Cobrada')
    if 'Cancelada' in states_list:
        return get_state_color('Cancelada')
    if 'No-Show' in states_list:
        return get_state_color('No-Show')

    # Usar estado de mayor prioridad
    if states_list:
        top_state = max(states_list, key=lambda s: RESERVATION_STATE_DISPLAY_PRIORITY.get(s, 0))
        return get_state_color(top_state)

    return '#CCCCCC'  # Default
```

### 4.5 Estados que Liberan Disponibilidad

```python
def get_active_releasing_states():
    """
    Obtiene lista de estados que liberan disponibilidad.

    Returns:
        list: Nombres de estados con is_availability_releasing=1
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM beach_reservation_states
            WHERE is_availability_releasing = 1 AND active = 1
        ''')
        return [row['name'] for row in cursor.fetchall()]
```

---

## 5. DISPONIBILIDAD DE MOBILIARIO

### 5.1 Verificación de Disponibilidad

```python
def check_furniture_availability(furniture_id, date, exclude_reservation_id=None, cursor=None):
    """
    Verifica si mobiliario está disponible para fecha específica.

    Lógica:
    1. Busca asignaciones existentes para (furniture_id, date)
    2. Excluye reservaciones con estados que liberan disponibilidad
    3. Excluye reservation_id específico (para updates)

    Returns:
        bool: True si disponible
    """
    releasing_states = get_active_releasing_states()

    query = '''
        SELECT brf.id
        FROM beach_reservation_furniture brf
        JOIN beach_reservations br ON brf.reservation_id = br.id
        WHERE brf.furniture_id = ?
          AND brf.assignment_date = ?
    '''
    params = [furniture_id, date]

    # Excluir estados que liberan
    if releasing_states:
        placeholders = ','.join('?' * len(releasing_states))
        query += f'''
          AND NOT EXISTS (
              SELECT 1 FROM beach_reservation_states brs
              WHERE brs.name IN ({placeholders})
                AND brs.is_availability_releasing = 1
                AND br.current_states LIKE '%' || brs.name || '%'
          )
        '''
        params.extend(releasing_states)

    if exclude_reservation_id:
        query += ' AND br.id != ?'
        params.append(exclude_reservation_id)

    cursor.execute(query, params)
    return cursor.fetchone() is None
```

### 5.2 Verificación Bulk de Disponibilidad

```python
def check_furniture_availability_bulk(furniture_ids, dates, exclude_reservation_id=None):
    """
    Verifica disponibilidad de múltiples muebles para múltiples fechas.

    Returns:
        dict: {
            'all_available': bool,
            'unavailable': [
                {'furniture_id': int, 'date': str, 'reason': str},
                ...
            ]
        }
    """
```

---

## 6. DETECCIÓN DE DUPLICADOS

### 6.1 Lógica de Detección

```python
def check_duplicate_reservation(customer_id, dates, furniture_ids=None,
                                exclude_reservation_id=None, cursor=None, conn=None):
    """
    Detecta reservas duplicadas para el mismo cliente.

    Reglas de duplicado:
    1. Mismo customer_id
    2. Mismas fechas (cualquier overlap)
    3. (Opcional) Mismo mobiliario
    4. NO incluye reservas con estados que liberan disponibilidad

    Returns:
        tuple: (is_duplicate: bool, duplicate_info: dict or None)
    """
    releasing_states = get_active_releasing_states()

    # Construir exclusión de estados
    exclude_clause = ''
    if releasing_states:
        for state in releasing_states:
            exclude_clause += f" AND br.current_states NOT LIKE '%{state}%'"

    # Buscar por fecha y cliente
    for date in dates:
        cursor.execute(f'''
            SELECT br.id, br.ticket_number, br.reservation_date, br.current_states
            FROM beach_reservations br
            WHERE br.customer_id = ?
              AND br.reservation_date = ?
              {exclude_clause}
              {f"AND br.id != {exclude_reservation_id}" if exclude_reservation_id else ""}
        ''', (customer_id, date))

        existing = cursor.fetchone()
        if existing:
            return True, {
                'reservation_id': existing['id'],
                'ticket_number': existing['ticket_number'],
                'date': existing['reservation_date'],
                'states': existing['current_states']
            }

    return False, None
```

---

## 7. SUGERENCIA INTELIGENTE DE MOBILIARIO

### 7.1 Algoritmo de Scoring

```python
def suggest_furniture_for_reservation(dates, num_people, preferences_csv='',
                                      customer_id=None, customer_type='interno', limit=10):
    """
    Sugiere mobiliario óptimo basado en preferencias y capacidad.

    Pesos del Scoring:
    - 40% Contiguidad (mobiliario junto, sin gaps)
    - 35% Match de preferencias
    - 25% Ajuste de capacidad

    Returns:
        dict: {
            'success': bool,
            'strategy': 'preference_based' | 'capacity_based' | 'no_furniture',
            'suggested_furniture': [
                {
                    'id': int,
                    'number': str,
                    'zone_name': str,
                    'capacity': int,
                    'score': float,
                    'preference_matches': ['pref1', 'pref2'],
                    'available_all_dates': bool,
                    'contiguity_score': float
                }
            ],
            'total_capacity': int,
            'message': str
        }
    """
```

### 7.2 Sistema de Contiguidad

```python
def build_furniture_occupancy_map(date, zone_id=None):
    """
    Construye mapa espacial de ocupación para fecha.

    Agrupa mobiliario por filas (±25px tolerancia vertical).

    Returns:
        dict: {
            'occupied': [furniture_ids ocupados],
            'available': [furniture_ids disponibles],
            'row_groups': {
                row_y: [furniture_ids en esa fila]
            }
        }
    """

def validate_cluster_contiguity(furniture_items, occupancy_map):
    """
    Valida si grupo de mobiliario es contiguo (sin gaps ocupados en medio).

    Detección de gaps:
    - Dentro de misma fila: estricto (no puede haber ocupado entre seleccionados)
    - Entre filas: más tolerante

    Returns:
        dict: {
            'is_contiguous': bool,
            'gap_count': int,
            'blocking_furniture': [ids de mobiliario que bloquea],
            'contiguity_score': float  # 1.0 = perfecto, -0.3 por cada gap
        }
    """
```

### 7.3 Mapeo de Preferencias

```python
PREFERENCE_TO_FURNITURE_FEATURES = {
    'pref_first_line': ['furn_first_line', 'furn_premium'],
    'pref_shade': ['furn_shaded', 'furn_umbrella'],
    'pref_sun': ['furn_full_sun'],
    'pref_quiet': ['furn_quiet_zone'],
    'pref_near_bar': ['furn_near_bar'],
    'pref_near_pool': ['furn_near_pool'],
    'pref_accessibility': ['furn_accessible'],
    # ...
}
```

### 7.4 Optimización Multi-día

```python
def optimize_furniture_for_multiday(dates, num_people, suggestions):
    """
    Optimiza asignación de mobiliario para reservas multi-día.

    Estrategias:
    - 'consistent': Mismo mobiliario todos los días (preferido)
    - 'per_day': Diferente mobiliario por día (fallback)

    Returns:
        dict: {
            'strategy': 'consistent' | 'per_day',
            'furniture_assignment': {date: [furniture_ids]} | [furniture_ids],
            'message': str
        }
    """
```

---

## 8. VALIDACIÓN DE PRECIOS (SEGURIDAD)

### 8.1 Validación Server-Side Anti-Fraude

```python
def validate_and_calculate_price(customer_type, price_catalog_id, hamaca_included,
                                  client_submitted_price=None):
    """
    SEGURIDAD: Valida precio contra catálogo para prevenir manipulación.

    Args:
        customer_type: 'interno' o 'externo'
        price_catalog_id: ID del catálogo
        hamaca_included: 1 = gratis, 0 = con cargo
        client_submitted_price: Precio enviado por cliente

    Returns:
        dict: {
            'validated_price': float,      # Precio correcto a usar
            'is_valid': bool,              # True si cliente envió precio correcto
            'expected_price': float,       # Lo que debería ser
            'client_price': float,         # Lo que envió cliente
            'discrepancy': float,          # Diferencia (si hay)
            'catalog_item_name': str       # Nombre del item
        }
    """
    result = {
        'validated_price': 0.0,
        'is_valid': True,
        'expected_price': 0.0,
        'client_price': client_submitted_price or 0.0,
        'discrepancy': 0.0,
        'catalog_item_name': None
    }

    # Si hamaca incluida, precio debe ser 0
    if hamaca_included == 1:
        result['expected_price'] = 0.0
        result['validated_price'] = 0.0
        if client_submitted_price and client_submitted_price != 0.0:
            result['is_valid'] = False
            result['discrepancy'] = client_submitted_price
        return result

    # Validar contra catálogo
    if price_catalog_id:
        catalog_item = get_price_catalog_item_by_id(price_catalog_id)
        if catalog_item:
            expected = catalog_item['price_interno'] if customer_type == 'interno' else catalog_item['price_externo']
            result['expected_price'] = expected
            result['validated_price'] = expected
            result['catalog_item_name'] = catalog_item['name']

            # Tolerancia de 0.01 para floating-point
            if client_submitted_price and abs(client_submitted_price - expected) > 0.01:
                result['is_valid'] = False
                result['discrepancy'] = client_submitted_price - expected

    return result
```

---

## 9. CONSUMO MÍNIMO Y CARGOS PMS

### 9.1 Aplicación de Política de Consumo

```python
def get_applicable_consumption_policy(reservation_date, furniture_type, zone_id, customer_type):
    """
    Encuentra política de consumo mínimo aplicable.

    Prioridad (mayor = más específico):
    1. Política específica de zona + tipo mobiliario + tipo cliente
    2. Política de zona + tipo mobiliario
    3. Política de tipo mobiliario + tipo cliente
    4. Política general

    Returns:
        dict or None: Política aplicable con minimum_amount
    """
```

### 9.2 Cargo a PMS

```python
def mark_consumption_charged_to_pms(reservation_id, charged_by):
    """Marca reserva individual como cargada al PMS"""

def bulk_mark_consumption_charged(reservation_ids, charged_by):
    """Marca múltiples reservas como cargadas al PMS"""

def get_reservations_pending_pms_charge(date_from=None, date_to=None):
    """Obtiene reservas con consumo pendiente de cargar"""

def count_reservations_pending_pms_charge(date_from=None, date_to=None):
    """Cuenta reservas y total pendiente"""
```

---

## 10. TAGS DE RESERVAS

### 10.1 CRUD de Tags

```python
def get_all_beach_tags(active_only=True):
    """Obtiene todos los tags (cacheado 5 min)"""

def create_beach_tag(name, color, description='', created_by='system'):
    """Crea nuevo tag"""

def update_beach_tag(tag_id, name, color, description=''):
    """Actualiza tag"""

def toggle_beach_tag_active(tag_id):
    """Activa/desactiva tag"""

def delete_beach_tag(tag_id):
    """Elimina tag (solo si no está en uso)"""
```

### 10.2 Asignación a Reservas

```python
def add_tag_to_reservation(reservation_id, tag_id, assigned_by):
    """Asigna tag a reserva (ignora si ya existe)"""

def remove_tag_from_reservation(reservation_id, tag_id):
    """Remueve tag de reserva"""
```

---

## 11. CONSULTAS Y FILTROS

### 11.1 Listado de Reservas

```python
def get_all_beach_reservations(
    date=None,                 # Fecha exacta
    date_from=None,            # Rango desde
    date_to=None,              # Rango hasta
    status_filter=None,        # Estado específico
    room_number=None,          # Filtrar por habitación
    guest_name=None,           # Búsqueda por nombre
    customer_type=None,        # 'interno' o 'externo'
    ticket_number=None         # Búsqueda por ticket
):
    """
    Lista reservas con filtros opcionales.

    Returns:
        list: Reservas con datos de cliente y mobiliario expandidos
    """
```

### 11.2 Reservas Vinculadas

```python
def get_linked_reservations(reservation_id):
    """
    Obtiene todas las reservas vinculadas (parent + children).

    Returns:
        list: Todas las reservas del grupo
    """

def is_parent_reservation(reservation_id):
    """Verifica si es reserva parent (tiene hijos)"""
```

### 11.3 Obtener Reserva por ID o Ticket

```python
def get_beach_reservation_by_id(reservation_id):
    """Obtiene reserva con todos los datos relacionados"""

def get_beach_reservation_by_ticket(ticket_number):
    """Obtiene reserva por número de ticket"""

def get_daily_states_for_reservation(reservation_id):
    """Obtiene estados diarios para reserva multi-día"""
```

---

## 12. API ENDPOINTS

### 12.1 Endpoints de Reservas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/beachclub/reservations` | Vista de lista con filtros |
| POST | `/beachclub/reservation/create` | Crear reserva (form) |
| POST | `/beachclub/reservation/create-quick` | Crear rápida desde mapa |
| POST | `/beachclub/reservation/create-full-modal` | Crear desde modal completo |
| POST | `/beachclub/api/reservation/create-linked-multiday` | Crear multi-día vinculadas |
| GET | `/beachclub/api/reservation/<id>` | Obtener detalles |
| POST | `/beachclub/api/reservation/update` | Actualizar reserva |
| POST | `/beachclub/api/reservation/update-multiday` | Actualizar multi-día |
| GET | `/beachclub/api/reservation/<id>/history` | Historial de estados |
| POST | `/beachclub/api/reservation/toggle-state` | Toggle estado |
| POST | `/beachclub/api/reservation/<id>/cancel` | Cancelar reserva |
| POST | `/beachclub/api/reservation/<id>/change-state` | Cambiar estado |
| POST | `/beachclub/api/reservation/check-duplicate` | Verificar duplicado |
| POST | `/beachclub/api/reservation/suggest-furniture` | Sugerir mobiliario |
| POST | `/beachclub/api/reservation/check-furniture-availability-bulk` | Verificar disponibilidad bulk |
| POST | `/beachclub/reservation/update-furniture` | Actualizar mobiliario asignado |

### 12.2 Endpoints de Consumo/PMS

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/beachclub/api/consumption/mark-charged/<id>` | Marcar cargado |

### 12.3 Request/Response de API Sugerir Mobiliario

**Request:**
```json
{
    "dates": ["2025-01-16", "2025-01-17"],
    "num_people": 4,
    "preferences": "pref_first_line,pref_shade",
    "customer_id": 123,
    "customer_type": "interno",
    "limit": 10
}
```

**Response:**
```json
{
    "success": true,
    "strategy": "preference_based",
    "suggested_furniture": [
        {
            "id": 45,
            "number": "62",
            "zone_name": "Primera Línea",
            "capacity": 2,
            "score": 0.85,
            "preference_matches": ["pref_first_line", "pref_shade"],
            "available_all_dates": true,
            "contiguity_score": 1.0
        }
    ],
    "total_capacity": 4,
    "message": "Sugerencias basadas en preferencias"
}
```

---

## 13. SINCRONIZACIÓN DE PREFERENCIAS

### 13.1 Bidireccional Cliente ↔ Reserva

```python
def sync_preferences_to_customer_profile(customer_id, preferences_csv, conn=None):
    """
    Sincroniza preferencias de reserva al perfil del cliente.

    Se ejecuta automáticamente al crear/modificar reserva.
    """

def sync_customer_preferences_to_reservations(customer_id, conn=None):
    """
    Sincroniza preferencias del cliente a todas sus reservas futuras.

    Se ejecuta cuando se actualiza el perfil del cliente.
    """

def sync_customer_data_to_reservations(customer_id):
    """
    Sincroniza datos del cliente (nombre, teléfono, etc.) a reservas existentes.
    """
```

---

## 14. AUDITORÍA Y LOGGING

### 14.1 Acciones a Loggear

```python
# En creación
log_action(username, 'Crear reserva Beach Club', f'Reserva: {ticket_number}')

# En cambio de estado
log_action(username, 'Cambio estado reserva', f'Reserva: {id}, Estado: {new_state}')

# En cancelación
log_action(username, 'Cancelar reserva', f'Reserva: {id}')

# En manipulación de precio detectada
log_action(username, 'SECURITY: Price manipulation attempt',
           f'Expected: {expected}, Submitted: {submitted}')

# En cargo a PMS
log_action(username, 'update', 'reservation_consumption', reservation_id,
          'Marked consumption as charged to PMS')
```

---

## 15. ÍNDICES DE RENDIMIENTO

```sql
-- Índices críticos para disponibilidad
CREATE INDEX idx_res_furniture_date_furniture
ON beach_reservation_furniture(assignment_date, furniture_id);

CREATE INDEX idx_reservations_date
ON beach_reservations(reservation_date);

CREATE INDEX idx_reservations_customer
ON beach_reservations(customer_id);

CREATE INDEX idx_reservations_ticket
ON beach_reservations(ticket_number);

CREATE INDEX idx_reservations_parent
ON beach_reservations(parent_reservation_id);

CREATE INDEX idx_reservations_states
ON beach_reservations(current_states);

-- Índice para consumo pendiente
CREATE INDEX idx_reservations_consumption
ON beach_reservations(consumption_charged_to_pms, minimum_consumption_amount);

-- Índice para historial
CREATE INDEX idx_status_history_reservation
ON reservation_status_history(reservation_id, changed_at);
```

---

## 16. TRANSACCIONES Y CONCURRENCIA

### 16.1 Patrón de Transacción Segura

```python
def create_reservation_atomic(...):
    """Creación atómica con protección contra race conditions"""

    # Conexión directa para control manual
    conn = sqlite3.connect(DATABASE_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')

    try:
        cursor = conn.cursor()
        cursor.execute('BEGIN IMMEDIATE')  # Lock exclusivo

        # 1. Verificar disponibilidad
        # 2. Generar ticket_number
        # 3. INSERT reserva
        # 4. INSERT furniture assignments
        # 5. Actualizar estadísticas

        conn.commit()
        return reservation_id, ticket_number

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 16.2 Context Manager para Transacciones

```python
@contextmanager
def get_db():
    """Context manager para conexiones de base de datos"""
    conn = sqlite3.connect(DATABASE_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## 17. VALIDACIONES DE NEGOCIO

### 17.1 Checklist de Validaciones

- [ ] Disponibilidad de mobiliario para todas las fechas
- [ ] Capacidad total >= número de personas
- [ ] Restricción de suites para balinesas suite_only
- [ ] Detección de reserva duplicada
- [ ] Validación de precio contra catálogo (anti-fraude)
- [ ] Fechas válidas (no pasadas excepto admin)
- [ ] Cliente existe y está activo
- [ ] Mobiliario existe y está activo
- [ ] Estados válidos según configuración
- [ ] Número de personas es entero positivo
- [ ] Ticket number único

### 17.2 Validación de Capacidad y Restricciones

```python
def _validate_furniture_and_capacity(furniture_ids, reservation_date, num_people, customer_id):
    """
    Valida disponibilidad, capacidad, y restricciones de suite.

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    # 1. Validar disponibilidad
    for furniture_id in furniture_ids:
        if not check_furniture_availability(furniture_id, reservation_date):
            return False, f'El mueble ID {furniture_id} no está disponible'

    # 2. Verificar capacidad
    furniture_list = [get_beach_furniture_by_id(fid) for fid in furniture_ids]
    total_capacity = sum(f['capacity'] for f in furniture_list if f)

    if num_people > total_capacity:
        return False, f'Capacidad excedida. Máximo: {total_capacity}'

    # 3. Verificar restricción de suite
    customer = get_beach_customer_by_id(customer_id)
    has_suite_only = any(f['furniture_type'] == 'balinesa' and f.get('suite_only')
                         for f in furniture_list if f)

    if has_suite_only and not customer.get('is_suite'):
        return False, 'Las balinesas están restringidas solo para clientes de Suite'

    return True, None
```

---

## 18. ERRORES COMUNES Y MANEJO

### 18.1 Excepciones Personalizadas

```python
class ReservationError(Exception):
    """Base exception for reservation errors"""
    pass

class CapacityExceededError(ReservationError):
    """Número de personas excede capacidad del mobiliario"""
    pass

class FurnitureUnavailableError(ReservationError):
    """Mobiliario no disponible para fecha"""
    pass

class DuplicateReservationError(ReservationError):
    """Ya existe reserva para este cliente en esta fecha"""
    pass

class PriceManipulationError(ReservationError):
    """Intento de manipulación de precio detectado"""
    pass

class SuiteRestrictionError(ReservationError):
    """Balinesa suite_only reservada por no-suite"""
    pass

class MaxDailyReservationsError(ReservationError):
    """Máximo de reservas diarias (99) alcanzado"""
    pass
```

### 18.2 Manejo en Endpoints

```python
@beachclub_bp.route('/api/reservation/create-linked-multiday', methods=['POST'])
def create_multiday():
    try:
        # ... lógica de creación ...
        return jsonify({'success': True, ...})

    except DuplicateReservationError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'duplicate'
        }), 409

    except FurnitureUnavailableError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'unavailable'
        }), 400

    except Exception as e:
        logger.error(f"Error creating reservation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500
```

---

## 19. ESTADÍSTICAS DEL CLIENTE

### 19.1 Actualización Automática

```python
def update_beach_customer_statistics(customer_id, conn=None):
    """
    Actualiza estadísticas del cliente basado en sus reservas.

    Se ejecuta automáticamente cuando:
    - Se crea una reserva
    - Se cambia estado de reserva
    - Se cancela reserva

    Estadísticas calculadas:
    - total_reservations: Total de reservas (excluyendo releasing states)
    - total_visits: Reservas con estado 'Sentada'
    - no_shows: Reservas con estado 'No-Show'
    - cancellations: Reservas con estado 'Cancelada'
    - last_visit_date: Fecha de última visita
    """
```

---

## 20. INCIDENTES AUTOMÁTICOS

### 20.1 Creación Automática por No-Show

```python
# Dentro de add_reservation_state():
if state_type == 'No-Show':
    cursor.execute('''
        INSERT INTO beach_customer_incidents
        (customer_id, description, incident_type, reservation_id, reported_by)
        VALUES (?, ?, 'no_show', ?, ?)
    ''', (customer_id, f'No-Show automático para reserva {reservation_id}',
          reservation_id, changed_by))

    # Actualizar flags del cliente
    cursor.execute('''
        UPDATE beach_customers
        SET has_incidents = 1,
            incident_count = (SELECT COUNT(*) FROM beach_customer_incidents
                             WHERE customer_id = ?)
        WHERE id = ?
    ''', (customer_id, customer_id))
```

---

## 21. MOBILIARIO TEMPORAL

### 21.1 Integración con Reservas

El mobiliario temporal (T1, T2, T3...) funciona igual que el permanente para reservas:

- **Visibilidad:** Solo visible en la fecha `valid_date` especificada
- **Disponibilidad:** Se verifica igual que mobiliario permanente
- **Reservabilidad:** Se puede reservar normalmente
- **Numeración:** T1, T2, T3... por zona por día

```python
def get_all_beach_furniture_with_availability(date, zone_id=None):
    """
    Obtiene mobiliario con disponibilidad para fecha.

    Incluye:
    - Mobiliario permanente (is_temporary = 0)
    - Mobiliario temporal válido para la fecha (is_temporary = 1 AND valid_date = date)
    """
```

---

## 22. CONFIGURACIÓN DEL SISTEMA

### 22.1 Parámetros de beachclub_config.json

```json
{
    "opening_time": "09:00",
    "closing_time": "19:00",
    "advance_booking_days": 30,
    "max_party_size": 8,
    "allow_overbooking": false,
    "cancellation_hours": 24,
    "default_time_slot": "all_day",
    "require_payment_on_booking": false
}
```

---

## 23. RESUMEN DE FUNCIONES PRINCIPALES

### Database Layer (database.py)

| Función | Descripción |
|---------|-------------|
| `create_beach_reservation()` | Crear reserva completa |
| `get_beach_reservation_by_id()` | Obtener por ID |
| `get_beach_reservation_by_ticket()` | Obtener por ticket |
| `get_all_beach_reservations()` | Listar con filtros |
| `update_beach_reservation()` | Actualizar reserva |
| `check_furniture_availability()` | Verificar disponibilidad |
| `check_duplicate_reservation()` | Detectar duplicados |
| `add_reservation_state()` | Agregar estado |
| `remove_reservation_state()` | Remover estado |
| `cancel_beach_reservation()` | Cancelar reserva |
| `suggest_furniture_for_reservation()` | Sugerir mobiliario |
| `validate_and_calculate_price()` | Validar precio |
| `generate_reservation_number()` | Generar ticket |
| `get_linked_reservations()` | Obtener vinculadas |
| `add_tag_to_reservation()` | Agregar tag |
| `remove_tag_from_reservation()` | Remover tag |
| `mark_consumption_charged_to_pms()` | Marcar cargo PMS |
| `build_furniture_occupancy_map()` | Mapa de ocupación |
| `validate_cluster_contiguity()` | Validar contiguidad |

---

Este documento cubre el 100% de la funcionalidad del sistema de reservas. Incluye todas las tablas, funciones, validaciones, endpoints, y lógica de negocio necesarias para una implementación completa y profesional.
