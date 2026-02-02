"""
Route decorators for authentication and authorization.
Provides permission-based access control for routes.
"""

from functools import wraps
from flask import flash, redirect, url_for, g, abort, request, jsonify
from flask_login import login_required, current_user


def _is_api_request() -> bool:
    """
    Detect if the current request is an API/AJAX request.

    Checks request path for '/api/' prefix and Accept header for JSON.
    API requests should receive JSON error responses instead of redirects.

    Returns:
        True if the request is an API request
    """
    # Check URL path for API routes
    if '/api/' in request.path:
        return True
    # Check if client explicitly requests JSON
    if request.is_json:
        return True
    if request.accept_mimetypes.best == 'application/json':
        return True
    # Check X-Requested-With header (common AJAX pattern)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    return False


def permission_required(permission_code: str):
    """
    Decorator to require specific permission for a route.

    For API requests, returns JSON 403 error instead of aborting with HTML.
    For regular requests, flashes an error message and aborts with 403.

    Usage:
        @app.route('/admin/users')
        @login_required
        @permission_required('admin.users.view')
        def admin_users():
            ...

    Args:
        permission_code: Permission code required (e.g., 'beach.map.view')

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Admin role bypasses all permission checks
            if hasattr(current_user, 'role_name') and current_user.role_name == 'admin':
                return func(*args, **kwargs)

            # Check if user has permission
            if not hasattr(g, 'user_permissions'):
                # Load permissions if not cached
                from utils.permissions import load_user_permissions
                g.user_permissions = load_user_permissions(current_user.id)

            if permission_code not in g.user_permissions:
                if _is_api_request():
                    return jsonify({
                        'success': False,
                        'error': 'No tiene permisos para realizar esta acción'
                    }), 403
                flash('No tiene permisos para acceder a esta página', 'error')
                abort(403)

            return func(*args, **kwargs)
        return wrapper
    return decorator


# Re-export login_required for convenience
__all__ = ['login_required', 'permission_required']
