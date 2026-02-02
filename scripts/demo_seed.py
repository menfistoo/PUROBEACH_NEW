#!/usr/bin/env python3
"""
Comprehensive Demo Seed Script for Purobeach Beach Club

Creates realistic demo data for demonstrating the beach club management system.
Preserves admin users, roles, and permissions while creating:
- 2 zones (Pool Club with furniture, empty Terraza Sur)
- ~80 furniture pieces arranged realistically
- ~40 diverse clients with history
- ~50 reservations across 30+ days for analytics
- Pricing and configuration data

Usage: docker exec purobeach-app python3 /app/scripts/demo_seed.py
"""

import sqlite3
import sys
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
import random
import json

# Add the app directory to Python path for imports
sys.path.insert(0, '/app')

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('/app/instance/beach_club.db')

def clear_demo_data(conn):
    """Clear existing demo data while preserving admin setup."""
    print("🧹 Clearing existing demo data...")
    
    cursor = conn.cursor()
    
    # Disable foreign key constraints temporarily
    cursor.execute('PRAGMA foreign_keys = OFF')
    
    # Clear demo data tables (preserve users, roles, permissions)
    tables_to_clear = [
        'reservation_status_history',
        'audit_log',
        'beach_waitlist',
        'beach_reservation_tags',
        'beach_reservation_daily_states', 
        'beach_reservation_furniture',
        'beach_reservations',
        'beach_customer_preferences',
        'beach_customer_characteristics',
        'beach_customer_tags',
        'beach_customers',
        'hotel_guests',
        'beach_furniture_blocks',
        'beach_furniture_daily_positions',
        'beach_furniture',
        'beach_price_catalog',
        'beach_minimum_consumption_policies',
        'beach_packages',
    ]
    
    for table in tables_to_clear:
        cursor.execute(f'DELETE FROM {table}')
        print(f"   Cleared {table}")
    
    # Clear non-system zones and furniture types (keep system ones from seed.py)
    cursor.execute('DELETE FROM beach_zones WHERE name NOT IN ("Primera Línea", "Segunda Línea")')
    cursor.execute('DELETE FROM beach_furniture_types WHERE type_code NOT IN ("hamaca", "balinesa", "sombrilla", "piscina")')
    
    # Re-enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys = ON')
    
    conn.commit()
    print("✅ Demo data cleared")

