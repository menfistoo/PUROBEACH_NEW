"""
Map reservation edit API routes.
Furniture reassignment, partial updates, customer changes, and date operations.

This module aggregates routes from:
- map_res_edit_furniture: Furniture reassignment and lock toggle
- map_res_edit_fields: Partial updates and customer changes
- map_res_edit_dates: Availability checking and date changes
"""

from flask import Blueprint

from . import map_res_edit_furniture
from . import map_res_edit_fields
from . import map_res_edit_dates


def register_routes(bp: Blueprint) -> None:
    """Register all map reservation edit routes on the blueprint."""
    map_res_edit_furniture.register_routes(bp)
    map_res_edit_fields.register_routes(bp)
    map_res_edit_dates.register_routes(bp)
