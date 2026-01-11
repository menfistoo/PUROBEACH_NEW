"""
Beach configuration routes package.
Split into smaller modules by entity for maintainability.
"""

from flask import Blueprint

# Create the config blueprint
config_bp = Blueprint('beach_config', __name__, url_prefix='/config')

# Import and register routes from submodules
from blueprints.beach.routes.config import zones
from blueprints.beach.routes.config import furniture_types
from blueprints.beach.routes.config import furniture
from blueprints.beach.routes.config import characteristics
from blueprints.beach.routes.config import tags
from blueprints.beach.routes.config import states
from blueprints.beach.routes.config import packages
from blueprints.beach.routes.config import minimum_consumption
from blueprints.beach.routes.config import pricing

# Register all route functions on the blueprint
zones.register_routes(config_bp)
furniture_types.register_routes(config_bp)
furniture.register_routes(config_bp)
characteristics.register_routes(config_bp)
tags.register_routes(config_bp)
states.register_routes(config_bp)
packages.register_routes(config_bp)
minimum_consumption.register_routes(config_bp)
pricing.register_routes(config_bp)
from blueprints.beach.routes.config import map_editor
from blueprints.beach.routes.config import furniture_manager
map_editor.register_routes(config_bp)
furniture_manager.register_routes(config_bp)
