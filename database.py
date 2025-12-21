"""
Database connection, schema creation, and initialization.
Handles all database operations for the Beach Club Management System.
"""

import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from flask import g


def get_db():
    """
    Get thread-safe database connection with row factory.

    Returns:
        sqlite3.Connection: Database connection object
    """
    if 'db' not in g:
        db_path = os.environ.get('DATABASE_PATH', 'instance/beach_club.db')
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraints
        g.db.execute('PRAGMA foreign_keys = ON')
        # Enable WAL mode for better concurrency
        g.db.execute('PRAGMA journal_mode = WAL')
    return g.db


def close_db(e=None):
    """
    Close database connection.

    Args:
        e: Exception if any (from Flask teardown context)
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Initialize database: drop existing tables, create new schema, insert seed data.
    WARNING: This will delete all existing data!
    """
    db = get_db()

    # Drop existing tables (in reverse order of dependencies)
    drop_tables(db)

    # Create all tables
    create_tables(db)

    # Create indexes
    create_indexes(db)

    # Insert seed data
    seed_database(db)

    db.commit()
    print("Database initialized successfully!")


def migrate_furniture_types_v2():
    """
    Migration: Enhance beach_furniture_types table with additional columns
    for status colors, numbering, features, zones, and display order.

    Safe to run multiple times - checks if columns already exist.

    Note: This migration adds columns to the existing schema which already has:
    - map_shape, custom_svg, default_width, default_height, border_radius
    - fill_color, stroke_color, stroke_width
    - default_capacity, default_rotation, number_prefix, is_decorative

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied (check for one of the new columns)
    cursor.execute("PRAGMA table_info(beach_furniture_types)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'status_colors' in existing_columns:
        print("Migration already applied - furniture_types_v2 columns exist.")
        return False

    print("Applying furniture_types_v2 migration...")

    try:
        # Add only the columns that don't exist yet
        columns_to_add = [
            ("ALTER TABLE beach_furniture_types ADD COLUMN status_colors TEXT DEFAULT '{\"available\":\"#D2B48C\",\"reserved\":\"#4CAF50\",\"occupied\":\"#F44336\",\"maintenance\":\"#9E9E9E\"}'", 'status_colors'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN number_start INTEGER DEFAULT 1', 'number_start'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN default_features TEXT', 'default_features'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN allowed_zones TEXT', 'allowed_zones'),
            ('ALTER TABLE beach_furniture_types ADD COLUMN display_order INTEGER DEFAULT 0', 'display_order'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Update existing rows with display_order
        db.execute('''
            UPDATE beach_furniture_types
            SET display_order = id
            WHERE display_order IS NULL OR display_order = 0
        ''')

        db.commit()
        print("Migration furniture_types_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_reservations_v2():
    """
    Migration: Enhance beach_reservations table with SPEC columns for Phase 6.

    Adds columns for:
    - Ticket numbering (YYMMDDRR format)
    - Multi-state management (CSV-based)
    - Pricing and payment fields
    - PMS integration fields
    - Hotel stay dates

    Safe to run multiple times - checks if columns already exist.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("PRAGMA table_info(beach_reservations)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'ticket_number' in existing_columns:
        print("Migration already applied - reservations_v2 columns exist.")
        return False

    print("Applying reservations_v2 migration...")

    try:
        # Add new columns to beach_reservations
        columns_to_add = [
            # Ticket and date (UNIQUE handled by index)
            ('ALTER TABLE beach_reservations ADD COLUMN ticket_number TEXT', 'ticket_number'),
            ('ALTER TABLE beach_reservations ADD COLUMN reservation_date DATE', 'reservation_date'),
            ("ALTER TABLE beach_reservations ADD COLUMN time_slot TEXT DEFAULT 'all_day'", 'time_slot'),

            # Multi-state management
            ("ALTER TABLE beach_reservations ADD COLUMN current_states TEXT DEFAULT ''", 'current_states'),
            ("ALTER TABLE beach_reservations ADD COLUMN current_state TEXT DEFAULT 'Confirmada'", 'current_state'),

            # Pricing fields
            ("ALTER TABLE beach_reservations ADD COLUMN payment_status TEXT DEFAULT 'NO'", 'payment_status'),
            ('ALTER TABLE beach_reservations ADD COLUMN price REAL DEFAULT 0.0', 'price'),
            ('ALTER TABLE beach_reservations ADD COLUMN final_price REAL DEFAULT 0.0', 'final_price'),
            ('ALTER TABLE beach_reservations ADD COLUMN hamaca_included INTEGER DEFAULT 1', 'hamaca_included'),
            ('ALTER TABLE beach_reservations ADD COLUMN price_catalog_id INTEGER', 'price_catalog_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN paid INTEGER DEFAULT 0', 'paid'),

            # Charge to room
            ('ALTER TABLE beach_reservations ADD COLUMN charge_to_room INTEGER DEFAULT 0', 'charge_to_room'),
            ("ALTER TABLE beach_reservations ADD COLUMN charge_reference TEXT DEFAULT ''", 'charge_reference'),

            # Minimum consumption
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_amount REAL DEFAULT 0.0', 'minimum_consumption_amount'),
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_policy_id INTEGER', 'minimum_consumption_policy_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_to_pms INTEGER DEFAULT 0', 'consumption_charged_to_pms'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_at TIMESTAMP', 'consumption_charged_at'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_by TEXT', 'consumption_charged_by'),

            # Hotel stay dates
            ('ALTER TABLE beach_reservations ADD COLUMN check_in_date DATE', 'check_in_date'),
            ('ALTER TABLE beach_reservations ADD COLUMN check_out_date DATE', 'check_out_date'),

            # Reservation type
            ("ALTER TABLE beach_reservations ADD COLUMN reservation_type TEXT DEFAULT 'normal'", 'reservation_type'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Migrate existing reservations: copy start_date to reservation_date
        db.execute('''
            UPDATE beach_reservations
            SET reservation_date = start_date
            WHERE reservation_date IS NULL
        ''')
        print("  Migrated start_date to reservation_date for existing records")

        # Set current_state based on existing state_id
        db.execute('''
            UPDATE beach_reservations
            SET current_state = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = beach_reservations.state_id
            ),
            current_states = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = beach_reservations.state_id
            )
            WHERE state_id IS NOT NULL AND current_state = 'Confirmada'
        ''')
        print("  Migrated state_id to current_state/current_states")

        # Create new indexes for ticket_number and reservation_date
        try:
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_ticket ON beach_reservations(ticket_number)')
            print("  Created index: idx_reservations_ticket")
        except Exception:
            pass  # Index may already exist

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_reservations_date ON beach_reservations(reservation_date)')
            print("  Created index: idx_reservations_date")
        except Exception:
            pass

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_reservations_consumption ON beach_reservations(consumption_charged_to_pms, minimum_consumption_amount)')
            print("  Created index: idx_reservations_consumption")
        except Exception:
            pass

        db.commit()
        print("Migration reservations_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_status_history_v2():
    """
    Migration: Update reservation_status_history table for SPEC compatibility.

    Changes from state_id references to state names for simpler querying.

    Safe to run multiple times - checks if columns already exist.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("PRAGMA table_info(reservation_status_history)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'status_type' in existing_columns:
        print("Migration already applied - status_history_v2 columns exist.")
        return False

    print("Applying status_history_v2 migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE reservation_status_history ADD COLUMN status_type TEXT', 'status_type'),
            ('ALTER TABLE reservation_status_history ADD COLUMN action TEXT', 'action'),
            ('ALTER TABLE reservation_status_history ADD COLUMN notes TEXT', 'notes'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Migrate existing records: convert state_id to status_type
        db.execute('''
            UPDATE reservation_status_history
            SET status_type = (
                SELECT brs.name FROM beach_reservation_states brs
                WHERE brs.id = reservation_status_history.new_state_id
            ),
            action = 'added'
            WHERE status_type IS NULL AND new_state_id IS NOT NULL
        ''')
        print("  Migrated old records to new format")

        # Create index for history lookups
        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_status_history_reservation ON reservation_status_history(reservation_id, created_at)')
            print("  Created index: idx_status_history_reservation")
        except Exception:
            pass

        db.commit()
        print("Migration status_history_v2 applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_hotel_guests_multi_guest():
    """
    Migration: Support multiple guests per room.

    Changes:
    - Adds `is_main_guest` column (BOOLEAN DEFAULT 0)
    - Changes UNIQUE constraint from (room_number, arrival_date)
      to (room_number, arrival_date, guest_name)

    This allows storing all family members in the same room:
    - Room 301: John Smith (main guest)
    - Room 301: Johanne Smith (additional guest)

    Safe to run multiple times - checks if column already exists.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'is_main_guest' in existing_columns:
        print("Migration already applied - is_main_guest column exists.")
        return False

    print("Applying hotel_guests_multi_guest migration...")

    try:
        # SQLite doesn't support modifying constraints directly,
        # so we need to recreate the table

        # 1. Create new table with updated schema
        db.execute('''
            CREATE TABLE hotel_guests_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT NOT NULL,
                guest_name TEXT NOT NULL,
                arrival_date DATE,
                departure_date DATE,
                num_adults INTEGER DEFAULT 1,
                num_children INTEGER DEFAULT 0,
                vip_code TEXT,
                guest_type TEXT,
                nationality TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                source_file TEXT,
                is_main_guest INTEGER DEFAULT 0,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(room_number, arrival_date, guest_name)
            )
        ''')
        print("  Created new table with is_main_guest column")

        # 2. Copy existing data (all existing guests become main guests)
        db.execute('''
            INSERT INTO hotel_guests_new
            (id, room_number, guest_name, arrival_date, departure_date,
             num_adults, num_children, vip_code, guest_type, nationality,
             email, phone, notes, source_file, is_main_guest, imported_at, updated_at)
            SELECT
                id, room_number, guest_name, arrival_date, departure_date,
                num_adults, num_children, vip_code, guest_type, nationality,
                email, phone, notes, source_file, 1, imported_at, updated_at
            FROM hotel_guests
        ''')
        print("  Migrated existing data (marked as main guests)")

        # 3. Drop old table
        db.execute('DROP TABLE hotel_guests')
        print("  Dropped old table")

        # 4. Rename new table
        db.execute('ALTER TABLE hotel_guests_new RENAME TO hotel_guests')
        print("  Renamed new table to hotel_guests")

        # 5. Recreate indexes
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_room ON hotel_guests(room_number)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_dates ON hotel_guests(arrival_date, departure_date)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_active ON hotel_guests(departure_date)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_hotel_guests_main ON hotel_guests(room_number, is_main_guest)')
        print("  Recreated indexes")

        db.commit()
        print("Migration hotel_guests_multi_guest applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_hotel_guests_booking_reference():
    """
    Migration: Add booking_reference column to hotel_guests.

    This stores the hotel PMS reservation number (from "Reserva" column in Excel).

    Safe to run multiple times - checks if column already exists.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'booking_reference' in existing_columns:
        print("Migration already applied - booking_reference column exists.")
        return False

    print("Applying hotel_guests_booking_reference migration...")

    try:
        # Add the new column
        db.execute('ALTER TABLE hotel_guests ADD COLUMN booking_reference TEXT')
        print("  Added booking_reference column")

        db.commit()
        print("Migration hotel_guests_booking_reference applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_customers_language_phone():
    """
    Migration: Add language and country_code columns to beach_customers.

    These fields support the enhanced customer creation flow with:
    - Language selector (ES, EN, DE, FR, etc.)
    - Phone with country code (+34, +49, etc.)

    Safe to run multiple times - checks if columns already exist.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("PRAGMA table_info(beach_customers)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'language' in existing_columns:
        print("Migration already applied - language column exists.")
        return False

    print("Applying customers_language_phone migration...")

    try:
        columns_to_add = [
            ("ALTER TABLE beach_customers ADD COLUMN language TEXT", 'language'),
            ("ALTER TABLE beach_customers ADD COLUMN country_code TEXT DEFAULT '+34'", 'country_code'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Create index for language
        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_customers_language ON beach_customers(language)')
            print("  Created index: idx_customers_language")
        except Exception:
            pass

        db.commit()
        print("Migration customers_language_phone applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_add_furniture_types_menu():
    """
    Migration: Add 'Tipos de Mobiliario' menu permission.

    Safe to run multiple times - checks if permission already exists.
    """
    db = get_db()
    cursor = db.cursor()

    # Check if permission already exists
    cursor.execute("SELECT id FROM permissions WHERE code = 'beach.furniture_types.view'")
    if cursor.fetchone():
        print("Menu permission 'beach.furniture_types.view' already exists.")
        return False

    print("Adding furniture types menu permission...")

    try:
        # Get parent menu ID for Configuración
        cursor.execute("SELECT id FROM permissions WHERE code = 'menu.config'")
        parent_row = cursor.fetchone()
        if not parent_row:
            print("ERROR: Parent menu 'menu.config' not found!")
            return False
        menu_config_id = parent_row[0]

        # Insert menu permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('beach.furniture_types.view', 'Tipos de Mobiliario', 'config', 1, 22, 'fa-shapes', '/beach/config/furniture-types', menu_config_id))

        new_perm_id = cursor.lastrowid

        # Insert manage permission
        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES (?, ?, ?, 0)
        ''', ('beach.furniture_types.manage', 'Gestionar Tipos Mobiliario', 'config'))

        manage_perm_id = cursor.lastrowid

        # Assign to admin role
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_role_id = admin_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, new_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, manage_perm_id))

        # Assign to manager role
        cursor.execute("SELECT id FROM roles WHERE name = 'manager'")
        manager_row = cursor.fetchone()
        if manager_row:
            manager_role_id = manager_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, new_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (manager_role_id, manage_perm_id))

        db.commit()
        print("Menu permission added successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def drop_tables(db):
    """Drop all existing tables."""
    # Disable foreign key constraints before dropping
    db.execute('PRAGMA foreign_keys = OFF')

    tables = [
        'reservation_status_history',
        'audit_log',
        'beach_config',
        'beach_minimum_consumption_policies',
        'beach_price_catalog',
        'beach_reservation_tags',
        'beach_reservation_daily_states',
        'beach_reservation_furniture',
        'beach_reservations',
        'beach_reservation_states',
        'beach_customer_preferences',
        'beach_preferences',
        'beach_customer_tags',
        'beach_tags',
        'beach_customers',
        'hotel_guests',
        'beach_furniture',
        'beach_furniture_types',
        'beach_zones',
        'role_permissions',
        'permissions',
        'roles',
        'users'
    ]

    for table in tables:
        db.execute(f'DROP TABLE IF EXISTS {table}')

    # Re-enable foreign key constraints
    db.execute('PRAGMA foreign_keys = ON')


def create_tables(db):
    """Create all database tables."""

    # 1. Users & Auth Tables
    db.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role_id INTEGER REFERENCES roles(id),
            active INTEGER DEFAULT 1,
            theme_preference TEXT DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            is_system INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            module TEXT NOT NULL,
            category TEXT,
            parent_permission_id INTEGER REFERENCES permissions(id),
            is_menu_item INTEGER DEFAULT 0,
            menu_order INTEGER DEFAULT 0,
            menu_icon TEXT,
            menu_url TEXT,
            active INTEGER DEFAULT 1
        )
    ''')

    db.execute('''
        CREATE TABLE role_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(role_id, permission_id)
        )
    ''')

    # 2. Beach Infrastructure Tables
    db.execute('''
        CREATE TABLE beach_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            parent_zone_id INTEGER REFERENCES beach_zones(id),
            color TEXT DEFAULT '#F5E6D3',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_furniture_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_code TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            icon TEXT DEFAULT 'fa-umbrella-beach',
            default_color TEXT DEFAULT '#A0522D',
            min_capacity INTEGER DEFAULT 1,
            max_capacity INTEGER DEFAULT 4,
            is_suite_only INTEGER DEFAULT 0,
            notes TEXT,
            active INTEGER DEFAULT 1,

            -- SVG Visual representation
            map_shape TEXT DEFAULT 'rounded_rect',
            custom_svg TEXT,
            default_width REAL DEFAULT 60,
            default_height REAL DEFAULT 40,
            border_radius INTEGER DEFAULT 5,
            fill_color TEXT DEFAULT '#A0522D',
            stroke_color TEXT DEFAULT '#654321',
            stroke_width INTEGER DEFAULT 2,
            status_colors TEXT DEFAULT '{"available":"#D2B48C","reserved":"#4CAF50","occupied":"#F44336","maintenance":"#9E9E9E"}',

            -- Capacity & Behavior
            default_capacity INTEGER DEFAULT 2,
            default_rotation INTEGER DEFAULT 0,
            is_decorative INTEGER DEFAULT 0,

            -- Numbering
            number_prefix TEXT,
            number_start INTEGER DEFAULT 1,

            -- Configuration
            default_features TEXT,
            allowed_zones TEXT,
            display_order INTEGER DEFAULT 0
        )
    ''')

    db.execute('''
        CREATE TABLE beach_furniture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            zone_id INTEGER NOT NULL REFERENCES beach_zones(id),
            furniture_type TEXT NOT NULL,
            capacity INTEGER DEFAULT 2,
            position_x REAL DEFAULT 0,
            position_y REAL DEFAULT 0,
            rotation INTEGER DEFAULT 0,
            width REAL DEFAULT 60,
            height REAL DEFAULT 40,
            is_temporary INTEGER DEFAULT 0,
            valid_date DATE,
            features TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Hotel Guests Table (supports multiple guests per room)
    db.execute('''
        CREATE TABLE hotel_guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            guest_name TEXT NOT NULL,
            arrival_date DATE,
            departure_date DATE,
            num_adults INTEGER DEFAULT 1,
            num_children INTEGER DEFAULT 0,
            vip_code TEXT,
            guest_type TEXT,
            nationality TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT,
            source_file TEXT,
            is_main_guest INTEGER DEFAULT 0,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_number, arrival_date, guest_name)
        )
    ''')

    # 4. Customer Tables
    db.execute('''
        CREATE TABLE beach_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_type TEXT NOT NULL CHECK(customer_type IN ('interno', 'externo')),
            first_name TEXT NOT NULL,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            country_code TEXT DEFAULT '+34',
            room_number TEXT,
            language TEXT,
            notes TEXT,
            vip_status INTEGER DEFAULT 0,
            total_visits INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0,
            last_visit DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#6C757D',
            description TEXT,
            active INTEGER DEFAULT 1
        )
    ''')

    db.execute('''
        CREATE TABLE beach_customer_tags (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES beach_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, tag_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            maps_to_feature TEXT,
            active INTEGER DEFAULT 1
        )
    ''')

    db.execute('''
        CREATE TABLE beach_customer_preferences (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            preference_id INTEGER REFERENCES beach_preferences(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, preference_id)
        )
    ''')

    # 5. Reservation Tables
    db.execute('''
        CREATE TABLE beach_reservation_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#6C757D',
            icon TEXT,
            is_availability_releasing INTEGER DEFAULT 0,
            display_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES beach_customers(id),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            num_people INTEGER NOT NULL DEFAULT 1,
            state_id INTEGER REFERENCES beach_reservation_states(id),
            preferences TEXT,
            notes TEXT,
            internal_notes TEXT,
            source TEXT DEFAULT 'direct',
            parent_reservation_id INTEGER REFERENCES beach_reservations(id),
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservation_furniture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL REFERENCES beach_reservations(id) ON DELETE CASCADE,
            furniture_id INTEGER NOT NULL REFERENCES beach_furniture(id),
            assignment_date DATE NOT NULL,
            UNIQUE(furniture_id, assignment_date, reservation_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservation_daily_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL REFERENCES beach_reservations(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            state_id INTEGER REFERENCES beach_reservation_states(id),
            notes TEXT,
            UNIQUE(reservation_id, date)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservation_tags (
            reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES beach_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (reservation_id, tag_id)
        )
    ''')

    # 6. Pricing Tables
    db.execute('''
        CREATE TABLE beach_price_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            furniture_type TEXT,
            customer_type TEXT,
            zone_id INTEGER REFERENCES beach_zones(id),
            base_price REAL NOT NULL,
            weekend_price REAL,
            holiday_price REAL,
            valid_from DATE,
            valid_until DATE,
            active INTEGER DEFAULT 1
        )
    ''')

    db.execute('''
        CREATE TABLE beach_minimum_consumption_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_name TEXT NOT NULL,
            minimum_amount REAL NOT NULL,
            furniture_type TEXT,
            customer_type TEXT,
            zone_id INTEGER REFERENCES beach_zones(id),
            priority_order INTEGER DEFAULT 0,
            policy_description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. Configuration and Audit Tables
    db.execute('''
        CREATE TABLE beach_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE reservation_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER REFERENCES beach_reservations(id),
            old_state_id INTEGER,
            new_state_id INTEGER,
            changed_by TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')


def create_indexes(db):
    """Create performance indexes."""

    # Furniture indexes
    db.execute('CREATE INDEX idx_furniture_zone ON beach_furniture(zone_id)')
    db.execute('CREATE INDEX idx_furniture_active ON beach_furniture(active)')
    db.execute('CREATE INDEX idx_furniture_temp_date ON beach_furniture(is_temporary, valid_date)')

    # Customer indexes
    db.execute('CREATE INDEX idx_customers_type ON beach_customers(customer_type)')
    db.execute('CREATE INDEX idx_customers_phone ON beach_customers(phone)')
    db.execute('CREATE INDEX idx_customers_room ON beach_customers(room_number)')

    # Reservation indexes
    db.execute('CREATE INDEX idx_reservations_dates ON beach_reservations(start_date, end_date)')
    db.execute('CREATE INDEX idx_reservations_customer ON beach_reservations(customer_id)')
    db.execute('CREATE INDEX idx_reservations_state ON beach_reservations(state_id)')

    # Reservation furniture indexes
    db.execute('CREATE INDEX idx_res_furniture_date ON beach_reservation_furniture(assignment_date, furniture_id)')
    db.execute('CREATE INDEX idx_res_furniture_lookup ON beach_reservation_furniture(reservation_id, assignment_date)')

    # Permission indexes
    db.execute('CREATE INDEX idx_permissions_code ON permissions(code)')
    db.execute('CREATE INDEX idx_permissions_menu ON permissions(is_menu_item) WHERE is_menu_item = 1')
    db.execute('CREATE INDEX idx_role_perms ON role_permissions(role_id, permission_id)')

    # Hotel guest indexes
    db.execute('CREATE INDEX idx_hotel_guests_room ON hotel_guests(room_number)')
    db.execute('CREATE INDEX idx_hotel_guests_dates ON hotel_guests(arrival_date, departure_date)')
    db.execute('CREATE INDEX idx_hotel_guests_active ON hotel_guests(departure_date)')
    db.execute('CREATE INDEX idx_hotel_guests_main ON hotel_guests(room_number, is_main_guest)')


def seed_database(db):
    """Insert initial seed data."""

    # 1. Create Roles
    roles_data = [
        ('admin', 'Administrador', 'Acceso completo al sistema', 1),
        ('manager', 'Manager Beach', 'Gestión completa del beach club', 1),
        ('staff', 'Staff Beach', 'Operaciones diarias del beach club', 1),
        ('readonly', 'Solo Lectura', 'Consultas sin modificar datos', 1)
    ]

    for name, display_name, description, is_system in roles_data:
        db.execute('''
            INSERT INTO roles (name, display_name, description, is_system)
            VALUES (?, ?, ?, ?)
        ''', (name, display_name, description, is_system))

    # 2. Create Parent Menu Permissions (no URL, is_menu_item=1)
    parent_menus = [
        ('menu.admin', 'Administración', 'admin', 1, 10, 'fa-shield-halved'),
        ('menu.config', 'Configuración', 'config', 1, 20, 'fa-sliders'),
        ('menu.operations', 'Operaciones', 'operations', 1, 30, 'fa-umbrella-beach'),
        ('menu.reports', 'Informes', 'reports', 1, 40, 'fa-chart-line'),
    ]

    for code, name, module, is_menu, menu_order, menu_icon in parent_menus:
        db.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, module, is_menu, menu_order, menu_icon))

    # Get parent IDs for child assignments
    menu_admin_id = db.execute('SELECT id FROM permissions WHERE code = "menu.admin"').fetchone()[0]
    menu_config_id = db.execute('SELECT id FROM permissions WHERE code = "menu.config"').fetchone()[0]
    menu_operations_id = db.execute('SELECT id FROM permissions WHERE code = "menu.operations"').fetchone()[0]
    menu_reports_id = db.execute('SELECT id FROM permissions WHERE code = "menu.reports"').fetchone()[0]

    # 3. Create Child Menu Permissions (with parent_permission_id)
    child_permissions = [
        # Administración children
        ('admin.users.view', 'Usuarios', 'admin', 1, 11, 'fa-users-gear', '/admin/users', menu_admin_id),
        ('admin.roles.view', 'Roles', 'admin', 1, 12, 'fa-user-shield', '/admin/roles', menu_admin_id),
        ('admin.audit.view', 'Auditoría', 'admin', 1, 13, 'fa-clipboard-list', '/admin/audit', menu_admin_id),
        ('admin.hotel_guests.view', 'Huéspedes Hotel', 'admin', 1, 14, 'fa-hotel', '/admin/hotel-guests', menu_admin_id),

        # Configuración children
        ('beach.zones.view', 'Zonas', 'config', 1, 21, 'fa-layer-group', '/beach/config/zones', menu_config_id),
        ('beach.furniture_types.view', 'Tipos de Mobiliario', 'config', 1, 22, 'fa-shapes', '/beach/config/furniture-types', menu_config_id),
        ('beach.furniture.view', 'Mobiliario', 'config', 1, 23, 'fa-couch', '/beach/config/furniture', menu_config_id),
        ('beach.pricing.view', 'Precios', 'config', 1, 24, 'fa-tags', '/beach/config/pricing', menu_config_id),
        ('beach.states.view', 'Estados', 'config', 1, 25, 'fa-toggle-on', '/beach/config/states', menu_config_id),

        # Operaciones children
        ('beach.map.view', 'Mapa', 'operations', 1, 31, 'fa-map', '/beach/map', menu_operations_id),
        ('beach.reservations.view', 'Reservas', 'operations', 1, 32, 'fa-calendar-check', '/beach/reservations', menu_operations_id),
        ('beach.customers.view', 'Clientes', 'operations', 1, 33, 'fa-address-book', '/beach/customers', menu_operations_id),

        # Informes children
        ('beach.reports.view', 'Reportes', 'reports', 1, 41, 'fa-file-lines', '/beach/reports', menu_reports_id),
        ('beach.analytics.view', 'Analytics', 'reports', 1, 42, 'fa-chart-pie', '/beach/analytics', menu_reports_id),
    ]

    for code, name, module, is_menu, menu_order, menu_icon, menu_url, parent_id in child_permissions:
        db.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, module, is_menu, menu_order, menu_icon, menu_url, parent_id))

    # 4. Create non-menu action permissions
    action_permissions = [
        ('admin.users.manage', 'Gestionar Usuarios', 'admin'),
        ('admin.roles.manage', 'Gestionar Roles', 'admin'),
        ('admin.hotel_guests.import', 'Importar Huéspedes', 'admin'),
        ('admin.hotel_guests.export', 'Exportar Huéspedes', 'admin'),
        ('beach.map.interact', 'Interactuar con Mapa', 'operations'),
        ('beach.reservations.create', 'Crear Reservas', 'operations'),
        ('beach.reservations.edit', 'Editar Reservas', 'operations'),
        ('beach.reservations.delete', 'Eliminar Reservas', 'operations'),
        ('beach.reservations.change_state', 'Cambiar Estado Reservas', 'operations'),
        ('beach.customers.create', 'Crear Clientes', 'operations'),
        ('beach.customers.edit', 'Editar Clientes', 'operations'),
        ('beach.customers.merge', 'Fusionar Clientes', 'operations'),
        ('beach.zones.manage', 'Gestionar Zonas', 'config'),
        ('beach.furniture_types.manage', 'Gestionar Tipos Mobiliario', 'config'),
        ('beach.furniture.manage', 'Gestionar Mobiliario', 'config'),
        ('beach.pricing.manage', 'Gestionar Precios', 'config'),
        ('beach.states.manage', 'Gestionar Estados', 'config'),
        ('beach.config.manage', 'Gestionar Configuración', 'config'),
        ('beach.reports.export', 'Exportar Datos', 'reports'),
        ('api.access', 'Acceso API', 'api'),
        ('api.admin', 'Administración API', 'api'),
    ]

    for code, name, module in action_permissions:
        db.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES (?, ?, ?, 0)
        ''', (code, name, module))

    # 5. Assign Permissions to Roles
    # Get role IDs
    admin_role_id = db.execute('SELECT id FROM roles WHERE name = "admin"').fetchone()[0]
    manager_role_id = db.execute('SELECT id FROM roles WHERE name = "manager"').fetchone()[0]
    staff_role_id = db.execute('SELECT id FROM roles WHERE name = "staff"').fetchone()[0]
    readonly_role_id = db.execute('SELECT id FROM roles WHERE name = "readonly"').fetchone()[0]

    # Admin gets all permissions
    all_perms = db.execute('SELECT id FROM permissions').fetchall()
    for perm in all_perms:
        db.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                   (admin_role_id, perm[0]))

    # Manager gets operations, config, reports menus and beach.* permissions
    manager_perms = db.execute('''
        SELECT id FROM permissions
        WHERE code LIKE "beach.%"
           OR code LIKE "menu.%"
           OR code = "admin.hotel_guests.view"
    ''').fetchall()
    for perm in manager_perms:
        db.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                   (manager_role_id, perm[0]))

    # Staff gets view + create + edit beach operations
    staff_perms = db.execute('''
        SELECT id FROM permissions
        WHERE code LIKE "beach.%.view"
           OR code LIKE "beach.%.create"
           OR code LIKE "beach.%.edit"
           OR code = "beach.map.interact"
           OR code = "menu.operations"
    ''').fetchall()
    for perm in staff_perms:
        db.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                   (staff_role_id, perm[0]))

    # Readonly gets only view permissions and parent menus
    view_perms = db.execute('''
        SELECT id FROM permissions
        WHERE code LIKE "%.view"
           OR code LIKE "menu.%"
    ''').fetchall()
    for perm in view_perms:
        db.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                   (readonly_role_id, perm[0]))

    # 4. Create Admin User
    password_hash = generate_password_hash('admin123')
    db.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role_id, active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@purobeach.com', password_hash, 'Administrador Sistema', admin_role_id, 1))

    # 5. Create Beach Zones
    zones_data = [
        ('Primera Línea', 'Zona frente al mar con vistas directas', 1, '#FFE4B5'),
        ('Segunda Línea', 'Zona posterior con sombra natural', 2, '#F5E6D3')
    ]

    for name, description, display_order, color in zones_data:
        db.execute('''
            INSERT INTO beach_zones (name, description, display_order, color)
            VALUES (?, ?, ?, ?)
        ''', (name, description, display_order, color))

    # 6. Create Furniture Types (with v2 enhanced fields)
    furniture_types_data = [
        # (type_code, display_name, icon, default_color, min_cap, max_cap, suite_only,
        #  map_shape, width, height, border_radius, fill_color, stroke_color,
        #  default_capacity, default_rotation, is_decorative, number_prefix, display_order, status_colors)
        ('hamaca', 'Hamaca', 'fa-umbrella-beach', '#A0522D', 1, 2, 0,
         'rounded_rect', 100, 45, 8, '#A0522D', '#654321',
         2, 0, 0, 'H', 1,
         '{"available":"#D2B48C","reserved":"#4CAF50","occupied":"#F44336","maintenance":"#9E9E9E"}'),
        ('balinesa', 'Balinesa', 'fa-bed', '#8B4513', 2, 4, 0,
         'rounded_rect', 120, 100, 4, '#8B4513', '#4A3728',
         4, 0, 0, 'B', 2,
         '{"available":"#E8D4B8","reserved":"#4CAF50","occupied":"#F44336","maintenance":"#9E9E9E"}'),
        ('sombrilla', 'Sombrilla', 'fa-umbrella', '#6B8E23', 0, 0, 0,
         'circle', 60, 60, 0, '#6B8E23', '#556B2F',
         0, 0, 1, 'S', 10,
         '{"available":"#90EE90","reserved":"#4CAF50","occupied":"#F44336","maintenance":"#9E9E9E"}'),
    ]

    for (type_code, display_name, icon, color, min_cap, max_cap, suite_only,
         map_shape, width, height, border_radius, fill_color, stroke_color,
         default_cap, default_rotation, decorative, prefix, display_order, status_colors) in furniture_types_data:
        db.execute('''
            INSERT INTO beach_furniture_types
            (type_code, display_name, icon, default_color, min_capacity, max_capacity, is_suite_only,
             map_shape, default_width, default_height, border_radius, fill_color, stroke_color,
             default_capacity, default_rotation, is_decorative, number_prefix, display_order, status_colors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (type_code, display_name, icon, color, min_cap, max_cap, suite_only,
              map_shape, width, height, border_radius, fill_color, stroke_color,
              default_cap, default_rotation, decorative, prefix, display_order, status_colors))

    # 7. Create Sample Furniture Items
    # Get zone IDs
    primera_linea_id = db.execute('SELECT id FROM beach_zones WHERE name = "Primera Línea"').fetchone()[0]
    segunda_linea_id = db.execute('SELECT id FROM beach_zones WHERE name = "Segunda Línea"').fetchone()[0]

    furniture_data = [
        # Hamacas in Primera Línea
        ('H1', primera_linea_id, 'hamaca', 2, 50, 50, 0, 60, 40, 'primera_linea,cerca_mar'),
        ('H2', primera_linea_id, 'hamaca', 2, 120, 50, 0, 60, 40, 'primera_linea,cerca_mar'),
        ('H3', primera_linea_id, 'hamaca', 2, 190, 50, 0, 60, 40, 'primera_linea'),
        ('H4', primera_linea_id, 'hamaca', 2, 260, 50, 0, 60, 40, 'primera_linea'),

        # Hamacas in Segunda Línea
        ('H5', segunda_linea_id, 'hamaca', 2, 50, 150, 0, 60, 40, 'sombra,tranquila'),
        ('H6', segunda_linea_id, 'hamaca', 2, 120, 150, 0, 60, 40, 'sombra,tranquila'),

        # Balinesas in Primera Línea
        ('B1', primera_linea_id, 'balinesa', 4, 350, 50, 0, 80, 60, 'primera_linea,vip'),
        ('B2', primera_linea_id, 'balinesa', 4, 450, 50, 0, 80, 60, 'primera_linea,vip'),

        # Balinesas in Segunda Línea
        ('B3', segunda_linea_id, 'balinesa', 4, 200, 150, 0, 80, 60, 'sombra'),
        ('B4', segunda_linea_id, 'balinesa', 4, 300, 150, 0, 80, 60, 'sombra'),
    ]

    for number, zone_id, furn_type, capacity, x, y, rotation, width, height, features in furniture_data:
        db.execute('''
            INSERT INTO beach_furniture
            (number, zone_id, furniture_type, capacity, position_x, position_y, rotation, width, height, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (number, zone_id, furn_type, capacity, x, y, rotation, width, height, features))

    # 8. Create Reservation States
    states_data = [
        ('pendiente', 'Pendiente', '#FFC107', 'fa-clock', 0, 1),
        ('confirmada', 'Confirmada', '#0066CC', 'fa-check-circle', 0, 2),
        ('checkin', 'Check-in', '#17A2B8', 'fa-user-check', 0, 3),
        ('activa', 'Activa', '#28A745', 'fa-play-circle', 0, 4),
        ('completada', 'Completada', '#6C757D', 'fa-check-double', 0, 5),
        ('cancelada', 'Cancelada', '#DC3545', 'fa-times-circle', 1, 6),
        ('noshow', 'No-Show', '#FD7E14', 'fa-user-times', 1, 7),
        ('liberada', 'Liberada', '#6C757D', 'fa-unlock', 1, 8)
    ]

    for code, name, color, icon, is_releasing, display_order in states_data:
        db.execute('''
            INSERT INTO beach_reservation_states
            (code, name, color, icon, is_availability_releasing, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, color, icon, is_releasing, display_order))

    # 9. Create Customer Preferences
    preferences_data = [
        ('pref_sombra', 'Sombra', 'Prefiere zona con sombra', 'fa-umbrella', 'sombra'),
        ('pref_primera_linea', 'Primera Línea', 'Prefiere primera línea de playa', 'fa-water', 'primera_linea'),
        ('pref_cerca_mar', 'Cerca del Mar', 'Lo más cerca posible del mar', 'fa-anchor', 'cerca_mar'),
        ('pref_tranquila', 'Zona Tranquila', 'Prefiere zona alejada y tranquila', 'fa-volume-off', 'tranquila'),
        ('pref_vip', 'VIP', 'Cliente VIP, zona premium', 'fa-star', 'vip'),
        ('pref_cerca_bar', 'Cerca del Bar', 'Cerca del bar o zona de servicio', 'fa-martini-glass', 'cerca_bar'),
        ('pref_familia', 'Zona Familiar', 'Zona adecuada para familias', 'fa-children', 'familia'),
        ('pref_accesible', 'Acceso Fácil', 'Acceso fácil para movilidad reducida', 'fa-wheelchair', 'accesible'),
    ]

    for code, name, description, icon, maps_to in preferences_data:
        db.execute('''
            INSERT INTO beach_preferences (code, name, description, icon, maps_to_feature)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, name, description, icon, maps_to))

    # 10. Create Default Configuration
    config_data = [
        ('opening_time', '09:00', 'Hora de apertura del beach club'),
        ('closing_time', '19:00', 'Hora de cierre del beach club'),
        ('advance_booking_days', '30', 'Días de antelación para reservas'),
        ('max_party_size', '8', 'Tamaño máximo de grupo'),
        ('allow_overbooking', 'false', 'Permitir sobrerreservas'),
        ('cancellation_hours', '24', 'Horas mínimas para cancelación gratuita'),
        ('default_reservation_state', 'pendiente', 'Estado por defecto de nuevas reservas'),
        ('season_current', '2025_verano', 'Temporada actual')
    ]

    for key, value, description in config_data:
        db.execute('''
            INSERT INTO beach_config (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, description))
