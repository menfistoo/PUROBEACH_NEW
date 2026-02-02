"""
Input validation helper functions.
Provides validation for common input types.
"""

import re
from datetime import datetime


def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number for consistent storage and deduplication.
    Strips all formatting characters and removes Spanish country code prefix.

    Examples:
        '+34 666-123-456' -> '666123456'
        '(666) 123 456'   -> '666123456'
        '00 34 666123456' -> '666123456'
        '0034666123456'   -> '666123456'
        '+34666123456'    -> '666123456'
        '666123456'       -> '666123456'
        None              -> None
        ''                -> ''

    Args:
        phone: Raw phone number string

    Returns:
        Normalized phone string with only digits (country code stripped),
        or None/empty if input is None/empty
    """
    if phone is None:
        return None
    if not phone:
        return ''

    # Strip all non-digit characters
    digits = re.sub(r'\D', '', phone)

    if not digits:
        return ''

    # Remove Spanish country code prefix: 0034 or 34
    if digits.startswith('0034'):
        digits = digits[4:]
    elif digits.startswith('34') and len(digits) > 9:
        digits = digits[2:]

    return digits


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid email format
    """
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate Spanish phone number format.
    Accepts: +34 XXX XXX XXX, 34XXXXXXXXX, XXX XXX XXX

    Args:
        phone: Phone number to validate

    Returns:
        True if valid phone format
    """
    if not phone:
        return False

    # Remove spaces and common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)

    # Spanish patterns
    patterns = [
        r'^\+34[0-9]{9}$',  # +34XXXXXXXXX
        r'^34[0-9]{9}$',    # 34XXXXXXXXX
        r'^[6-9][0-9]{8}$'  # XXXXXXXXX (starts with 6, 7, 8, or 9)
    ]

    return any(bool(re.match(pattern, cleaned)) for pattern in patterns)


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Validate that end date is not before start date.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        True if valid date range
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        return end >= start
    except ValueError:
        return False


def validate_room_number(room: str) -> bool:
    """
    Validate hotel room number format.
    Accepts: digits, alphanumeric

    Args:
        room: Room number to validate

    Returns:
        True if valid room format
    """
    if not room:
        return False

    # Allow alphanumeric room numbers (e.g., "101", "A12", "SU01")
    return bool(re.match(r'^[A-Z0-9]{1,10}$', room.upper()))


def validate_password(password: str, min_length: int = 6) -> tuple:
    """
    Validate password strength.

    Args:
        password: Password to validate
        min_length: Minimum password length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, 'La contraseña es requerida'

    if len(password) < min_length:
        return False, f'La contraseña debe tener al menos {min_length} caracteres'

    return True, ''


