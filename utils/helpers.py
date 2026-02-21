"""
Miscellaneous utility helper functions.
Provides common functionality used across the application.
"""

import random
import string
from datetime import datetime
from utils.datetime_helpers import get_now
import os


def format_date(date_str: str, format_str: str = '%d/%m/%Y') -> str:
    """
    Format date string to Spanish format.

    Args:
        date_str: Date string (YYYY-MM-DD)
        format_str: Output format (default: DD/MM/YYYY)

    Returns:
        Formatted date string or original if invalid
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(format_str)
    except (ValueError, TypeError):
        return date_str or ''


def format_datetime(datetime_str: str, format_str: str = '%d/%m/%Y %H:%M') -> str:
    """
    Format datetime string to Spanish format.

    Args:
        datetime_str: Datetime string
        format_str: Output format (default: DD/MM/YYYY HH:MM)

    Returns:
        Formatted datetime string or original if invalid
    """
    try:
        if not datetime_str:
            return ''

        # Handle different input formats
        for input_format in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
            try:
                dt_obj = datetime.strptime(datetime_str, input_format)
                return dt_obj.strftime(format_str)
            except ValueError:
                continue

        return datetime_str
    except (ValueError, TypeError):
        return datetime_str or ''


def generate_unique_code(prefix: str = '', length: int = 8) -> str:
    """
    Generate unique code for reservations, etc.

    Args:
        prefix: Optional prefix (e.g., 'RES')
        length: Length of random part

    Returns:
        Unique code string
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    if prefix:
        return f'{prefix}-{random_part}'

    return random_part


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file uploads.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return 'unnamed'

    # Get file extension
    name, ext = os.path.splitext(filename)

    # Remove non-alphanumeric characters (except dash and underscore)
    safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)

    # Limit length
    safe_name = safe_name[:100]

    # Add timestamp to ensure uniqueness
    timestamp = get_now().strftime('%Y%m%d_%H%M%S')

    return f'{safe_name}_{timestamp}{ext.lower()}'


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Filename

    Returns:
        Extension without dot (lowercase)
    """
    if not filename:
        return ''

    return os.path.splitext(filename)[1][1:].lower()


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if file extension is allowed.

    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions

    Returns:
        True if extension is allowed
    """
    return get_file_extension(filename) in allowed_extensions


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ''

    return text[:max_length - len(suffix)] + suffix


def get_weekday_name_es(date_str: str) -> str:
    """
    Get Spanish weekday name from date.

    Args:
        date_str: Date string (YYYY-MM-DD)

    Returns:
        Spanish weekday name
    """
    weekdays_es = {
        0: 'Lunes',
        1: 'Martes',
        2: 'Miércoles',
        3: 'Jueves',
        4: 'Viernes',
        5: 'Sábado',
        6: 'Domingo'
    }

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return weekdays_es.get(date_obj.weekday(), '')
    except ValueError:
        return ''
