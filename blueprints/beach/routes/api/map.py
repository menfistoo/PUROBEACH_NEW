"""
Map API routes for interactive beach map.
Provides data endpoints for SVG rendering and furniture positioning.

This module aggregates all map-related API routes from submodules:
- map_data: Map data and availability endpoints
- map_furniture: Furniture positioning and details
- map_reservations: Quick reservations and customer search
- map_blocks: Furniture blocking (maintenance, VIP hold, etc.)
- map_daily: Daily position overrides
- map_temporary: Temporary furniture management
"""

from . import map_data
from . import map_furniture
from . import map_reservations
from . import map_blocks
from . import map_daily
from . import map_temporary


def register_routes(bp):
    """Register all map API routes on the blueprint."""
    map_data.register_routes(bp)
    map_furniture.register_routes(bp)
    map_reservations.register_routes(bp)
    map_blocks.register_routes(bp)
    map_daily.register_routes(bp)
    map_temporary.register_routes(bp)
