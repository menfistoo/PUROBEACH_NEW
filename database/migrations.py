"""
Database migrations.
Safe, idempotent migrations for schema evolution.
"""

from database.connection import get_db


def migrate_furniture_types_v2():
    """
    Migration: Enhance beach_furniture_types table with additional columns
    for status colors, numbering, features, zones, and display order.

    Safe to run multiple times - checks if columns already exist.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_furniture_types)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'status_colors' in existing_columns:
        print("Migration already applied - furniture_types_v2 columns exist.")
        return False

    print("Applying furniture_types_v2 migration...")

    try:
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

    Adds columns for ticket numbering, multi-state management, pricing,
    PMS integration, and hotel stay dates.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_reservations)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'ticket_number' in existing_columns:
        print("Migration already applied - reservations_v2 columns exist.")
        return False

    print("Applying reservations_v2 migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE beach_reservations ADD COLUMN ticket_number TEXT', 'ticket_number'),
            ('ALTER TABLE beach_reservations ADD COLUMN reservation_date DATE', 'reservation_date'),
            ("ALTER TABLE beach_reservations ADD COLUMN time_slot TEXT DEFAULT 'all_day'", 'time_slot'),
            ("ALTER TABLE beach_reservations ADD COLUMN current_states TEXT DEFAULT ''", 'current_states'),
            ("ALTER TABLE beach_reservations ADD COLUMN current_state TEXT DEFAULT 'Confirmada'", 'current_state'),
            ("ALTER TABLE beach_reservations ADD COLUMN payment_status TEXT DEFAULT 'NO'", 'payment_status'),
            ('ALTER TABLE beach_reservations ADD COLUMN price REAL DEFAULT 0.0', 'price'),
            ('ALTER TABLE beach_reservations ADD COLUMN final_price REAL DEFAULT 0.0', 'final_price'),
            ('ALTER TABLE beach_reservations ADD COLUMN hamaca_included INTEGER DEFAULT 1', 'hamaca_included'),
            ('ALTER TABLE beach_reservations ADD COLUMN price_catalog_id INTEGER', 'price_catalog_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN paid INTEGER DEFAULT 0', 'paid'),
            ('ALTER TABLE beach_reservations ADD COLUMN charge_to_room INTEGER DEFAULT 0', 'charge_to_room'),
            ("ALTER TABLE beach_reservations ADD COLUMN charge_reference TEXT DEFAULT ''", 'charge_reference'),
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_amount REAL DEFAULT 0.0', 'minimum_consumption_amount'),
            ('ALTER TABLE beach_reservations ADD COLUMN minimum_consumption_policy_id INTEGER', 'minimum_consumption_policy_id'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_to_pms INTEGER DEFAULT 0', 'consumption_charged_to_pms'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_at TIMESTAMP', 'consumption_charged_at'),
            ('ALTER TABLE beach_reservations ADD COLUMN consumption_charged_by TEXT', 'consumption_charged_by'),
            ('ALTER TABLE beach_reservations ADD COLUMN check_in_date DATE', 'check_in_date'),
            ('ALTER TABLE beach_reservations ADD COLUMN check_out_date DATE', 'check_out_date'),
            ("ALTER TABLE beach_reservations ADD COLUMN reservation_type TEXT DEFAULT 'normal'", 'reservation_type'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        db.execute('''
            UPDATE beach_reservations
            SET reservation_date = start_date
            WHERE reservation_date IS NULL
        ''')
        print("  Migrated start_date to reservation_date for existing records")

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

        try:
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_reservations_ticket ON beach_reservations(ticket_number)')
            print("  Created index: idx_reservations_ticket")
        except Exception:
            pass

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

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

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

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'is_main_guest' in existing_columns:
        print("Migration already applied - is_main_guest column exists.")
        return False

    print("Applying hotel_guests_multi_guest migration...")

    try:
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

        db.execute('DROP TABLE hotel_guests')
        print("  Dropped old table")

        db.execute('ALTER TABLE hotel_guests_new RENAME TO hotel_guests')
        print("  Renamed new table to hotel_guests")

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

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(hotel_guests)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'booking_reference' in existing_columns:
        print("Migration already applied - booking_reference column exists.")
        return False

    print("Applying hotel_guests_booking_reference migration...")

    try:
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

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

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


def migrate_add_sentada_state():
    """
    Migration: Add 'Sentada' state for tracking when customers are at the beach.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM beach_reservation_states WHERE code = 'sentada'")
    if cursor.fetchone():
        print("Migration already applied - Sentada state exists.")
        return False

    print("Applying add_sentada_state migration...")

    try:
        cursor.execute("SELECT MAX(display_order) as max_order FROM beach_reservation_states")
        row = cursor.fetchone()
        next_order = (row['max_order'] or 0) + 1

        cursor.execute('''
            INSERT INTO beach_reservation_states
            (code, name, color, icon, is_availability_releasing, display_order, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('sentada', 'Sentada', '#28A745', 'fa-couch', 0, next_order, 1))

        db.commit()
        print("Migration add_sentada_state applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_customers_extended_stats():
    """
    Migration: Add extended statistics columns to beach_customers.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_customers)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'no_shows' in existing_columns:
        print("Migration already applied - extended stats columns exist.")
        return False

    print("Applying customers_extended_stats migration...")

    try:
        columns_to_add = [
            ('ALTER TABLE beach_customers ADD COLUMN no_shows INTEGER DEFAULT 0', 'no_shows'),
            ('ALTER TABLE beach_customers ADD COLUMN cancellations INTEGER DEFAULT 0', 'cancellations'),
            ('ALTER TABLE beach_customers ADD COLUMN total_reservations INTEGER DEFAULT 0', 'total_reservations'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_customers_stats ON beach_customers(total_visits, no_shows, total_reservations)')
            print("  Created index: idx_customers_stats")
        except Exception:
            pass

        db.commit()
        print("Migration customers_extended_stats applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_add_furniture_types_menu():
    """
    Migration: Add 'Tipos de Mobiliario' menu permission.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM permissions WHERE code = 'beach.furniture_types.view'")
    if cursor.fetchone():
        print("Menu permission 'beach.furniture_types.view' already exists.")
        return False

    print("Adding furniture types menu permission...")

    try:
        cursor.execute("SELECT id FROM permissions WHERE code = 'menu.config'")
        parent_row = cursor.fetchone()
        if not parent_row:
            print("ERROR: Parent menu 'menu.config' not found!")
            return False
        menu_config_id = parent_row[0]

        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('beach.furniture_types.view', 'Tipos de Mobiliario', 'config', 1, 22, 'fa-shapes', '/beach/config/furniture-types', menu_config_id))

        new_perm_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item)
            VALUES (?, ?, ?, 0)
        ''', ('beach.furniture_types.manage', 'Gestionar Tipos Mobiliario', 'config'))

        manage_perm_id = cursor.lastrowid

        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_role_id = admin_row[0]
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, new_perm_id))
            cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                           (admin_role_id, manage_perm_id))

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


