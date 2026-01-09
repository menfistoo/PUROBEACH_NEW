"""
Database migrations.
Safe, idempotent migrations for schema evolution.

This module re-exports all migrations from the migrations/ package
for backward compatibility. New code should import directly from
database.migrations submodules.

Structure:
    database/migrations/
    ├── __init__.py              - Orchestrator with run_all_migrations()
    ├── furniture_types.py       - Furniture type enhancements
    ├── reservations.py          - Reservation and status history
    ├── hotel_guests.py          - Multi-guest support
    ├── customers.py             - Customer statistics
    ├── states.py                - Reservation states
    ├── permissions.py           - Menu and permission additions
    ├── zones.py                 - Zone canvas properties
    └── furniture_manager_menu.py - Unified furniture manager menu
"""

# Re-export everything from the migrations package
from database.migrations import (
    # Main orchestrator
    run_all_migrations,
    MIGRATIONS,

    # Individual migrations (for backward compatibility)
    migrate_furniture_types_v2,
    migrate_reservations_v2,
    migrate_status_history_v2,
    migrate_reservations_original_room,
    migrate_hotel_guests_multi_guest,
    migrate_hotel_guests_booking_reference,
    migrate_customers_language_phone,
    migrate_customers_extended_stats,
    migrate_add_sentada_state,
    migrate_reservation_states_configurable,
    migrate_add_furniture_types_menu,
    migrate_add_map_edit_permission,
    migrate_add_map_editor_permission,
    migrate_zones_to_furniture_manager,
    migrate_zone_canvas_properties,
    migrate_furniture_manager_menu,
    migrate_furniture_blocks_table,
    migrate_furniture_daily_positions_table,
    migrate_add_blocking_permission,
    migrate_furniture_fill_color,
    migrate_add_temporary_furniture_permission,
)

__all__ = [
    'run_all_migrations',
    'MIGRATIONS',
    'migrate_furniture_types_v2',
    'migrate_reservations_v2',
    'migrate_status_history_v2',
    'migrate_reservations_original_room',
    'migrate_hotel_guests_multi_guest',
    'migrate_hotel_guests_booking_reference',
    'migrate_customers_language_phone',
    'migrate_customers_extended_stats',
    'migrate_add_sentada_state',
    'migrate_reservation_states_configurable',
    'migrate_add_furniture_types_menu',
    'migrate_add_map_edit_permission',
    'migrate_add_map_editor_permission',
    'migrate_zones_to_furniture_manager',
    'migrate_zone_canvas_properties',
    'migrate_furniture_manager_menu',
    'migrate_furniture_blocks_table',
    'migrate_furniture_daily_positions_table',
    'migrate_add_blocking_permission',
    'migrate_furniture_fill_color',
    'migrate_add_temporary_furniture_permission',
]
