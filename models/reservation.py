"""
Reservation data access functions.
Handles reservation CRUD operations, furniture assignments, state management,
and availability checking. Implements RESERVATIONS_SYSTEM_SPEC.md

This module re-exports all functions from the split modules for backward compatibility:
- reservation_state.py: State management and transitions
- reservation_crud.py: Create, read, update, delete operations
- reservation_queries.py: Listing, filtering, and availability
- reservation_availability.py: Bulk availability and duplicate detection (Phase 6B)

Phase 6A: Core CRUD + State Management
Phase 6B: Availability + Multi-day + Suggestions
"""

# =============================================================================
# RE-EXPORTS FOR BACKWARD COMPATIBILITY
# =============================================================================

# State management
from .reservation_state import (
    # Constants
    RESERVATION_STATE_DISPLAY_PRIORITY,
    # State queries
    get_reservation_states,
    get_active_releasing_states,
    # State transitions
    add_reservation_state,
    remove_reservation_state,
    change_reservation_state,
    cancel_beach_reservation,
    # Color calculation
    calculate_reservation_color,
    # Customer statistics
    update_customer_statistics,
    # History
    get_status_history,
)

# CRUD operations
from .reservation_crud import (
    # Ticket generation
    generate_reservation_number,
    generate_child_reservation_number,
    # Create
    create_beach_reservation,
    create_reservation_with_furniture,
    # Read
    get_beach_reservation_by_id,
    get_beach_reservation_by_ticket,
    get_reservation_with_details,
    get_reservation_by_id,
    # Update
    update_beach_reservation,
    update_reservation_with_furniture,
    # Delete
    delete_reservation,
    # Preferences
    sync_preferences_to_customer,
    get_customer_preference_codes,
)

# Query operations
from .reservation_queries import (
    # List queries
    get_all_beach_reservations,
    get_reservations_filtered,
    get_linked_reservations,
    # Statistics
    get_reservation_stats,
    # Availability
    get_available_furniture,
    check_furniture_availability,
    get_reservation_furniture,
    get_reservations_by_furniture,
    get_customer_reservation_history,
)

# Bulk availability operations (Phase 6B)
from .reservation_availability import (
    check_furniture_availability_bulk,
    check_duplicate_reservation,
    get_furniture_availability_map,
    get_conflicting_reservations,
)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Constants
    'RESERVATION_STATE_DISPLAY_PRIORITY',

    # State management
    'get_reservation_states',
    'get_active_releasing_states',
    'add_reservation_state',
    'remove_reservation_state',
    'change_reservation_state',
    'cancel_beach_reservation',
    'calculate_reservation_color',
    'update_customer_statistics',
    'get_status_history',

    # Ticket generation
    'generate_reservation_number',
    'generate_child_reservation_number',

    # CRUD
    'create_beach_reservation',
    'create_reservation_with_furniture',
    'get_beach_reservation_by_id',
    'get_beach_reservation_by_ticket',
    'get_reservation_with_details',
    'get_reservation_by_id',
    'update_beach_reservation',
    'update_reservation_with_furniture',
    'delete_reservation',

    # Preferences
    'sync_preferences_to_customer',
    'get_customer_preference_codes',

    # Queries
    'get_all_beach_reservations',
    'get_reservations_filtered',
    'get_linked_reservations',
    'get_reservation_stats',

    # Availability
    'get_available_furniture',
    'check_furniture_availability',
    'get_reservation_furniture',
    'get_reservations_by_furniture',
    'get_customer_reservation_history',

    # Bulk availability (Phase 6B)
    'check_furniture_availability_bulk',
    'check_duplicate_reservation',
    'get_furniture_availability_map',
    'get_conflicting_reservations',
]