def validate_date_format(date_str: str) -> bool:
    """
    Validate date is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid format
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def sanitize_input(text: str, max_length: int = None) -> str:
    """
    Sanitize text input by trimming and limiting length.

    Args:
        text: Text to sanitize
        max_length: Maximum length (optional)

    Returns:
        Sanitized text
    """
    if not text:
        return ''

    # Strip whitespace
    sanitized = text.strip()

    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


# =============================================================================
# API PAYLOAD VALIDATION
# =============================================================================

def validate_positive_integer(value, field_name: str) -> tuple:
    """
    Validate that a value is a positive integer.

    Args:
        value: Value to validate
        field_name: Spanish field name for error messages

    Returns:
        tuple: (is_valid: bool, parsed_value: int or None, error: str or None)
    """
    if value is None:
        return False, None, f'El campo {field_name} es obligatorio'
    try:
        parsed = int(value)
        if parsed <= 0:
            return False, None, f'El campo {field_name} debe ser un entero positivo'
        return True, parsed, None
    except (ValueError, TypeError):
        return False, None, f'El campo {field_name} debe ser un entero valido'


def validate_integer_list(value, field_name: str, allow_empty: bool = False) -> tuple:
    """
    Validate that a value is a list of positive integers.

    Args:
        value: Value to validate (should be a list)
        field_name: Spanish field name for error messages
        allow_empty: Whether an empty list is valid

    Returns:
        tuple: (is_valid: bool, parsed_list: list or None, error: str or None)
    """
    if not isinstance(value, list):
        return False, None, f'El campo {field_name} debe ser una lista'
    if not allow_empty and len(value) == 0:
        return False, None, f'El campo {field_name} no puede estar vacio'
    try:
        parsed = [int(v) for v in value]
        if any(v <= 0 for v in parsed):
            return False, None, f'Todos los IDs en {field_name} deben ser enteros positivos'
        return True, parsed, None
    except (ValueError, TypeError):
        return False, None, f'Todos los valores en {field_name} deben ser enteros validos'


def validate_date_string(value, field_name: str) -> tuple:
    """
    Validate that a value is a valid YYYY-MM-DD date string.

    Args:
        value: Value to validate
        field_name: Spanish field name for error messages

    Returns:
        tuple: (is_valid: bool, value: str or None, error: str or None)
    """
    if not value or not isinstance(value, str):
        return False, None, f'El campo {field_name} es obligatorio'
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True, value, None
    except ValueError:
        return False, None, f'El campo {field_name} debe tener formato YYYY-MM-DD'


def validate_date_list(values, field_name: str) -> tuple:
    """
    Validate that a value is a non-empty list of valid YYYY-MM-DD date strings.

    Args:
        values: Value to validate (should be a list of strings)
        field_name: Spanish field name for error messages

    Returns:
        tuple: (is_valid: bool, parsed_list: list or None, error: str or None)
    """
    if not isinstance(values, list) or len(values) == 0:
        return False, None, f'El campo {field_name} no puede estar vacio'
    for v in values:
        if not isinstance(v, str):
            return False, None, f'Todas las fechas en {field_name} deben ser cadenas YYYY-MM-DD'
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            return False, None, f'Fecha invalida en {field_name}: {v}. Formato esperado: YYYY-MM-DD'
    return True, values, None


def validate_furniture_by_date(value, field_name: str) -> tuple:
    """
    Validate furniture_by_date dict: {date_string: [int_ids]}.

    Args:
        value: Value to validate (should be a dict)
        field_name: Spanish field name for error messages

    Returns:
        tuple: (is_valid: bool, value: dict or None, error: str or None)
    """
    if not isinstance(value, dict):
        return False, None, f'El campo {field_name} debe ser un objeto'
    if len(value) == 0:
        return False, None, f'El campo {field_name} no puede estar vacio'
    for date_key, furn_ids in value.items():
        # Validate date key
        try:
            datetime.strptime(date_key, '%Y-%m-%d')
        except ValueError:
            return False, None, f'Fecha invalida en {field_name}: {date_key}'
        # Validate furniture IDs list
        if not isinstance(furn_ids, list) or len(furn_ids) == 0:
            return False, None, f'Los IDs de mobiliario para {date_key} deben ser una lista no vacia'
        try:
            parsed_ids = [int(fid) for fid in furn_ids]
            if any(fid <= 0 for fid in parsed_ids):
                return False, None, f'IDs de mobiliario invalidos para {date_key}'
        except (ValueError, TypeError):
            return False, None, f'IDs de mobiliario invalidos para {date_key}'
    return True, value, None


def validate_start_end_dates(start_date: str, end_date: str) -> tuple:
    """
    Validate that start_date <= end_date (both in YYYY-MM-DD format).
    Assumes both dates have already been validated as valid date strings.

    Args:
        start_date: Start date string
        end_date: End date string

    Returns:
        tuple: (is_valid: bool, error: str or None)
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if start > end:
            return False, 'La fecha de inicio no puede ser posterior a la fecha de fin'
        return True, None
    except ValueError:
        return False, 'Formato de fecha invalido para el rango'
