#!/usr/bin/env python
"""
Seed sample pricing data for testing.
Adds packages and minimum consumption policies.
"""

from app import create_app
from models.package import create_package
from models.pricing import create_minimum_consumption_policy
from datetime import date, timedelta

def seed_pricing_data():
    """Add sample packages and minimum consumption policies."""

    print("Seeding pricing data...")

    # Get some IDs we'll need
    from database.connection import get_db
    db = get_db()
    cursor = db.cursor()

    # Get first zone ID
    cursor.execute('SELECT id FROM beach_zones LIMIT 1')
    zone_row = cursor.fetchone()
    zone_id = zone_row[0] if zone_row else None

    # Get furniture type IDs
    cursor.execute('SELECT id, display_name FROM beach_furniture_types ORDER BY display_name')
    furniture_types = cursor.fetchall()
    furniture_type_map = {row[1]: row[0] for row in furniture_types}

    # Sample packages
    packages = [
        {
            'package_name': 'Día de Lujo VIP',
            'package_description': 'Experiencia premium con los mejores servicios de playa',
            'customer_type': 'both',
            'zone_id': zone_id,
            'base_price': 150.00,
            'price_type': 'per_package',
            'min_people': 2,
            'standard_people': 2,
            'max_people': 4,
            'furniture_types_included': '''2 Hamacas premium primera línea
Sombrilla privada de lujo
Toallas de playa premium
Champagne de bienvenida
Frutas frescas de temporada
Servicio de camarero dedicado''',
            'valid_from': None,
            'valid_until': None
        },
        {
            'package_name': 'Paquete Familia',
            'package_description': 'Perfecto para familias con niños',
            'customer_type': 'externo',
            'zone_id': None,
            'base_price': 60.00,
            'price_type': 'per_person',
            'min_people': 3,
            'standard_people': 4,
            'max_people': 6,
            'furniture_types_included': '''Hamacas cómodas
Sombrilla familiar
Acceso a zona infantil
Toallas de playa
Bebidas de bienvenida''',
            'valid_from': None,
            'valid_until': None
        },
        {
            'package_name': 'Romántico para Dos',
            'package_description': 'Experiencia íntima para parejas',
            'customer_type': 'both',
            'zone_id': zone_id,
            'base_price': 120.00,
            'price_type': 'per_package',
            'min_people': 2,
            'standard_people': 2,
            'max_people': 2,
            'furniture_types_included': '''Balinesa doble primera línea
Champagne rosé
Frutas con chocolate
Servicio romántico
Toallas premium''',
            'valid_from': None,
            'valid_until': None
        },
        {
            'package_name': 'Paquete Verano 2025',
            'package_description': 'Oferta especial de temporada alta',
            'customer_type': 'interno',
            'zone_id': None,
            'base_price': 40.00,
            'price_type': 'per_person',
            'min_people': 1,
            'standard_people': 2,
            'max_people': 4,
            'furniture_types_included': '''Hamaca estándar
Sombrilla compartida
Toalla de playa
Agua mineral''',
            'valid_from': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'valid_until': (date.today() + timedelta(days=120)).strftime('%Y-%m-%d')
        },
        {
            'package_name': 'Wellness Experience',
            'package_description': 'Bienestar y relajación total',
            'customer_type': 'both',
            'zone_id': zone_id,
            'base_price': 95.00,
            'price_type': 'per_person',
            'min_people': 1,
            'standard_people': 1,
            'max_people': 2,
            'furniture_types_included': '''Hamaca premium zona tranquila
Masaje de 30 minutos
Frutas y zumos detox
Toalla premium
Aceites aromáticos''',
            'valid_from': None,
            'valid_until': None
        }
    ]

    print(f"\nCreating {len(packages)} sample packages...")
    for pkg_data in packages:
        success, package_id, message = create_package(pkg_data)
        if success:
            print(f"  ✓ Created package: {pkg_data['package_name']}")
        else:
            print(f"  ✗ Failed to create package {pkg_data['package_name']}: {message}")

    # Sample minimum consumption policies
    policies = [
        {
            'policy_name': 'Balinesa VIP Externa',
            'policy_description': 'Consumo mínimo para balinesas, clientes externos',
            'furniture_type': furniture_type_map.get('Balinesa'),
            'customer_type': 'externo',
            'zone_id': None,
            'minimum_amount': 100.00,
            'calculation_type': 'per_reservation'
        },
        {
            'policy_name': 'Primera Línea General',
            'policy_description': 'Consumo mínimo para primera línea de playa',
            'furniture_type': None,
            'customer_type': None,
            'zone_id': zone_id,
            'minimum_amount': 30.00,
            'calculation_type': 'per_person'
        },
        {
            'policy_name': 'Hamaca Premium Externa',
            'policy_description': 'Consumo mínimo hamacas premium para externos',
            'furniture_type': furniture_type_map.get('Hamaca Premium'),
            'customer_type': 'externo',
            'zone_id': None,
            'minimum_amount': 50.00,
            'calculation_type': 'per_reservation'
        },
        {
            'policy_name': 'Externos Fin de Semana',
            'policy_description': 'Consumo mínimo general para clientes externos',
            'furniture_type': None,
            'customer_type': 'externo',
            'zone_id': None,
            'minimum_amount': 20.00,
            'calculation_type': 'per_person'
        }
    ]

    print(f"\nCreating {len(policies)} sample minimum consumption policies...")
    for policy_data in policies:
        success, policy_id, message = create_minimum_consumption_policy(policy_data)
        if success:
            print(f"  ✓ Created policy: {policy_data['policy_name']}")
        else:
            print(f"  ✗ Failed to create policy {policy_data['policy_name']}: {message}")

    print("\n✓ Pricing data seeded successfully!")


if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        seed_pricing_data()
