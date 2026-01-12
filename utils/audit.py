"""
Audit logging utility functions and decorators.
Provides automatic and manual audit logging for tracking user actions.
"""

import logging
from functools import wraps
from flask import request, g, current_app
from flask_login import current_user

# Configure logger for audit operations
logger = logging.getLogger(__name__)


def log_audit(
    action: str,
    entity_type: str,
    entity_id: int = None,
    before: dict = None,
    after: dict = None,
    user_id: int = None
) -> int:
    """
    Log an audit entry manually.

    This function is the primary entry point for manual audit logging.
    It captures the current user, IP address, and user agent automatically
    from the Flask request context.

    Args:
        action: Action type (CREATE, UPDATE, DELETE, VIEW, etc.)
        entity_type: Entity type (reservation, customer, pricing, etc.)
        entity_id: ID of the affected entity
        before: Dictionary with entity state before the change
        after: Dictionary with entity state after the change
        user_id: Override user ID (defaults to current_user.id)

    Returns:
        New audit log ID, or None if logging failed

    Example:
        # Log a manual action
        log_audit(
            action='UPDATE',
            entity_type='reservation',
            entity_id=123,
            before={'status': 'pending'},
            after={'status': 'confirmed'}
        )
    """
    try:
        from models.audit_log import create_audit_log

        # Get user ID from current_user if not provided
        if user_id is None:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                user_id = current_user.id
            else:
                user_id = None  # System action

        # Extract request context (IP, user agent)
        ip_address = None
        user_agent = None

        try:
            if request:
                # Get client IP, considering proxies
                ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                if ip_address and ',' in ip_address:
                    ip_address = ip_address.split(',')[0].strip()
                user_agent = request.headers.get('User-Agent', '')[:255]  # Truncate to DB limit
        except RuntimeError:
            # Outside request context (e.g., background jobs)
            pass

        # Build changes dictionary
        changes = None
        if before is not None or after is not None:
            changes = {
                'before': before,
                'after': after
            }

        # Create audit log entry
        audit_log_id = create_audit_log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return audit_log_id

    except Exception as e:
        # Audit logging should never fail the main operation
        logger.error(f"Failed to log audit entry: {e}", exc_info=True)
        return None


