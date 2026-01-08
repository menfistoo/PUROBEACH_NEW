"""
Waitlist model.
CRUD operations for the beach waiting list.
"""

from database import get_db
from typing import Optional, List
from datetime import date


# =============================================================================
# STATUS CONSTANTS
# =============================================================================

WAITLIST_STATUSES = {
    'waiting': {'name': 'En espera', 'color': '#FEF3C7'},
    'contacted': {'name': 'Contactado', 'color': '#DBEAFE'},
    'converted': {'name': 'Convertido', 'color': '#D1FAE5'},
    'declined': {'name': 'Rechazado', 'color': '#FEE2E2'},
    'no_answer': {'name': 'Sin respuesta', 'color': '#F3F4F6'},
    'expired': {'name': 'Expirado', 'color': '#E5E7EB'},
}

TIME_PREFERENCES = {
    'morning': 'Mañana',
    'manana': 'Mañana',
    'afternoon': 'Tarde',
    'tarde': 'Tarde',
    'mediodia': 'Mediodía',
    'all_day': 'Todo el día',
    'todo_el_dia': 'Todo el día',
}


# =============================================================================
# COUNT & QUERIES
# =============================================================================

def get_waitlist_count(requested_date: str) -> int:
    """
    Get count of waiting entries for a specific date.
    Used for badge display.

    Args:
        requested_date: Date string (YYYY-MM-DD)

    Returns:
        int: Number of entries with status='waiting'
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_waitlist
            WHERE requested_date = ?
              AND status = 'waiting'
        ''', (requested_date,))
        return cursor.fetchone()[0]


# =============================================================================
# CREATE
# =============================================================================

def create_waitlist_entry(data: dict, created_by: int) -> int:
    """
    Create a new waitlist entry.

    Args:
        data: Entry data with keys:
            - customer_id (required for interno, optional for externo)
            - external_name (required for externo without customer_id)
            - external_phone (required for externo without customer_id)
            - requested_date (required)
            - num_people (required)
            - preferred_zone_id (optional)
            - preferred_furniture_type_id (optional)
            - time_preference (optional)
            - reservation_type (optional, default 'incluido')
            - package_id (optional)
            - notes (optional)
        created_by: User ID creating the entry

    Returns:
        int: New entry ID

    Raises:
        ValueError: If validation fails
    """
    # Validate customer - either customer_id OR external_name+phone
    customer_id = data.get('customer_id')
    external_name = data.get('external_name', '').strip() if data.get('external_name') else None
    external_phone = data.get('external_phone', '').strip() if data.get('external_phone') else None

    if not customer_id and not (external_name and external_phone):
        raise ValueError("Debe seleccionar un cliente o ingresar nombre y telefono")

    if not data.get('requested_date'):
        raise ValueError("La fecha es requerida")

    # Validate date is not in past
    req_date = date.fromisoformat(data['requested_date'])
    if req_date < date.today():
        raise ValueError("La fecha debe ser hoy o futura")

    num_people = data.get('num_people', 1)
    if not isinstance(num_people, int) or num_people < 1 or num_people > 20:
        raise ValueError("Numero de personas debe ser entre 1 y 20")

    # Validate time_preference if provided
    time_pref = data.get('time_preference')
    if time_pref and time_pref not in TIME_PREFERENCES:
        raise ValueError("Preferencia de horario no valida")

    # Validate reservation_type
    res_type = data.get('reservation_type', 'incluido')
    if res_type not in ('incluido', 'paquete', 'consumo_minimo'):
        raise ValueError("Tipo de reserva no valido")

    # Validate package_id if type is 'paquete'
    if res_type == 'paquete' and not data.get('package_id'):
        raise ValueError("Debe seleccionar un paquete")

    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO beach_waitlist (
                customer_id, external_name, external_phone,
                requested_date, num_people,
                preferred_zone_id, preferred_furniture_type_id,
                time_preference, reservation_type, package_id,
                notes, status, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'waiting', ?)
        ''', (
            customer_id if customer_id else None,
            external_name,
            external_phone,
            data['requested_date'],
            num_people,
            data.get('preferred_zone_id'),
            data.get('preferred_furniture_type_id'),
            time_pref,
            res_type,
            data.get('package_id'),
            data.get('notes'),
            created_by
        ))
        conn.commit()
        return cursor.lastrowid


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_waitlist_by_date(requested_date: str, include_all: bool = False) -> List[dict]:
    """
    Get waitlist entries for a specific date.

    Args:
        requested_date: Date string (YYYY-MM-DD)
        include_all: If True, include all statuses. If False, only 'waiting'.

    Returns:
        list: List of entry dicts with customer details
    """
    status_filter = "" if include_all else "AND w.status = 'waiting'"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT
                w.id,
                w.customer_id,
                w.external_name,
                w.external_phone,
                w.requested_date,
                w.num_people,
                w.preferred_zone_id,
                w.preferred_furniture_type_id,
                w.time_preference,
                w.reservation_type,
                w.package_id,
                w.notes,
                w.status,
                w.converted_reservation_id,
                w.created_at,
                w.updated_at,
                COALESCE(c.first_name || ' ' || COALESCE(c.last_name, ''), w.external_name) as customer_name,
                COALESCE(c.customer_type, 'externo') as customer_type,
                COALESCE(c.phone, w.external_phone) as phone,
                c.room_number,
                z.name as zone_name,
                ft.display_name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            LEFT JOIN beach_customers c ON w.customer_id = c.id
            LEFT JOIN beach_zones z ON w.preferred_zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON w.preferred_furniture_type_id = ft.id
            LEFT JOIN beach_packages p ON w.package_id = p.id
            WHERE w.requested_date = ?
            {status_filter}
            ORDER BY w.created_at ASC
        ''', (requested_date,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_waitlist_entry(entry_id: int) -> Optional[dict]:
    """
    Get a single waitlist entry by ID.

    Args:
        entry_id: Entry ID

    Returns:
        dict or None: Entry with customer details
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                w.*,
                COALESCE(c.first_name || ' ' || COALESCE(c.last_name, ''), w.external_name) as customer_name,
                COALESCE(c.customer_type, 'externo') as customer_type,
                COALESCE(c.phone, w.external_phone) as phone,
                c.email,
                c.room_number,
                z.name as zone_name,
                ft.display_name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            LEFT JOIN beach_customers c ON w.customer_id = c.id
            LEFT JOIN beach_zones z ON w.preferred_zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON w.preferred_furniture_type_id = ft.id
            LEFT JOIN beach_packages p ON w.package_id = p.id
            WHERE w.id = ?
        ''', (entry_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# =============================================================================
# UPDATE
# =============================================================================

def update_waitlist_entry(entry_id: int, data: dict) -> bool:
    """
    Update a waitlist entry with new data.

    Args:
        entry_id: Entry ID
        data: Fields to update:
            - customer_id (optional)
            - external_name (optional)
            - external_phone (optional)
            - requested_date (optional)
            - num_people (optional)
            - preferred_zone_id (optional)
            - preferred_furniture_type_id (optional)
            - time_preference (optional)
            - reservation_type (optional)
            - package_id (optional)
            - notes (optional)

    Returns:
        bool: True if updated

    Raises:
        ValueError: If validation fails
    """
    # Get current entry
    entry = get_waitlist_entry(entry_id)
    if not entry:
        raise ValueError("Entrada no encontrada")

    # Cannot edit converted or expired entries
    if entry['status'] in ('converted', 'expired'):
        raise ValueError("No se puede modificar una entrada ya procesada")

    # Validate customer if changing
    customer_id = data.get('customer_id', entry.get('customer_id'))
    external_name = data.get('external_name', entry.get('external_name'))
    external_phone = data.get('external_phone', entry.get('external_phone'))

    if external_name:
        external_name = external_name.strip()
    if external_phone:
        external_phone = external_phone.strip()

    if not customer_id and not (external_name and external_phone):
        raise ValueError("Debe seleccionar un cliente o ingresar nombre y teléfono")

    # Validate date if changing
    requested_date = data.get('requested_date', entry['requested_date'])
    if requested_date:
        req_date = date.fromisoformat(requested_date)
        if req_date < date.today():
            raise ValueError("La fecha debe ser hoy o futura")

    # Validate num_people
    num_people = data.get('num_people', entry['num_people'])
    if not isinstance(num_people, int) or num_people < 1 or num_people > 20:
        raise ValueError("Número de personas debe ser entre 1 y 20")

    # Validate time_preference
    time_pref = data.get('time_preference', entry['time_preference'])
    if time_pref and time_pref not in TIME_PREFERENCES:
        raise ValueError("Preferencia de horario no válida")

    # Validate reservation_type
    res_type = data.get('reservation_type', entry['reservation_type'])
    if res_type not in ('incluido', 'paquete', 'consumo_minimo'):
        raise ValueError("Tipo de reserva no válido")

    # Validate package_id
    package_id = data.get('package_id', entry['package_id'])
    if res_type == 'paquete' and not package_id:
        raise ValueError("Debe seleccionar un paquete")

    with get_db() as conn:
        conn.execute('''
            UPDATE beach_waitlist
            SET customer_id = ?,
                external_name = ?,
                external_phone = ?,
                requested_date = ?,
                num_people = ?,
                preferred_zone_id = ?,
                preferred_furniture_type_id = ?,
                time_preference = ?,
                reservation_type = ?,
                package_id = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            customer_id if customer_id else None,
            external_name if not customer_id else None,
            external_phone if not customer_id else None,
            requested_date,
            num_people,
            data.get('preferred_zone_id', entry['preferred_zone_id']),
            data.get('preferred_furniture_type_id', entry['preferred_furniture_type_id']),
            time_pref,
            res_type,
            package_id if res_type == 'paquete' else None,
            data.get('notes', entry['notes']),
            entry_id
        ))
        conn.commit()
    return True