def create_zones(conn):
    """Create demo zones."""
    print("🏖️ Creating demo zones...")
    
    cursor = conn.cursor()
    
    zones_data = [
        ('Pool Club', 'Central pool area with sun loungers arranged around the pool', 1, '#87CEEB', 2200, 1400, '#F0F8FF'),
        ('Terraza Sur', 'Southern terrace area - empty for live configuration demo', 2, '#DDA0DD', 1800, 1000, '#FDF5E6'),
    ]
    
    zone_ids = {}
    for name, description, order, color, width, height, bg_color in zones_data:
        cursor.execute('''
            INSERT INTO beach_zones (name, description, display_order, color, canvas_width, canvas_height, background_color, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (name, description, order, color, width, height, bg_color))
        
        zone_ids[name] = cursor.lastrowid
        print(f"   Created zone: {name} (ID: {zone_ids[name]})")
    
    conn.commit()
    return zone_ids

def create_furniture_types(conn):
    """Create additional furniture types if needed."""
    print("🪑 Ensuring furniture types exist...")
    
    cursor = conn.cursor()
    
    # Check existing types
    cursor.execute('SELECT type_code FROM beach_furniture_types')
    existing_types = {row[0] for row in cursor.fetchall()}
    
    # Add missing types
    new_types = [
        ('mesa_auxiliar', 'Mesa Auxiliar', 'fa-table', '#8B4513', 0, 0, 0,
         'rounded_rect', 40, 30, 4, '#8B4513', '#654321',
         0, 0, 1, 'M', 30,
         '{}'),
    ]
    
    for type_data in new_types:
        type_code = type_data[0]
        if type_code not in existing_types:
            cursor.execute('''
                INSERT INTO beach_furniture_types
                (type_code, display_name, icon, default_color, min_capacity, max_capacity, is_suite_only,
                 map_shape, default_width, default_height, border_radius, fill_color, stroke_color,
                 default_capacity, default_rotation, is_decorative, number_prefix, display_order, status_colors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', type_data)
            print(f"   Added furniture type: {type_data[1]}")
    
    conn.commit()

def create_pool_club_furniture(conn, zone_id):
    """Create Pool Club zone furniture layout."""
    print("🏊 Creating Pool Club furniture layout...")
    
    cursor = conn.cursor()
    
    furniture_data = []
    
    # Central decorative pool (400x200 pixels)
    furniture_data.append({
        'number': 'POOL1',
        'zone_id': zone_id,
        'furniture_type': 'piscina',
        'capacity': 0,
        'position_x': 900,  # Centered in 2200px width
        'position_y': 600,  # Centered in 1400px height
        'rotation': 0,
        'width': 400,
        'height': 200,
        'features': 'decorative_pool',
        'is_decorative': 1
    })
    
    # Hamacas around the pool in realistic arrangement
    hamaca_num = 1
    
    # Top row (above pool) - 12 hamacas
    for i in range(12):
        x = 600 + (i * 100)  # Start left of pool, spread across
        y = 200
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca',
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 180,  # Facing the pool
            'width': 80,
            'height': 45,
            'features': 'primera_linea,cerca_mar'
        })
        hamaca_num += 1
    
    # Bottom row (below pool) - 12 hamacas  
    for i in range(12):
        x = 600 + (i * 100)
        y = 1000
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca', 
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 0,  # Facing the pool
            'width': 80,
            'height': 45,
            'features': 'primera_linea'
        })
        hamaca_num += 1
    
    # Left side - 8 hamacas
    for i in range(8):
        x = 300
        y = 350 + (i * 80)
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca',
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 90,  # Facing the pool
            'width': 80,
            'height': 45,
            'features': 'segunda_linea,sombra'
        })
        hamaca_num += 1
    
    # Right side - 8 hamacas
    for i in range(8):
        x = 1700
        y = 350 + (i * 80)
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca',
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 270,  # Facing the pool
            'width': 80,
            'height': 45,
            'features': 'segunda_linea'
        })
        hamaca_num += 1
    
    # VIP Balinesas - 6 pieces in prime positions
    balinesa_positions = [
        {'x': 450, 'y': 150, 'features': 'vip,primera_linea,cerca_mar'},
        {'x': 750, 'y': 150, 'features': 'vip,primera_linea,cerca_mar'},
        {'x': 1050, 'y': 150, 'features': 'vip,primera_linea,cerca_mar'},
        {'x': 1350, 'y': 150, 'features': 'vip,primera_linea,cerca_mar'},
        {'x': 450, 'y': 1100, 'features': 'vip,primera_linea'},
        {'x': 1350, 'y': 1100, 'features': 'vip,primera_linea'},
    ]
    
    for i, pos in enumerate(balinesa_positions, 1):
        furniture_data.append({
            'number': f'B{i:02d}',
            'zone_id': zone_id,
            'furniture_type': 'balinesa',
            'capacity': 4,
            'position_x': pos['x'],
            'position_y': pos['y'],
            'rotation': 0,
            'width': 120,
            'height': 100,
            'features': pos['features']
        })
    
    # Additional hamacas in segunda línea - fill to ~80 total
    remaining = 80 - hamaca_num + 1
    
    # Second row behind top
    for i in range(min(12, remaining)):
        x = 600 + (i * 100)
        y = 100
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca',
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 180,
            'width': 80,
            'height': 45,
            'features': 'segunda_linea,sombra'
        })
        hamaca_num += 1
    
    remaining -= 12
    
    # Second row behind bottom
    for i in range(min(12, remaining)):
        x = 600 + (i * 100)
        y = 1200
        furniture_data.append({
            'number': f'H{hamaca_num:02d}',
            'zone_id': zone_id,
            'furniture_type': 'hamaca',
            'capacity': 2,
            'position_x': x,
            'position_y': y,
            'rotation': 0,
            'width': 80,
            'height': 45,
            'features': 'segunda_linea'
        })
        hamaca_num += 1
    
    # Decorative sombrillas - 6 pieces for shade
    sombrilla_positions = [
        {'x': 200, 'y': 300}, {'x': 200, 'y': 700}, {'x': 200, 'y': 1100},
        {'x': 1900, 'y': 300}, {'x': 1900, 'y': 700}, {'x': 1900, 'y': 1100},
    ]
    
    for i, pos in enumerate(sombrilla_positions, 1):
        furniture_data.append({
            'number': f'S{i:02d}',
            'zone_id': zone_id,
            'furniture_type': 'sombrilla',
            'capacity': 0,
            'position_x': pos['x'],
            'position_y': pos['y'],
            'rotation': 0,
            'width': 60,
            'height': 60,
            'features': 'sombra',
            'is_decorative': 1
        })
    
    # Insert all furniture
    for item in furniture_data:
        cursor.execute('''
            INSERT INTO beach_furniture 
            (number, zone_id, furniture_type, capacity, position_x, position_y, rotation, width, height, features, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            item['number'], item['zone_id'], item['furniture_type'], item['capacity'],
            item['position_x'], item['position_y'], item['rotation'], 
            item['width'], item['height'], item['features']
        ))
    
    conn.commit()
    
    print(f"   Created {len(furniture_data)} furniture pieces")
    return len(furniture_data)

def create_pricing_data(conn):
    """Create pricing catalog and policies."""
    print("💰 Creating pricing data...")
    
    cursor = conn.cursor()
    
    # Get zone IDs
    cursor.execute('SELECT id, name FROM beach_zones')
    zones = {name: id for id, name in cursor.fetchall()}
    
    # Price catalog
    pricing_data = [
        # Pool Club prices
        ('Hamaca Pool Club Primera', 'hamaca', 'interno', zones.get('Pool Club'), 45.0, 50.0, 60.0),
        ('Hamaca Pool Club Primera Ext', 'hamaca', 'externo', zones.get('Pool Club'), 63.0, 70.0, 84.0),  # 40% markup
        ('Balinesa Pool Club VIP', 'balinesa', 'interno', zones.get('Pool Club'), 75.0, 85.0, 95.0),
        ('Balinesa Pool Club VIP Ext', 'balinesa', 'externo', zones.get('Pool Club'), 105.0, 120.0, 135.0),  # 40% markup
        
        # General pricing (any zone)
        ('Hamaca Estándar', 'hamaca', 'interno', None, 35.0, 40.0, 50.0),
        ('Hamaca Estándar Ext', 'hamaca', 'externo', None, 50.0, 56.0, 70.0),
        ('Balinesa Estándar', 'balinesa', 'interno', None, 65.0, 75.0, 85.0), 
        ('Balinesa Estándar Ext', 'balinesa', 'externo', None, 90.0, 105.0, 120.0),
        ('Sombrilla', 'sombrilla', None, None, 20.0, 25.0, 30.0),
    ]
    
    # Valid from today for 1 year
    valid_from = date.today()
    valid_until = valid_from + timedelta(days=365)
    
    for name, furniture_type, customer_type, zone_id, base, weekend, holiday in pricing_data:
        cursor.execute('''
            INSERT INTO beach_price_catalog 
            (name, furniture_type, customer_type, zone_id, base_price, weekend_price, holiday_price, valid_from, valid_until, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (name, furniture_type, customer_type, zone_id, base, weekend, holiday, valid_from, valid_until))
    
    # Minimum consumption policies
    consumption_policies = [
        ('VIP Balinesa Mínimo', 150.0, 'per_reservation', 'balinesa', None, zones.get('Pool Club'), 1),
        ('Externa General', 50.0, 'per_person', None, 'externo', None, 2),
        ('Grupo Grande', 300.0, 'per_reservation', None, None, None, 3),
    ]
    
    for policy_name, amount, calc_type, furniture_type, customer_type, zone_id, priority in consumption_policies:
        cursor.execute('''
            INSERT INTO beach_minimum_consumption_policies
            (policy_name, minimum_amount, calculation_type, furniture_type, customer_type, zone_id, priority_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (policy_name, amount, calc_type, furniture_type, customer_type, zone_id, priority))
    
    # Packages
    packages_data = [
        ('Día Completo VIP', 'Hamaca + bebida + toalla + servicio personalizado', 125.0, 'per_package', 1, 2, 4, 'hamaca,balinesa', 'interno', zones.get('Pool Club')),
        ('Grupo Familiar', 'Perfecto para familias de 3-6 personas', 200.0, 'per_package', 3, 4, 6, 'hamaca,balinesa', 'both', None),
        ('Day Pass Premium', 'Acceso completo con consumo incluido', 95.0, 'per_person', 1, 1, 2, 'hamaca', 'externo', None),
    ]
    
    for pkg_name, description, price, price_type, min_people, std_people, max_people, furniture_types, customer_type, zone_id in packages_data:
        cursor.execute('''
            INSERT INTO beach_packages 
            (package_name, package_description, base_price, price_type, min_people, standard_people, max_people, 
             furniture_types_included, customer_type, zone_id, valid_from, valid_until, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (pkg_name, description, price, price_type, min_people, std_people, max_people, furniture_types, customer_type, zone_id, valid_from, valid_until))
    
    conn.commit()
    print("   Created pricing catalog, consumption policies, and packages")

def create_demo_clients(conn):
    """Create diverse demo clients."""
    print("👥 Creating demo clients...")
    
    cursor = conn.cursor()
    
    # Get state ID for confirmada
    cursor.execute('SELECT id FROM beach_reservation_states WHERE code = "confirmada"')
    confirmed_state_id = cursor.fetchone()[0]
    
    clients_data = []
    
    # VIP Hotel Guests (internal) - Suites 201-220
    vip_guests = [
        ('Emma', 'Thompson', 'emma.thompson@luxurytravel.com', '+44 20 7123 4567', '203', 'en', 'Renowned actress, prefers tranquil spots'),
        ('Jean', 'Dupont', 'j.dupont@parishotels.fr', '+33 1 42 86 75 49', '207', 'fr', 'French businessman, frequent visitor'),
        ('Carlos', 'Mendoza', 'carlos@mendozafamily.es', '+34 91 234 5678', '211', 'es', 'Spanish tech entrepreneur, family man'),
        ('Sophia', 'Rossi', 'sophia.rossi@milanodesign.it', '+39 02 7234 5678', '215', 'it', 'Italian fashion designer, loves poolside meetings'),
        ('Michael', 'Schmidt', 'mschmidt@berlinventures.de', '+49 30 1234 5678', '218', 'de', 'German investor, golf enthusiast'),
    ]
    
    for first_name, last_name, email, phone, room, lang, notes in vip_guests:
        # Create hotel guest record first
        cursor.execute('''
            INSERT INTO hotel_guests 
            (room_number, guest_name, arrival_date, departure_date, num_adults, num_children, 
             vip_code, guest_type, email, phone, is_main_guest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (room, f"{first_name} {last_name}", 
              date.today() - timedelta(days=2), 
              date.today() + timedelta(days=5),
              2, 0, 'VIP_SUITE', 'VIP', email, phone))
        
        # Create customer record
        clients_data.append({
            'customer_type': 'interno',
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'room_number': room,
            'language': lang,
            'notes': notes,
            'vip_status': 1,
            'total_visits': random.randint(3, 12),
            'total_spent': random.randint(2000, 8000),
            'last_visit': date.today() - timedelta(days=random.randint(1, 30))
        })
    
    # Regular Hotel Guests (internal) - Standard rooms 101-180
    regular_guests = [
        ('Ana', 'García', 'ana.garcia@email.com', '+34 666 123 456', '125', 'es', 'Family from Madrid, regular summer visitors'),
        ('Tom', 'Johnson', 'tjohnson@email.co.uk', '+44 7700 900 123', '142', 'en', 'British couple, honeymoon'),
        ('Marie', 'Laurent', 'marie.l@email.fr', '+33 6 12 34 56 78', '156', 'fr', 'French family, kids love the pool'),
        ('Pietro', 'Bianchi', 'p.bianchi@email.it', '+39 333 123 4567', '167', 'it', 'Italian couple, anniversary trip'),
        ('Hans', 'Mueller', 'h.mueller@email.de', '+49 171 1234567', '173', 'de', 'German retirees, peaceful vacation'),
        ('Elena', 'Rodríguez', 'elena.r@email.com', '+34 678 901 234', '134', 'es', 'Barcelona family with teenagers'),
        ('James', 'Wilson', 'j.wilson@email.com', '+44 7890 123 456', '148', 'en', 'London businessman with family'),
        ('Claire', 'Martin', 'claire.m@email.fr', '+33 7 89 01 23 45', '162', 'fr', 'French artist, loves morning sun'),
    ]
    
    for first_name, last_name, email, phone, room, lang, notes in regular_guests:
        # Create hotel guest record
        cursor.execute('''
            INSERT INTO hotel_guests 
            (room_number, guest_name, arrival_date, departure_date, num_adults, num_children, 
             guest_type, email, phone, is_main_guest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (room, f"{first_name} {last_name}",
              date.today() - timedelta(days=1),
              date.today() + timedelta(days=random.randint(3, 7)),
              random.randint(2, 4), random.randint(0, 2), 'STANDARD', email, phone))
        
        clients_data.append({
            'customer_type': 'interno',
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'room_number': room,
            'language': lang,
            'notes': notes,
            'vip_status': 0,
            'total_visits': random.randint(1, 4),
            'total_spent': random.randint(300, 1500),
            'last_visit': date.today() - timedelta(days=random.randint(1, 7))
        })
    
    # External Clients - Mix of locals and day visitors
    external_clients = [
        # Local Residents (repeat customers)
        ('Marta', 'González', 'marta.gonzalez@local.es', '+34 655 123 789', None, 'es', 'Local resident, weekend regular'),
        ('Pedro', 'Sánchez', 'pedro.sanchez@local.es', '+34 666 987 654', None, 'es', 'Local businessman, lunch meetings'), 
        ('Isabel', 'López', 'isabel.lopez@local.es', '+34 677 456 123', None, 'es', 'Local family, children love the area'),
        ('Jorge', 'Martín', 'jorge.martin@local.es', '+34 688 321 654', None, 'es', 'Local entrepreneur, networking events'),
        
        # Day Visitors
        ('Sarah', 'Connor', 'sarah.connor@visitor.com', '+1 555 123 4567', None, 'en', 'American tourist, one-day visit'),
        ('Yuki', 'Tanaka', 'yuki.t@visitor.jp', '+81 90 1234 5678', None, 'en', 'Japanese couple, vacation day trip'),
        ('Lars', 'Andersen', 'lars.a@visitor.no', '+47 123 45 678', None, 'en', 'Norwegian family, summer holiday'),
        ('Olga', 'Petrov', 'olga.p@visitor.ru', '+7 916 123 4567', None, 'ru', 'Russian businesswoman, conference break'),
        
        # Recurring External Clients
        ('Roberto', 'Silva', 'roberto.silva@recurring.es', '+34 699 876 543', None, 'es', 'Monthly visitor, prefers corner spots'),
        ('Carmen', 'Vega', 'carmen.vega@recurring.es', '+34 611 234 567', None, 'es', 'Weekend regular, brings friends'),
        ('Fernando', 'Castro', 'fernando.castro@recurring.es', '+34 622 345 678', None, 'es', 'Business lunches, loyal customer'),
        ('Patricia', 'Moreno', 'patricia.moreno@recurring.es', '+34 633 456 789', None, 'es', 'Book club meetings, quiet preferences'),
        
        # Corporate Group - Deloitte Event
        ('David', 'Reynolds', 'david.reynolds@deloitte.com', '+44 20 7123 9876', None, 'en', 'Deloitte team lead, corporate event'),
        ('Laura', 'Bennett', 'laura.bennett@deloitte.com', '+44 20 7123 9877', None, 'en', 'Deloitte consultant, team building'),
        ('Mark', 'Thompson', 'mark.thompson@deloitte.com', '+44 20 7123 9878', None, 'en', 'Deloitte manager, company retreat'),
        ('Rachel', 'Green', 'rachel.green@deloitte.com', '+44 20 7123 9879', None, 'en', 'Deloitte analyst, corporate group'),
        ('Steven', 'Clark', 'steven.clark@deloitte.com', '+44 20 7123 9880', None, 'en', 'Deloitte director, business event'),
    ]
    
    for first_name, last_name, email, phone, room, lang, notes in external_clients:
        # Determine repeat customer stats
        is_repeat = 'recurring' in notes.lower() or 'regular' in notes.lower() or 'monthly' in notes.lower()
        visits = random.randint(8, 25) if is_repeat else random.randint(1, 3)
        spent = random.randint(1500, 5000) if is_repeat else random.randint(80, 500)
        
        clients_data.append({
            'customer_type': 'externo',
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'room_number': room,
            'language': lang,
            'notes': notes,
            'vip_status': 1 if 'director' in notes.lower() or 'entrepreneur' in notes.lower() else 0,
            'total_visits': visits,
            'total_spent': spent,
            'last_visit': date.today() - timedelta(days=random.randint(1, 90)) if is_repeat else None
        })
    
    # Insert all clients
    client_ids = {}
    for client in clients_data:
        cursor.execute('''
            INSERT INTO beach_customers 
            (customer_type, first_name, last_name, email, phone, room_number, language, notes, 
             vip_status, total_visits, total_spent, last_visit, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client['customer_type'], client['first_name'], client['last_name'], 
            client['email'], client['phone'], client['room_number'], client['language'], 
            client['notes'], client['vip_status'], client['total_visits'], 
            client['total_spent'], client['last_visit'], 
            datetime.now(), datetime.now()
        ))
        
        client_key = f"{client['first_name']} {client['last_name']}"
        client_ids[client_key] = cursor.lastrowid
    
    conn.commit()
    
    print(f"   Created {len(clients_data)} clients:")
    print(f"     - VIP hotel guests: 5")
    print(f"     - Regular hotel guests: 8") 
    print(f"     - External clients: {len(external_clients)}")
    
    return client_ids

def create_demo_reservations(conn, client_ids):
    """Create realistic reservations over past 30 days + next 7 days."""
    print("📅 Creating demo reservations...")
    
    cursor = conn.cursor()
    
    # Get required IDs
    cursor.execute('SELECT id FROM beach_reservation_states WHERE code = "confirmada"')
    confirmed_state_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id FROM beach_reservation_states WHERE code = "sentada"')
    occupied_state_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id FROM beach_reservation_states WHERE code = "cancelada"')
    cancelled_state_id = cursor.fetchone()[0]
    
    cursor.execute('SELECT id, furniture_type FROM beach_furniture WHERE active = 1')
    furniture_list = cursor.fetchall()
    
    cursor.execute('SELECT id, base_price FROM beach_price_catalog LIMIT 1')
    price_info = cursor.fetchone()
    base_price_catalog_id, base_price = price_info if price_info else (None, 45.0)
    
    # Date range: 30 days ago to 7 days ahead
    start_date = date.today() - timedelta(days=30)
    end_date = date.today() + timedelta(days=7)
    
    reservations_data = []
    
    # Generate reservations with realistic patterns
    current_date = start_date
    while current_date <= end_date:
        is_weekend = current_date.weekday() >= 5  # Saturday = 5, Sunday = 6
        is_past = current_date < date.today()
        is_today = current_date == date.today()
        
        # More reservations on weekends
        daily_reservations = random.randint(8, 15) if is_weekend else random.randint(3, 8)
        
        for _ in range(daily_reservations):
            # Pick random client
            client_name = random.choice(list(client_ids.keys()))
            client_id = client_ids[client_name]
            
            # Multi-day reservations (10% chance for 2-5 day stays)
            if random.random() < 0.1 and current_date <= end_date - timedelta(days=2):
                stay_days = random.randint(2, 5)
                reservation_end = min(current_date + timedelta(days=stay_days - 1), end_date)
            else:
                reservation_end = current_date
            
            # Determine state based on date
            if is_past:
                # Past reservations: mostly occupied/completed, some cancelled
                if random.random() < 0.85:
                    state_id = occupied_state_id  # Most were occupied
                else:
                    state_id = cancelled_state_id  # Some cancellations
            elif is_today:
                # Today: mix of confirmed and occupied
                state_id = occupied_state_id if random.random() < 0.6 else confirmed_state_id
            else:
                # Future: mostly confirmed
                state_id = confirmed_state_id
            
            # Party size
            num_people = random.choices([1, 2, 3, 4, 5, 6], weights=[5, 40, 25, 20, 7, 3])[0]
            
            # Pricing (weekend markup, hotel guest discount)
            price = base_price
            if is_weekend:
                price *= 1.2  # Weekend markup
            
            # Hotel guest discount (30%)
            if 'interno' in str(client_name).lower() or random.random() < 0.35:  # Approximate internal guests
                final_price = price * 0.7
            else:
                final_price = price
            
            # Some reservations have special features or notes
            notes_options = [
                None,
                "Cumpleaños - decoración especial solicitada",
                "Aniversario - botella de cava",
                "Reunión de negocios - mesa adicional necesaria",
                "Familia con niños pequeños",
                "Cliente VIP - atención personalizada",
                "Evento corporativo",
                "Celebración familiar",
            ]
            
            notes = random.choice(notes_options) if random.random() < 0.3 else None
            
            reservations_data.append({
                'customer_id': client_id,
                'start_date': current_date,
                'end_date': reservation_end,
                'num_people': num_people,
                'state_id': state_id,
                'notes': notes,
                'source': random.choice(['direct', 'phone', 'hotel', 'website', 'walk_in']),
                'price': price,
                'final_price': final_price,
                'price_catalog_id': base_price_catalog_id,
                'paid': 1 if is_past or (is_today and state_id == occupied_state_id) else 0,
                'reservation_type': random.choice(['normal', 'package', 'corporate']) if random.random() < 0.2 else 'normal',
                'payment_method': random.choice(['cash', 'card', 'room_charge']) if random.random() < 0.8 else None,
            })
        
        current_date += timedelta(days=1)
    
    # Special corporate event reservations for Deloitte group
    deloitte_clients = [name for name in client_ids.keys() if 'deloitte' in str(client_ids[name])][:5]
    if deloitte_clients:
        event_date = date.today() + timedelta(days=3)
        for client_name in deloitte_clients:
            reservations_data.append({
                'customer_id': client_ids[client_name],
                'start_date': event_date,
                'end_date': event_date,
                'num_people': 2,
                'state_id': confirmed_state_id,
                'notes': "Evento Corporativo Deloitte - Team Building",
                'source': 'corporate',
                'price': 75.0,
                'final_price': 75.0,
                'price_catalog_id': base_price_catalog_id,
                'paid': 0,
                'reservation_type': 'corporate',
                'payment_method': 'card',
            })
    
    # Insert reservations and assign furniture
    reservation_count = 0
    furniture_assignments = 0
    
    for res_data in reservations_data:
        # Insert reservation
        cursor.execute('''
            INSERT INTO beach_reservations 
            (customer_id, start_date, end_date, num_people, state_id, notes, source, 
             price, final_price, price_catalog_id, paid, reservation_type, payment_method,
             current_state, payment_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            res_data['customer_id'], res_data['start_date'], res_data['end_date'], 
            res_data['num_people'], res_data['state_id'], res_data['notes'], res_data['source'],
            res_data['price'], res_data['final_price'], res_data['price_catalog_id'],
            res_data['paid'], res_data['reservation_type'], res_data['payment_method'],
            'Confirmada', 'SI' if res_data['paid'] else 'NO',
            datetime.now(), datetime.now()
        ))
        
        reservation_id = cursor.lastrowid
        reservation_count += 1
        
        # Assign furniture (80% chance of getting furniture)
        if random.random() < 0.8 and furniture_list:
            furniture_id, furniture_type = random.choice(furniture_list)
            
            # Assign for each day of the reservation
            current_assign_date = res_data['start_date']
            while current_assign_date <= res_data['end_date']:
                cursor.execute('''
                    INSERT INTO beach_reservation_furniture 
                    (reservation_id, furniture_id, assignment_date)
                    VALUES (?, ?, ?)
                ''', (reservation_id, furniture_id, current_assign_date))
                furniture_assignments += 1
                current_assign_date += timedelta(days=1)
    
    # Add some furniture blocks for maintenance
    maintenance_blocks = [
        (random.choice(furniture_list)[0], 'maintenance', 
         date.today() + timedelta(days=1), date.today() + timedelta(days=3),
         'Mantenimiento preventivo', 'Revisión anual programada'),
        (random.choice(furniture_list)[0], 'event', 
         date.today() + timedelta(days=5), date.today() + timedelta(days=5),
         'Reserva especial VIP', 'Evento privado cliente premium'),
    ]
    
    for furniture_id, block_type, start_block_date, end_block_date, reason, notes in maintenance_blocks:
        cursor.execute('''
            INSERT INTO beach_furniture_blocks 
            (furniture_id, block_type, start_date, end_date, reason, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (furniture_id, block_type, start_block_date, end_block_date, reason, notes, 'demo_seed'))
    
    conn.commit()
    
    print(f"   Created {reservation_count} reservations:")
    print(f"     - Past 30 days: analytics-ready data")
    print(f"     - Next 7 days: upcoming reservations")
    print(f"     - Furniture assignments: {furniture_assignments}")
    print(f"     - Maintenance blocks: {len(maintenance_blocks)}")

def add_characteristics_and_tags(conn, client_ids):
    """Add characteristics and tags to furniture and customers."""
    print("🏷️ Adding characteristics and tags...")
    
    cursor = conn.cursor()
    
    # Get characteristics IDs
    cursor.execute('SELECT id, code FROM beach_characteristics')
    characteristics = {code: id for id, code in cursor.fetchall()}
    
    # Get furniture IDs by type
    cursor.execute('SELECT id, furniture_type, features FROM beach_furniture')
    furniture_data = cursor.fetchall()
    
    # Assign characteristics to furniture based on features
    for furniture_id, furniture_type, features in furniture_data:
        if not features:
            continue
            
        feature_list = features.split(',') if features else []
        for feature in feature_list:
            feature = feature.strip()
            if feature in characteristics:
                cursor.execute('''
                    INSERT OR IGNORE INTO beach_furniture_characteristics 
                    (furniture_id, characteristic_id) 
                    VALUES (?, ?)
                ''', (furniture_id, characteristics[feature]))
    
    # Create some tags
    tags_data = [
        ('VIP', '#D4AF37', 'Cliente VIP con atención especial'),
        ('Repetidor', '#28A745', 'Cliente habitual que repite visitas'),
        ('Corporativo', '#6F42C1', 'Cliente de empresa o evento corporativo'),
        ('Familia', '#FD7E14', 'Familia con niños'),
        ('Internacional', '#17A2B8', 'Cliente internacional/turista'),
        ('Local', '#6C757D', 'Cliente local/residente'),
    ]
    
    tag_ids = {}
    for name, color, description in tags_data:
        cursor.execute('''
            INSERT INTO beach_tags (name, color, description, active) 
            VALUES (?, ?, ?, 1)
        ''', (name, color, description))
        tag_ids[name] = cursor.lastrowid
    
    # Assign tags to clients based on their characteristics
    cursor.execute('SELECT id, first_name, last_name, customer_type, vip_status, notes, total_visits FROM beach_customers')
    customers_data = cursor.fetchall()
    
    for customer_id, first_name, last_name, customer_type, vip_status, notes, total_visits in customers_data:
        tags_to_assign = []
        
        if vip_status == 1:
            tags_to_assign.append('VIP')
        
        if total_visits >= 5:
            tags_to_assign.append('Repetidor')
        
        if customer_type == 'externo':
            tags_to_assign.append('Local' if 'local' in str(notes).lower() else 'Internacional')
        
        if 'deloitte' in str(notes).lower() or 'corporativo' in str(notes).lower() or 'business' in str(notes).lower():
            tags_to_assign.append('Corporativo')
        
        if 'family' in str(notes).lower() or 'familia' in str(notes).lower() or 'niños' in str(notes).lower() or 'children' in str(notes).lower():
            tags_to_assign.append('Familia')
        
        # Assign tags
        for tag_name in tags_to_assign:
            if tag_name in tag_ids:
                cursor.execute('''
                    INSERT OR IGNORE INTO beach_customer_tags 
                    (customer_id, tag_id) 
                    VALUES (?, ?)
                ''', (customer_id, tag_ids[tag_name]))
    
    conn.commit()
    
    print(f"   Added characteristics to furniture and {len(tags_data)} tag types to customers")

def print_summary(conn):
    """Print a summary of created demo data."""
    print("\n🎯 Demo Data Summary")
    print("=" * 50)
    
    cursor = conn.cursor()
    
    # Count various entities
    cursor.execute('SELECT COUNT(*) FROM beach_zones WHERE name IN ("Pool Club", "Terraza Sur")')
    zones_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM beach_furniture WHERE active = 1')
    furniture_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM beach_customers')
    customers_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM beach_reservations')
    reservations_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM beach_reservation_furniture')
    assignments_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM beach_price_catalog')
    pricing_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM hotel_guests')
    hotel_guests_count = cursor.fetchone()[0]
    
    # Customer breakdown
    cursor.execute('SELECT customer_type, COUNT(*) FROM beach_customers GROUP BY customer_type')
    customer_breakdown = dict(cursor.fetchall())
    
    # Reservation states
    cursor.execute('''
        SELECT brs.name, COUNT(*) 
        FROM beach_reservations br 
        JOIN beach_reservation_states brs ON br.state_id = brs.id 
        GROUP BY br.state_id, brs.name
    ''')
    reservation_states = dict(cursor.fetchall())
    
    # Date range
    cursor.execute('SELECT MIN(start_date), MAX(end_date) FROM beach_reservations')
    date_range = cursor.fetchone()
    
    # Revenue calculation
    cursor.execute('SELECT SUM(final_price) FROM beach_reservations WHERE paid = 1')
    paid_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(final_price) FROM beach_reservations')
    total_revenue = cursor.fetchone()[0] or 0
    
    print(f"📍 Zones Created: {zones_count}")
    print(f"   • Pool Club (with ~80 furniture pieces)")
    print(f"   • Terraza Sur (empty for live demo)")
    print()
    print(f"🪑 Furniture: {furniture_count} pieces")
    print(f"   • Hamacas around central pool")
    print(f"   • VIP Balinesas in prime positions") 
    print(f"   • Decorative sombrillas and pool")
    print()
    print(f"👥 Customers: {customers_count}")
    print(f"   • Internal (hotel): {customer_breakdown.get('interno', 0)}")
    print(f"   • External: {customer_breakdown.get('externo', 0)}")
    print(f"   • Hotel guests imported: {hotel_guests_count}")
    print()
    print(f"📅 Reservations: {reservations_count}")
    for state, count in reservation_states.items():
        print(f"   • {state}: {count}")
    print(f"   • Furniture assignments: {assignments_count}")
    print(f"   • Date range: {date_range[0]} to {date_range[1]}")
    print()
    print(f"💰 Revenue Data:")
    print(f"   • Total bookings: €{total_revenue:.2f}")
    print(f"   • Paid revenue: €{paid_revenue:.2f}")
    print(f"   • Pricing rules: {pricing_count}")
    print()
    print("✅ Demo data ready! The system now has:")
    print("   • Analytics-friendly historical data (30 days)")
    print("   • Active reservations for next week")
    print("   • Realistic customer mix with preferences")
    print("   • Corporate event demonstration (Deloitte)")
    print("   • VIP clients and repeat customers")
    print("   • Maintenance blocks and special events")
    print()
    print("🎪 You can now demonstrate:")
    print("   • Map view with occupied/available furniture")
    print("   • Reservation management and check-ins")
    print("   • Customer profiles and preferences")
    print("   • Revenue analytics and insights")
    print("   • Live furniture configuration (Terraza Sur)")

def main():
    """Main execution function."""
    print("🌊 Purobeach Demo Seed Script")
    print("=" * 50)
    print("Creating comprehensive demo data...")
    print()
    
    try:
        # Connect to database
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        
        # Enable foreign key support
        conn.execute('PRAGMA foreign_keys = ON')
        
        # Execute seeding steps
        clear_demo_data(conn)
        zone_ids = create_zones(conn)
        create_furniture_types(conn)
        create_pool_club_furniture(conn, zone_ids['Pool Club'])
        create_pricing_data(conn)
        client_ids = create_demo_clients(conn)
        create_demo_reservations(conn, client_ids)
        add_characteristics_and_tags(conn, client_ids)
        
        # Show summary
        print_summary(conn)
        
        conn.close()
        
        print("\n🎉 Demo seed completed successfully!")
        print("\nNext steps:")
        print("1. Visit https://beachclubinterno.duckdns.org")
        print("2. Login with: admin / PuroAdmin2026!")
        print("3. Check the map view to see the layout")
        print("4. Explore reservations and customer data")
        print("5. Use Terraza Sur for live configuration demo")
        
    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()