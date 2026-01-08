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
