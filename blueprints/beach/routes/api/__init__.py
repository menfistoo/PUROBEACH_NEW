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
from blueprints.beach.routes.api import map
from blueprints.beach.routes.api import pricing
from blueprints.beach.routes.api import states
from blueprints.beach.routes.api import waitlist

# Register all route functions on the blueprint
customers.register_routes(api_bp)
reservations.register_routes(api_bp)
map.register_routes(api_bp)
pricing.register_routes(api_bp)
states.register_routes(api_bp)
waitlist.register_routes(api_bp)
