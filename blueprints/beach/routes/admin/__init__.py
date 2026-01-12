"""
Beach admin routes package.
Contains administrative endpoints for audit logs and system management.
"""

from flask import Blueprint

# Create the admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Import and register routes from submodules
from blueprints.beach.routes.admin import audit_logs

# Register all route functions on the blueprint
audit_logs.register_routes(admin_bp)
