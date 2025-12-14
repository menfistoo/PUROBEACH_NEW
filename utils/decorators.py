"""
Route decorators for authentication and authorization.
Provides permission-based access control for routes.
"""

from functools import wraps
from flask import flash, redirect, url_for, g, abort
from flask_login import login_required, current_user


def permission_required(permission_code: str):
    """
    Decorator to require specific permission for a route.

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
            # Check if user has permission
            if not hasattr(g, 'user_permissions'):
                # Load permissions if not cached
                from utils.permissions import load_user_permissions
                g.user_permissions = load_user_permissions(current_user.id)

            if permission_code not in g.user_permissions:
                flash('No tiene permisos para acceder a esta página', 'error')
                abort(403)

            return func(*args, **kwargs)
        return wrapper
    return decorator


# Re-export login_required for convenience
__all__ = ['login_required', 'permission_required']
