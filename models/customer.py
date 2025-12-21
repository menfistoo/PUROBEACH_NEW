"""
Beach customer data access functions.
Handles customer CRUD operations, preferences, and tags.

This module re-exports all functions from the split modules for backward compatibility:
- customer_crud.py: Basic CRUD, preferences, and tags
- customer_queries.py: Filtering, statistics, and detailed queries
- customer_search.py: Unified search, hotel integration, and merging
"""

# =============================================================================
# RE-EXPORTS FOR BACKWARD COMPATIBILITY
# =============================================================================

# CRUD operations
from .customer_crud import (
    # Read
    get_all_customers,
    get_customer_by_id,
    search_customers,
    # Create/Update/Delete
    create_customer,
    update_customer,
    delete_customer,
    # Duplicates
    find_duplicates,
    # Preferences
    get_customer_preferences,
    set_customer_preferences,
    # Tags
    get_customer_tags,
    set_customer_tags,
)

# Query operations
from .customer_queries import (
    get_customers_filtered,
    get_customer_with_details,
    get_customer_stats,
    find_potential_duplicates_for_customer,
)

# Search and integration
from .customer_search import (
    search_customers_unified,
    create_customer_from_hotel_guest,
    merge_customers,
)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # CRUD
    'get_all_customers',
    'get_customer_by_id',
    'search_customers',
    'create_customer',
    'update_customer',
    'delete_customer',
    'find_duplicates',

    # Preferences & Tags
    'get_customer_preferences',
    'set_customer_preferences',
    'get_customer_tags',
    'set_customer_tags',

    # Queries
    'get_customers_filtered',
    'get_customer_with_details',
    'get_customer_stats',
    'find_potential_duplicates_for_customer',

    # Search & Integration
    'search_customers_unified',
    'create_customer_from_hotel_guest',
    'merge_customers',
]
