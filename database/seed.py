"""
Database seed data.
Initial data population for fresh database installations.
"""

from werkzeug.security import generate_password_hash


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
        ('admin.hotel_guests.view', 'Huéspedes Hotel', 'admin', 1, 14, 'fa-hotel', '/admin/hotel-guests', menu_admin_id),
        ('admin.audit.view', 'Registro de Auditoría', 'admin', 0, 15, 'fa-clipboard-list', '/admin/audit', menu_admin_id),

        # Configuración children (codes match route @permission_required)
        ('beach.config.furniture.view', 'Mobiliario', 'config', 1, 22, 'fa-couch', '/beach/config/furniture-manager', menu_config_id),
        ('beach.config.pricing.view', 'Precios', 'config', 1, 24, 'fa-tags', '/beach/config/pricing', menu_config_id),
        ('beach.config.states.view', 'Estados', 'config', 1, 25, 'fa-toggle-on', '/beach/config/states', menu_config_id),
        ('beach.config.characteristics.view', 'Etiquetas y Características', 'config', 1, 26, 'fa-list-check', '/beach/config/tags-characteristics', menu_config_id),
        ('beach.config.packages.view', 'Paquetes', 'config', 0, 27, 'fa-box-open', '/beach/config/packages', menu_config_id),
        ('beach.config.minimum_consumption.view', 'Consumo Mínimo', 'config', 0, 28, 'fa-receipt', '/beach/config/minimum-consumption', menu_config_id),
        ('beach.config.map_editor.view', 'Editor de Mapa', 'config', 0, 29, 'fa-map-pin', '/beach/config/map-editor', menu_config_id),

        # Operaciones children
        ('beach.map.view', 'Mapa', 'operations', 1, 31, 'fa-map', '/beach/map', menu_operations_id),
        ('beach.reservations.view', 'Reservas', 'operations', 1, 32, 'fa-calendar-check', '/beach/reservations', menu_operations_id),
        ('beach.customers.view', 'Clientes', 'operations', 1, 33, 'fa-address-book', '/beach/customers', menu_operations_id),
        ('beach.waitlist.view', 'Lista de Espera', 'operations', 0, 34, 'fa-clock', '/beach/waitlist', menu_operations_id),

        # Informes children
        ('beach.reports.payment_reconciliation', 'Conciliación de Pagos', 'reports', 1, 41, 'fa-file-lines', '/beach/reports/payment-reconciliation', menu_reports_id),
        ('beach.analytics.view', 'Analytics', 'reports', 0, 42, 'fa-chart-pie', '/beach/analytics', menu_reports_id),
        ('beach.insights.view', 'Insights', 'reports', 1, 43, 'fa-lightbulb', '/beach/insights', menu_reports_id),
    ]

    for code, name, module, is_menu, menu_order, menu_icon, menu_url, parent_id in child_permissions:
        db.execute('''
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon, menu_url, parent_permission_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, module, is_menu, menu_order, menu_icon, menu_url, parent_id))

    # 4. Create non-menu action permissions
    action_permissions = [
        # Admin actions
        ('admin.users.manage', 'Gestionar Usuarios', 'admin'),
        ('admin.roles.manage', 'Gestionar Roles', 'admin'),
        ('admin.hotel_guests.import', 'Importar Huéspedes', 'admin'),
        ('admin.hotel_guests.export', 'Exportar Huéspedes', 'admin'),

        # Map actions
        ('beach.map.interact', 'Interactuar con Mapa', 'operations'),
        ('beach.map.edit', 'Editar Posiciones Mapa', 'operations'),

        # Reservation actions
        ('beach.reservations.create', 'Crear Reservas', 'operations'),
        ('beach.reservations.edit', 'Editar Reservas', 'operations'),
        ('beach.reservations.delete', 'Eliminar Reservas', 'operations'),
        ('beach.reservations.change_state', 'Cambiar Estado Reservas', 'operations'),

        # Customer actions
        ('beach.customers.create', 'Crear Clientes', 'operations'),
        ('beach.customers.edit', 'Editar Clientes', 'operations'),
        ('beach.customers.merge', 'Fusionar Clientes', 'operations'),

        # Config actions (codes match route @permission_required)
        ('beach.zones.view', 'Ver Zonas', 'config'),
        ('beach.zones.manage', 'Gestionar Zonas', 'config'),
        ('beach.config.furniture.manage', 'Gestionar Mobiliario', 'config'),
        ('beach.config.pricing.manage', 'Gestionar Precios', 'config'),
        ('beach.config.states.manage', 'Gestionar Estados', 'config'),
        ('beach.config.characteristics.manage', 'Gestionar Caracteristicas', 'config'),
        ('beach.config.packages.manage', 'Gestionar Paquetes', 'config'),
        ('beach.config.minimum_consumption.manage', 'Gestionar Consumo Mínimo', 'config'),
        ('beach.config.map_editor.edit', 'Editar Mapa', 'config'),
        ('beach.config.manage', 'Gestionar Configuración', 'config'),

        # Furniture special actions
        ('beach.furniture.block', 'Bloquear Mobiliario', 'operations'),
        ('beach.furniture.temporary', 'Mobiliario Temporal', 'operations'),

        # Waitlist actions
        ('beach.waitlist.create', 'Crear Lista de Espera', 'operations'),
        ('beach.waitlist.manage', 'Gestionar Lista de Espera', 'operations'),

        # Insights actions
        ('beach.insights.analytics', 'Analytics Avanzados', 'reports'),

        # Reports & API
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

    # 6. Create Admin User
    password_hash = generate_password_hash('PuroAdmin2026!')
    db.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role_id, active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@purobeach.com', password_hash, 'Administrador Sistema', admin_role_id, 1))

    # 7. Create Beach Zones
    zones_data = [
        ('Primera Línea', 'Zona frente al mar con vistas directas', 1, '#FFE4B5'),
        ('Segunda Línea', 'Zona posterior con sombra natural', 2, '#F5E6D3')
    ]

    for name, description, display_order, color in zones_data:
        db.execute('''
            INSERT INTO beach_zones (name, description, display_order, color)
            VALUES (?, ?, ?, ?)
        ''', (name, description, display_order, color))

    # 8. Create Furniture Types (with v2 enhanced fields)
    furniture_types_data = [
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
        # Decorative pool element - fill_color is primary blue, stroke_color is pattern blue
        ('piscina', 'Piscina', 'fa-water', '#87CEEB', 0, 0, 0,
         'rounded_rect', 300, 150, 12, '#87CEEB', '#5DADE2',
         0, 0, 1, 'P', 20,
         '{}'),
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

    # 9. Create Standard Furniture: 20 Hamacas in Primera Línea
    # This is the production standard layout (4 rows x 5 columns)
    primera_linea_id = db.execute('SELECT id FROM beach_zones WHERE name = "Primera Línea"').fetchone()[0]

    furniture_data = []
    num = 1
    for row in range(4):
        for col in range(5):
            x = 50 + (col * 100)   # Start at x=50, 100px horizontal spacing
            y = 50 + (row * 80)    # Start at y=50, 80px vertical spacing
            furniture_data.append((
                f'H{num}',         # number
                primera_linea_id,  # zone_id
                'hamaca',          # furniture_type
                2,                 # capacity
                x,                 # position_x
                y,                 # position_y
                0,                 # rotation
                60,                # width
                40,                # height
                'primera_linea'    # features
            ))
            num += 1

    for number, zone_id, furn_type, capacity, x, y, rotation, width, height, features in furniture_data:
        db.execute('''
            INSERT INTO beach_furniture
            (number, zone_id, furniture_type, capacity, position_x, position_y, rotation, width, height, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (number, zone_id, furn_type, capacity, x, y, rotation, width, height, features))

    # 10. Create Reservation States (5 core states with full properties)
    # (code, name, color, icon, is_releasing, display_order, priority, incident, system, default)
    states_data = [
        ('confirmada', 'Confirmada', '#28A745', 'fa-check-circle', 0, 1, 3, 0, 1, 1),
        ('sentada', 'Sentada', '#2E8B57', 'fa-couch', 0, 2, 6, 0, 1, 0),
        ('cancelada', 'Cancelada', '#DC3545', 'fa-times-circle', 1, 3, 0, 0, 1, 0),
        ('noshow', 'No-Show', '#FF4444', 'fa-user-times', 1, 4, 0, 1, 1, 0),
        ('liberada', 'Liberada', '#6C757D', 'fa-unlock', 1, 5, 0, 0, 1, 0),
    ]

    for code, name, color, icon, is_releasing, display_order, priority, incident, is_system, is_default in states_data:
        db.execute('''
            INSERT INTO beach_reservation_states
            (code, name, color, icon, is_availability_releasing, display_order,
             display_priority, creates_incident, is_system, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, color, icon, is_releasing, display_order, priority, incident, is_system, is_default))

    # 11. Create Características
    characteristics_data = [
        ('primera_linea', 'Primera Linea', 'Mobiliario en primera linea de playa', 'fa-water', '#1A3A5C'),
        ('sombra', 'Sombra', 'Zona con sombra', 'fa-umbrella', '#4A7C59'),
        ('cerca_mar', 'Cerca del Mar', 'Lo mas cerca posible del mar', 'fa-anchor', '#1A3A5C'),
        ('tranquila', 'Zona Tranquila', 'Zona alejada y tranquila', 'fa-volume-off', '#6B7280'),
        ('vip', 'VIP', 'Zona premium', 'fa-star', '#D4AF37'),
        ('cerca_bar', 'Cerca del Bar', 'Cerca del bar o zona de servicio', 'fa-martini-glass', '#C1444F'),
        ('familia', 'Zona Familiar', 'Zona adecuada para familias', 'fa-children', '#E5A33D'),
        ('accesible', 'Acceso Facil', 'Acceso facil para movilidad reducida', 'fa-wheelchair', '#4A7C59'),
    ]

    for idx, (code, name, description, icon, color) in enumerate(characteristics_data):
        db.execute('''
            INSERT INTO beach_characteristics (code, name, description, icon, color, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, description, icon, color, idx))

    # 12. Create Default Configuration
    config_data = [
        ('opening_time', '09:00', 'Hora de apertura del beach club'),
        ('closing_time', '19:00', 'Hora de cierre del beach club'),
        ('advance_booking_days', '30', 'Días de antelación para reservas'),
        ('max_party_size', '8', 'Tamaño máximo de grupo'),
        ('allow_overbooking', 'false', 'Permitir sobrerreservas'),
        ('cancellation_hours', '24', 'Horas mínimas para cancelación gratuita'),
        ('default_reservation_state', 'pendiente', 'Estado por defecto de nuevas reservas'),
        ('season_current', '2025_verano', 'Temporada actual'),
        # Map configuration
        ('map_default_width', '1200', 'Ancho por defecto del mapa en píxeles'),
        ('map_min_height', '800', 'Altura mínima del mapa en píxeles'),
        ('map_zone_padding', '20', 'Espacio entre zonas en píxeles'),
        ('map_zone_height', '200', 'Altura por defecto de zona en píxeles'),
        ('map_auto_refresh_ms', '30000', 'Intervalo de auto-refresco en milisegundos'),
        ('map_min_zoom', '0.1', 'Zoom mínimo del mapa'),
        ('map_max_zoom', '3', 'Zoom máximo del mapa'),
        ('map_snap_grid', '10', 'Tamaño de rejilla para ajuste en píxeles'),
    ]

    for key, value, description in config_data:
        db.execute('''
            INSERT INTO beach_config (key, value, description)
            VALUES (?, ?, ?)
        ''', (key, value, description))
