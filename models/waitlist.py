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
    'afternoon': 'Tarde',
    'all_day': 'Todo el día',
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
            - customer_id (required)
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
    # Validate required fields
    if not data.get('customer_id'):
        raise ValueError("Debe seleccionar un cliente")

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
                customer_id, requested_date, num_people,
                preferred_zone_id, preferred_furniture_type_id,
                time_preference, reservation_type, package_id,
                notes, status, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'waiting', ?)
        ''', (
            data['customer_id'],
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
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.room_number,
                z.name as zone_name,
                ft.display_name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
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
                c.first_name || ' ' || COALESCE(c.last_name, '') as customer_name,
                c.customer_type,
                c.phone,
                c.email,
                c.room_number,
                z.name as zone_name,
                ft.display_name as furniture_type_name,
                p.package_name
            FROM beach_waitlist w
            JOIN beach_customers c ON w.customer_id = c.id
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
