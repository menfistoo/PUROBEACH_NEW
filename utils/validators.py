"""
Input validation helper functions.
Provides validation for common input types.
"""

import re
from datetime import datetime


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
