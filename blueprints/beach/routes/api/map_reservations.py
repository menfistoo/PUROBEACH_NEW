"""
Map reservation API routes.
Orchestrator module that registers all map reservation sub-modules.

Split into focused modules for maintainability:
- map_res_search.py: Customer search with furniture lookup
- map_res_create.py: Quick reservation creation
- map_res_edit.py: Furniture reassignment, partial updates, customer changes
- map_res_details.py: Reservation panel details, furniture moves
"""

from . import map_res_search
from . import map_res_create
from . import map_res_edit
from . import map_res_details


def register_routes(bp):
    """Register all map reservation routes on the blueprint."""
    map_res_search.register_routes(bp)
    map_res_create.register_routes(bp)
    map_res_edit.register_routes(bp)
    map_res_details.register_routes(bp)