def update_waitlist_status(entry_id: int, status: str) -> bool:
    """
    Update the status of a waitlist entry.

    Args:
        entry_id: Entry ID
        status: New status

    Returns:
        bool: True if updated

    Raises:
        ValueError: If invalid status or transition
    """
    if status not in WAITLIST_STATUSES:
        raise ValueError(f"Estado no válido: {status}")

    # Get current entry
    entry = get_waitlist_entry(entry_id)
    if not entry:
        raise ValueError("Entrada no encontrada")

    # Check valid transitions
    current = entry['status']
    if current in ('converted', 'expired'):
        raise ValueError("No se puede modificar una entrada ya procesada")

    with get_db() as conn:
        conn.execute('''
            UPDATE beach_waitlist
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, entry_id))
        conn.commit()
    return True


# =============================================================================
# CONVERSION & EXPIRATION
# =============================================================================

def convert_to_reservation(entry_id: int, reservation_id: int) -> bool:
    """
    Mark entry as converted and link to reservation.

    Args:
        entry_id: Waitlist entry ID
        reservation_id: Created reservation ID

    Returns:
        bool: True if updated

    Raises:
        ValueError: If entry not found or already processed
    """
    entry = get_waitlist_entry(entry_id)
    if not entry:
        raise ValueError("Entrada no encontrada")

    if entry['status'] in ('converted', 'expired'):
        raise ValueError("No se puede convertir una entrada ya procesada")

    with get_db() as conn:
        conn.execute('''
            UPDATE beach_waitlist
            SET status = 'converted',
                converted_reservation_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (reservation_id, entry_id))
        conn.commit()
    return True


def expire_old_entries() -> int:
    """
    Expire all entries with past requested_date.
    Called on app startup and periodically.

    Returns:
        int: Number of entries expired
    """
    with get_db() as conn:
        cursor = conn.execute('''
            UPDATE beach_waitlist
            SET status = 'expired', updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('waiting', 'contacted', 'no_answer')
              AND requested_date < date('now')
        ''')
        conn.commit()
        return cursor.rowcount


# =============================================================================
# HISTORY & REPORTING
# =============================================================================

def get_waitlist_history(
    requested_date: str = None,
    customer_id: int = None
) -> List[dict]:
    """
    Get non-waiting entries for reporting/history.

    Args:
        requested_date: Filter by date (optional)
        customer_id: Filter by customer (optional)

    Returns:
        list: List of entry dicts
    """
    filters = ["w.status != 'waiting'"]
    params = []

    if requested_date:
        filters.append("w.requested_date = ?")
        params.append(requested_date)

    if customer_id:
        filters.append("w.customer_id = ?")
        params.append(customer_id)

    where_clause = " AND ".join(filters)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT
                w.*,
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.room_number
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
            WHERE {where_clause}
            ORDER BY w.updated_at DESC
        ''', params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
