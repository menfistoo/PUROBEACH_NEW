"""
Beach API routes package.
Split into smaller modules by entity for maintainability.
"""

from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint('api', __name__)

# Import and register routes from submodules
from blueprints.beach.routes.api import customers
from blueprints.beach.routes.api import reservations

# Register all route functions on the blueprint
customers.register_routes(api_bp)
reservations.register_routes(api_bp)
