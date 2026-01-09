"""
Database migrations package.
Organized by feature area for maintainability.

Each module contains related migrations that can be run independently.
The run_all_migrations() function executes all migrations in order.
"""

from .furniture_types import migrate_furniture_types_v2
from .reservations import (
    migrate_reservations_v2,
    migrate_status_history_v2,
    migrate_reservations_original_room
)
from .hotel_guests import (
    migrate_hotel_guests_multi_guest,
    migrate_hotel_guests_booking_reference
)
from .customers import (
    migrate_customers_language_phone,
    migrate_customers_extended_stats
)
from .states import (
    migrate_add_sentada_state,
    migrate_reservation_states_configurable
)
from .permissions import (
    migrate_add_furniture_types_menu,
    migrate_add_map_edit_permission,
    migrate_add_map_editor_permission,
    migrate_zones_to_furniture_manager
)
from .zones import migrate_zone_canvas_properties
from .furniture_manager_menu import migrate_furniture_manager_menu
from .furniture_extensions import (
    migrate_furniture_blocks_table,
    migrate_furniture_daily_positions_table,
    migrate_add_blocking_permission,
    migrate_furniture_fill_color,
    migrate_add_temporary_furniture_permission
)
from .pricing import (
    migrate_create_beach_packages,
    migrate_minimum_consumption_calculation_type
)
from .pricing_integration import migrate_add_pricing_fields
from .add_payment_method import migrate_add_payment_method
from .waitlist import (
    migrate_waitlist_table,
    migrate_waitlist_permissions,
    migrate_waitlist_fix_constraints
)


# Ordered list of all migrations
MIGRATIONS = [
    # Phase 1: Core schema enhancements
    ('furniture_types_v2', migrate_furniture_types_v2),
    ('reservations_v2', migrate_reservations_v2),
    ('status_history_v2', migrate_status_history_v2),

    # Phase 2: Hotel guest improvements
    ('hotel_guests_multi_guest', migrate_hotel_guests_multi_guest),
    ('hotel_guests_booking_reference', migrate_hotel_guests_booking_reference),

    # Phase 3: Customer enhancements
    ('customers_language_phone', migrate_customers_language_phone),
    ('customers_extended_stats', migrate_customers_extended_stats),

    # Phase 4: State management
    ('add_sentada_state', migrate_add_sentada_state),
    ('reservation_states_configurable', migrate_reservation_states_configurable),

    # Phase 5: Permissions
    ('add_furniture_types_menu', migrate_add_furniture_types_menu),
    ('add_map_edit_permission', migrate_add_map_edit_permission),
    ('add_map_editor_permission', migrate_add_map_editor_permission),

    # Phase 6: Zone properties
    ('zone_canvas_properties', migrate_zone_canvas_properties),

    # Phase 7: UI consolidation
    ('furniture_manager_menu', migrate_furniture_manager_menu),

    # Phase 7B: Map extensions
    ('furniture_blocks_table', migrate_furniture_blocks_table),
    ('furniture_daily_positions_table', migrate_furniture_daily_positions_table),
    ('add_blocking_permission', migrate_add_blocking_permission),

    # Phase 7C: Furniture customization
    ('furniture_fill_color', migrate_furniture_fill_color),
    ('add_temporary_furniture_permission', migrate_add_temporary_furniture_permission),

    # Phase 8: UI consolidation - Zones to furniture manager
    ('zones_to_furniture_manager', migrate_zones_to_furniture_manager),

    # Phase 9: Packages and pricing
    ('create_beach_packages', migrate_create_beach_packages),
    ('minimum_consumption_calculation_type', migrate_minimum_consumption_calculation_type),

    # Phase 10: Pricing integration (reservation columns)
    ('add_pricing_fields', migrate_add_pricing_fields),
    ('add_payment_method', migrate_add_payment_method),

    # Phase 11: Waitlist
    ('waitlist_table', migrate_waitlist_table),
    ('waitlist_permissions', migrate_waitlist_permissions),
    ('waitlist_fix_constraints', migrate_waitlist_fix_constraints),

    # Phase 12: Room change tracking
    ('reservations_original_room', migrate_reservations_original_room),
]


def run_all_migrations() -> dict:
    """
    Run all migrations in order.

    Each migration is idempotent - safe to run multiple times.

    Returns:
        dict: {
            'total': int,
            'applied': int,
            'skipped': int,
            'failed': int,
            'results': [(name, bool, str), ...]
        }
    """
    results = []
    applied = 0
    skipped = 0
    failed = 0

    print("=" * 60)
    print("Running all database migrations...")
    print("=" * 60)

    for name, migration_func in MIGRATIONS:
        try:
            result = migration_func()
            if result:
                applied += 1
                results.append((name, True, 'applied'))
            else:
                skipped += 1
                results.append((name, True, 'skipped'))
        except Exception as e:
            failed += 1
            results.append((name, False, str(e)))
            print(f"ERROR in migration {name}: {e}")

    print("=" * 60)
    print(f"Migrations complete: {applied} applied, {skipped} skipped, {failed} failed")
    print("=" * 60)

    return {
        'total': len(MIGRATIONS),
        'applied': applied,
        'skipped': skipped,
        'failed': failed,
        'results': results
    }


# Re-export all migrations for backward compatibility
__all__ = [
    # Main function
    'run_all_migrations',
    'MIGRATIONS',

    # Individual migrations
    'migrate_furniture_types_v2',
    'migrate_reservations_v2',
    'migrate_status_history_v2',
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
    'migrate_create_beach_packages',
    'migrate_minimum_consumption_calculation_type',
    'migrate_add_pricing_fields',
    'migrate_add_payment_method',
    'migrate_waitlist_table',
    'migrate_waitlist_permissions',
    'migrate_waitlist_fix_constraints',
    'migrate_reservations_original_room',
]