def audit_action(action_type: str, entity_type: str, entity_id_param: str = None):
    """
    Decorator to automatically log actions for route functions.

    This decorator captures before/after state for UPDATE operations
    and logs the action after the decorated function completes successfully.

    Usage:
        @bp.route('/reservations/<int:reservation_id>', methods=['POST'])
        @login_required
        @permission_required('beach.reservations.edit')
        @audit_action('UPDATE', 'reservation', entity_id_param='reservation_id')
        def update_reservation(reservation_id):
            ...

    Args:
        action_type: Action type (CREATE, UPDATE, DELETE)
        entity_type: Entity type (reservation, customer, etc.)
        entity_id_param: Name of the route parameter containing entity ID

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            entity_id = None
            before_state = None

            # Extract entity ID from kwargs or args
            if entity_id_param:
                entity_id = kwargs.get(entity_id_param)
                if entity_id is None and args:
                    # Try to get from positional args
                    try:
                        entity_id = args[0]
                    except (IndexError, TypeError):
                        pass

            # Capture before state for UPDATE/DELETE operations
            if action_type in ('UPDATE', 'DELETE') and entity_id:
                before_state = _get_entity_state(entity_type, entity_id)

            # Execute the original function
            result = func(*args, **kwargs)

            # Only log if the operation was successful
            # Check for error responses (tuple with status code >= 400)
            if _is_error_response(result):
                return result

            # Capture after state for CREATE/UPDATE operations
            after_state = None
            result_entity_id = entity_id

            if action_type == 'CREATE':
                # Try to extract created entity ID from result
                result_entity_id = _extract_entity_id_from_result(result)
                if result_entity_id:
                    after_state = _get_entity_state(entity_type, result_entity_id)
            elif action_type == 'UPDATE' and entity_id:
                after_state = _get_entity_state(entity_type, entity_id)

            # Log the audit entry
            log_audit(
                action=action_type,
                entity_type=entity_type,
                entity_id=result_entity_id,
                before=before_state,
                after=after_state
            )

            return result

        return wrapper
    return decorator


def _get_entity_state(entity_type: str, entity_id: int) -> dict:
    """
    Fetch current state of an entity for before/after comparison.

    Args:
        entity_type: Type of entity (reservation, customer, etc.)
        entity_id: Entity ID

    Returns:
        Dictionary with entity state, or None if not found
    """
    try:
        if entity_type == 'reservation':
            from models.reservation import get_reservation_with_details
            reservation = get_reservation_with_details(entity_id)
            if reservation:
                # Return relevant fields for audit comparison
                return {
                    'id': reservation.get('id'),
                    'customer_id': reservation.get('customer_id'),
                    'customer_name': reservation.get('customer_name'),
                    'reservation_date': reservation.get('reservation_date'),
                    'num_people': reservation.get('num_people'),
                    'current_state': reservation.get('current_state'),
                    'current_states': reservation.get('current_states'),
                    'notes': reservation.get('notes'),
                    'paid': reservation.get('paid'),
                    'final_price': reservation.get('final_price'),
                    'payment_method': reservation.get('payment_method')
                }

        elif entity_type == 'customer':
            from models.customer_crud import get_customer_by_id
            customer = get_customer_by_id(entity_id)
            if customer:
                # Return relevant fields, excluding sensitive data
                return {
                    'id': customer.get('id'),
                    'name': customer.get('name'),
                    'email': customer.get('email'),
                    'phone': customer.get('phone'),
                    'customer_type': customer.get('customer_type'),
                    'preferences': customer.get('preferences'),
                    'observations': customer.get('observations')
                }

        elif entity_type == 'hotel_guest':
            from models.hotel_guest import get_hotel_guest_by_id
            guest = get_hotel_guest_by_id(entity_id)
            if guest:
                return {
                    'id': guest.get('id'),
                    'name': guest.get('name'),
                    'room_number': guest.get('room_number'),
                    'check_in_date': guest.get('check_in_date'),
                    'check_out_date': guest.get('check_out_date')
                }

        # Add more entity types as needed

    except Exception as e:
        logger.warning(f"Failed to get entity state for {entity_type}/{entity_id}: {e}")

    return None


def _is_error_response(result) -> bool:
    """
    Check if the result indicates an error response.

    Args:
        result: Flask response or tuple

    Returns:
        True if result is an error response
    """
    try:
        # Check for tuple responses with status code
        if isinstance(result, tuple) and len(result) >= 2:
            status_code = result[1]
            if isinstance(status_code, int) and status_code >= 400:
                return True

        # Check for Response object with error status
        if hasattr(result, 'status_code') and result.status_code >= 400:
            return True

        # Check for JSON response with 'error' key
        if hasattr(result, 'get_json'):
            json_data = result.get_json()
            if json_data and isinstance(json_data, dict):
                if 'error' in json_data and not json_data.get('success', True):
                    return True

    except Exception:
        pass

    return False


def _extract_entity_id_from_result(result) -> int:
    """
    Try to extract entity ID from a CREATE operation result.

    Args:
        result: Flask response or tuple

    Returns:
        Entity ID if found, None otherwise
    """
    try:
        json_data = None

        # Get JSON data from result
        if hasattr(result, 'get_json'):
            json_data = result.get_json()
        elif isinstance(result, tuple) and len(result) >= 1:
            if hasattr(result[0], 'get_json'):
                json_data = result[0].get_json()

        if json_data and isinstance(json_data, dict):
            # Common patterns for entity ID in response
            for key in ('id', 'reservation_id', 'customer_id', 'entity_id', 'created_id'):
                if key in json_data:
                    return json_data[key]

    except Exception:
        pass

    return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def log_create(entity_type: str, entity_id: int, data: dict = None) -> int:
    """
    Log a CREATE action.

    Args:
        entity_type: Entity type
        entity_id: ID of the created entity
        data: Optional data about the created entity

    Returns:
        Audit log ID
    """
    return log_audit(
        action='CREATE',
        entity_type=entity_type,
        entity_id=entity_id,
        after=data
    )


def log_update(entity_type: str, entity_id: int, before: dict = None, after: dict = None) -> int:
    """
    Log an UPDATE action with before/after state.

    Args:
        entity_type: Entity type
        entity_id: ID of the updated entity
        before: State before the update
        after: State after the update

    Returns:
        Audit log ID
    """
    return log_audit(
        action='UPDATE',
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after
    )


def log_delete(entity_type: str, entity_id: int, data: dict = None) -> int:
    """
    Log a DELETE action.

    Args:
        entity_type: Entity type
        entity_id: ID of the deleted entity
        data: Optional data about the deleted entity (for audit trail)

    Returns:
        Audit log ID
    """
    return log_audit(
        action='DELETE',
        entity_type=entity_type,
        entity_id=entity_id,
        before=data
    )


def log_view(entity_type: str, entity_id: int) -> int:
    """
    Log a VIEW action (for sensitive data access tracking).

    Args:
        entity_type: Entity type
        entity_id: ID of the viewed entity

    Returns:
        Audit log ID
    """
    return log_audit(
        action='VIEW',
        entity_type=entity_type,
        entity_id=entity_id
    )


# Export public API
__all__ = [
    'audit_action',
    'log_audit',
    'log_create',
    'log_update',
    'log_delete',
    'log_view'
]
