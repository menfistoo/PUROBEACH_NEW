"""
User-facing error message helpers (Spanish).

Models raise technical errors (often in English) for logging/debugging. The API
layer should show staff a clear Spanish reason instead of a generic message.
This translates known error patterns to friendly Spanish, with a safe fallback.
"""

import re


def friendly_reservation_error(raw: str) -> str:
    """
    Translate a raised reservation error into a clear Spanish message for staff.

    Args:
        raw: The original exception/error string.

    Returns:
        A user-friendly Spanish message.
    """
    msg = (raw or '').strip()
    low = msg.lower()

    if not msg:
        return 'No se pudo crear la reserva. Revisa los datos e inténtalo de nuevo.'

    # Daily ticket sequence exhausted
    if 'daily reservation limit' in low:
        return 'Se alcanzó el número máximo de reservas para este día.'

    # Ticket number generation race / retries exhausted
    if 'could not generate unique ticket' in low or 'unique ticket number' in low:
        return 'No se pudo generar el número de reserva. Inténtalo de nuevo.'

    # Duplicate reservation for the same customer/date
    if 'duplicate reservation' in low or 'already has a reservation' in low:
        m = re.search(r'ticket\s+([\w-]+)', msg, re.IGNORECASE)
        ref = f' (reserva {m.group(1)})' if m else ''
        return f'El cliente ya tiene una reserva para esta fecha{ref}.'

    # Furniture no longer available (English or Spanish variants)
    if 'not available' in low or 'no disponible' in low:
        m = re.search(r'(?:reservation|reserva)\s+([\w-]+)', msg, re.IGNORECASE)
        ref = f' (reserva {m.group(1)})' if m else ''
        return ('Alguna hamaca ya no está disponible para esas fechas; '
                f'puede que la hayan reservado mientras tanto{ref}. '
                'Actualiza el mapa e inténtalo de nuevo.')

    # Missing required data (validation)
    if ('at least one date' in low or 'customer_id is required' in low
            or 'furniture_ids' in low or 'is required' in low):
        return 'Faltan datos obligatorios para crear la reserva.'

    # Already a Spanish/user-friendly message → show it as-is.
    if re.search(r'[áéíóúñ¿¡]|\b(no|se|ya|reserva|cliente|mobiliario|hamaca|fecha)\b', low):
        return msg

    # Unknown/technical → generic safe message (the real one is logged separately).
    return 'No se pudo crear la reserva. Revisa los datos e inténtalo de nuevo.'
