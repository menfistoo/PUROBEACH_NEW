"""
Database schema definitions.
Table creation, indexes, and structure management.
"""


def drop_tables(db):
    """Drop all existing tables."""
    # Disable foreign key constraints before dropping
    db.execute('PRAGMA foreign_keys = OFF')

    tables = [
        'reservation_status_history',
        'audit_log',
        'beach_config',
        'beach_packages',
        'beach_minimum_consumption_policies',
        'beach_price_catalog',
        'beach_waitlist',
        'beach_reservation_tags',
        'beach_reservation_daily_states',
        'beach_reservation_furniture',
        'beach_reservations',
        'beach_reservation_states',
        'beach_customer_preferences',
        'beach_preferences',
        'beach_customer_characteristics',
        'beach_reservation_characteristics',
        'beach_furniture_characteristics',
        'beach_characteristics',
        'beach_customer_tags',
        'beach_tags',
        'beach_customers',
        'hotel_guests',
        'beach_furniture_blocks',
        'beach_furniture_daily_positions',
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
            canvas_width REAL DEFAULT 2000,
            canvas_height REAL DEFAULT 1000,
            background_color TEXT DEFAULT '#FAFAFA',
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
            fill_color TEXT DEFAULT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2b. Furniture Blocks Table (for maintenance, VIP holds, events)
    db.execute('''
        CREATE TABLE beach_furniture_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furniture_id INTEGER NOT NULL REFERENCES beach_furniture(id) ON DELETE CASCADE,
            block_type TEXT CHECK(block_type IN ('maintenance','vip_hold','event','other')) DEFAULT 'other',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2c. Furniture Daily Positions Table (for daily repositioning)
    db.execute('''
        CREATE TABLE beach_furniture_daily_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            furniture_id INTEGER NOT NULL REFERENCES beach_furniture(id) ON DELETE CASCADE,
            date DATE NOT NULL,
            position_x REAL NOT NULL,
            position_y REAL NOT NULL,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(furniture_id, date)
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
            no_shows INTEGER DEFAULT 0,
            cancellations INTEGER DEFAULT 0,
            total_reservations INTEGER DEFAULT 0,
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

    # Características system (unified preferences + features)
    db.execute('''
        CREATE TABLE beach_characteristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            color TEXT DEFAULT '#D4AF37',
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_furniture_characteristics (
            furniture_id INTEGER REFERENCES beach_furniture(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (furniture_id, characteristic_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservation_characteristics (
            reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (reservation_id, characteristic_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_customer_characteristics (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, characteristic_id)
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
            display_priority INTEGER DEFAULT 0,
            creates_incident INTEGER DEFAULT 0,
            is_system INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
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
            calculation_type TEXT DEFAULT 'per_reservation' CHECK(calculation_type IN ('per_reservation', 'per_person')),
            furniture_type TEXT,
            customer_type TEXT,
            zone_id INTEGER REFERENCES beach_zones(id),
            priority_order INTEGER DEFAULT 0,
            policy_description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            package_description TEXT,
            base_price REAL NOT NULL,
            price_type TEXT NOT NULL CHECK(price_type IN ('per_package', 'per_person')),
            min_people INTEGER NOT NULL DEFAULT 1,
            standard_people INTEGER NOT NULL DEFAULT 2,
            max_people INTEGER NOT NULL DEFAULT 4,
            furniture_types_included TEXT,
            customer_type TEXT CHECK(customer_type IN ('interno', 'externo', 'both')),
            zone_id INTEGER REFERENCES beach_zones(id),
            valid_from DATE,
            valid_until DATE,
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT valid_people_range CHECK(min_people <= standard_people AND standard_people <= max_people),
            CONSTRAINT valid_price CHECK(base_price > 0)
        )
    ''')

    # 6b. Waitlist Table
    db.execute('''
        CREATE TABLE beach_waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            external_name TEXT,
            external_phone TEXT,
            requested_date DATE NOT NULL,
            num_people INTEGER NOT NULL DEFAULT 1,
            preferred_zone_id INTEGER REFERENCES beach_zones(id),
            preferred_furniture_type_id INTEGER REFERENCES beach_furniture_types(id),
            time_preference TEXT CHECK(time_preference IN ('morning', 'afternoon', 'all_day', 'manana', 'tarde', 'mediodia', 'todo_el_dia')),
            reservation_type TEXT DEFAULT 'incluido' CHECK(reservation_type IN ('incluido', 'paquete', 'consumo_minimo')),
            package_id INTEGER REFERENCES beach_packages(id),
            notes TEXT,
            status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'contacted', 'converted', 'declined', 'no_answer', 'expired')),
            converted_reservation_id INTEGER REFERENCES beach_reservations(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
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

    # Furniture blocks indexes
    db.execute('CREATE INDEX idx_furniture_blocks_dates ON beach_furniture_blocks(start_date, end_date, furniture_id)')
    db.execute('CREATE INDEX idx_furniture_blocks_type ON beach_furniture_blocks(block_type)')

    # Furniture daily positions indexes
    db.execute('CREATE INDEX idx_daily_positions_date ON beach_furniture_daily_positions(date, furniture_id)')

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

    # Waitlist indexes
    db.execute('CREATE INDEX idx_waitlist_date_status ON beach_waitlist(requested_date, status)')
    db.execute('CREATE INDEX idx_waitlist_customer ON beach_waitlist(customer_id)')