def migrate_reservation_states_configurable():
    """
    Migration: Make reservation states fully configurable.

    Adds columns for display_priority, creates_incident, is_system, is_default.
    Updates existing states and replaces with 6 core states.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_reservation_states)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'display_priority' in existing_columns:
        print("Migration already applied - configurable states columns exist.")
        return False

    print("Applying reservation_states_configurable migration...")

    try:
        # Add new columns
        columns_to_add = [
            ('ALTER TABLE beach_reservation_states ADD COLUMN display_priority INTEGER DEFAULT 0', 'display_priority'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN creates_incident INTEGER DEFAULT 0', 'creates_incident'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN is_system INTEGER DEFAULT 0', 'is_system'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN is_default INTEGER DEFAULT 0', 'is_default'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Deactivate legacy states
        cursor.execute('''
            UPDATE beach_reservation_states
            SET active = 0
            WHERE code IN ('pendiente', 'checkin', 'activa', 'completada')
        ''')
        print("  Deactivated legacy states: pendiente, checkin, activa, completada")

        # Update core states with new properties
        # Confirmada: display_priority=3, is_system=1, is_default=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 3, is_system = 1, is_default = 1, color = '#28A745',
                display_order = 1
            WHERE code = 'confirmada'
        ''')

        # Sentada: display_priority=6, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 6, is_system = 1, color = '#2E8B57',
                display_order = 2
            WHERE code = 'sentada'
        ''')

        # Cancelada: is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                display_order = 3
            WHERE code = 'cancelada'
        ''')

        # No-Show: creates_incident=1, is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                creates_incident = 1, color = '#FF4444', display_order = 4
            WHERE code = 'noshow'
        ''')

        # Liberada: is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                display_order = 5
            WHERE code = 'liberada'
        ''')

        print("  Updated core states with configurable properties")

        db.commit()
        print("Migration reservation_states_configurable applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
