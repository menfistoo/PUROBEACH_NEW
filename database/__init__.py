"""
Database package for Beach Club Management System.

This package provides modular database operations:
- connection: Database connection management (get_db, close_db, init_db)
- migrations: Schema migration functions
- schema: Table creation and indexes
- seed: Initial seed data

For backwards compatibility, all functions are re-exported from this module.
"""

from database.connection import get_db, close_db, init_db
from database.migrations import (
    migrate_furniture_types_v2,
    migrate_reservations_v2,
    migrate_status_history_v2,
    migrate_hotel_guests_multi_guest,
    migrate_hotel_guests_booking_reference,
    migrate_customers_language_phone,
    migrate_add_sentada_state,
    migrate_customers_extended_stats,
    migrate_add_furniture_types_menu,
    migrate_reservation_states_configurable,
)
from database.schema import drop_tables, create_tables, create_indexes
from database.seed import seed_database

__all__ = [
    # Connection
    'get_db',
    'close_db',
    'init_db',
    # Migrations
    'migrate_furniture_types_v2',
    'migrate_reservations_v2',
    'migrate_status_history_v2',
    'migrate_hotel_guests_multi_guest',
    'migrate_hotel_guests_booking_reference',
    'migrate_customers_language_phone',
    'migrate_add_sentada_state',
    'migrate_customers_extended_stats',
    'migrate_add_furniture_types_menu',
    'migrate_reservation_states_configurable',
    # Schema
    'drop_tables',
    'create_tables',
    'create_indexes',
    # Seed
    'seed_database',
]
