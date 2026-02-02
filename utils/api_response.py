"""
Standardized API response helpers.

Provides consistent JSON response format across all API endpoints:

    Success:  {"success": true, "data": {...}, "message": "..."}
    Error:    {"success": false, "error": "Spanish error message"}
    Warning:  {"success": true, "data": {...}, "warning": "..."}

Usage:
    from utils.api_response import api_success, api_error

    return api_success(data={'id': 1}, message='Creado exitosamente')
    return api_error('Datos requeridos', status=400)
"""

from flask import jsonify
from typing import Any


def api_success(
    data: dict | None = None,
    message: str | None = None,
    warning: str | None = None,
    status: int = 200,
    **extra_fields: Any
) -> tuple:
    """
    Build a standardized success JSON response.

    Args:
        data: Optional dict to include as 'data' key.
        message: Optional success message (Spanish).
        warning: Optional warning message (Spanish).
        status: HTTP status code (default 200).
        **extra_fields: Additional top-level fields to include in the response.
            Use sparingly for backward-compatible fields that frontend
            already reads at the top level (e.g., reservation_id, ticket_number).

    Returns:
        Tuple of (Response, status_code)
    """
    response = {'success': True}

    if data is not None:
        response['data'] = data

    if message:
        response['message'] = message

    if warning:
        response['warning'] = warning

    # Merge extra fields at top level for backward compatibility
    if extra_fields:
        response.update(extra_fields)

    return jsonify(response), status


def api_error(error: str, status: int = 400, **extra_fields: Any) -> tuple:
    """
    Build a standardized error JSON response.

    Args:
        error: Error message (Spanish).
        status: HTTP status code (default 400).
        **extra_fields: Additional top-level fields (e.g., conflicts, unavailable).

    Returns:
        Tuple of (Response, status_code)
    """
    response = {'success': False, 'error': error}

    # Merge extra fields for additional error context
    if extra_fields:
        response.update(extra_fields)

    return jsonify(response), status
