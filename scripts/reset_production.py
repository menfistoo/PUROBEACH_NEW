#!/usr/bin/env python3
"""
Production Reset Script.

Cleans operational data (reservations, customers) while preserving
infrastructure configuration (furniture, zones, states, users).

Usage:
    python scripts/reset_production.py [options]

Options:
    --all           Reset everything including furniture to 20 standard hamacas
    --keep-furniture Keep current furniture layout (default)
    --dry-run       Show what would be deleted without executing
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.connection import get_db

# Create Flask app for database context
_app = create_app()


def count_records(db):
    """Count records in operational tables."""
    counts = {}

    tables = [
        ('beach_reservations', 'Reservas'),
        ('beach_reservation_furniture', 'Asignaciones mobiliario'),
        ('beach_reservation_daily_states', 'Estados diarios'),
        ('beach_reservation_tags', 'Tags de reservas'),
        ('beach_reservation_characteristics', 'Características de reservas'),
        ('beach_customers', 'Clientes'),
        ('beach_customer_tags', 'Tags de clientes'),
        ('beach_customer_preferences', 'Preferencias de clientes'),
        ('beach_customer_characteristics', 'Características de clientes'),
        ('beach_waitlist', 'Lista de espera'),
        ('hotel_guests', 'Huéspedes hotel'),
        ('reservation_status_history', 'Historial de estados'),
        ('audit_log', 'Log de auditoría'),
    ]

    for table, display_name in tables:
        try:
            count = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            counts[display_name] = count
        except Exception:
            counts[display_name] = 0

    return counts


def clear_operational_data(db, dry_run=False):
    """
    Clear all operational data (reservations, customers, waitlist).
    Preserves infrastructure (furniture, zones, states, users).
    """
    if dry_run:
        print("\n[DRY RUN] Los siguientes registros serían eliminados:\n")
        counts = count_records(db)
        for name, count in counts.items():
            if count > 0:
                print(f"  • {name}: {count} registros")
        return True

    print("\nEliminando datos operacionales...")

    # Order matters due to foreign key constraints
    # Delete in reverse dependency order

    # 1. Reservation-related tables (CASCADE should handle most)
    db.execute('DELETE FROM reservation_status_history')
    db.execute('DELETE FROM beach_reservation_characteristics')
    db.execute('DELETE FROM beach_reservation_tags')
    db.execute('DELETE FROM beach_reservation_daily_states')
    db.execute('DELETE FROM beach_reservation_furniture')
    db.execute('DELETE FROM beach_reservations')
    print("  [OK] Reservas eliminadas")

    # 2. Waitlist (references customers and reservations)
    db.execute('DELETE FROM beach_waitlist')
    print("  [OK] Lista de espera eliminada")

    # 3. Customer-related tables
    db.execute('DELETE FROM beach_customer_characteristics')
    db.execute('DELETE FROM beach_customer_preferences')
    db.execute('DELETE FROM beach_customer_tags')
    db.execute('DELETE FROM beach_customers')
    print("  [OK] Clientes eliminados")

    # 4. Hotel guests
    db.execute('DELETE FROM hotel_guests')
    print("  [OK] Huéspedes hotel eliminados")

    # 5. Audit log (optional - keep for debugging)
    db.execute('DELETE FROM audit_log')
    print("  [OK] Log de auditoría limpiado")

    return True


def reset_furniture_to_standard(db, dry_run=False):
    """
    Reset furniture to 20 standard hamacas in zone 1.
    This is the new production standard.
    """
    if dry_run:
        current = db.execute('SELECT COUNT(*) FROM beach_furniture').fetchone()[0]
        print(f"\n[DRY RUN] Mobiliario actual: {current} items")
        print("[DRY RUN] Se crearían 20 hamacas estándar en Primera Línea")
        return True

    print("\nReseteando mobiliario a 20 hamacas estándar...")

    # Clear existing furniture and related tables
    db.execute('DELETE FROM beach_furniture_characteristics')
    db.execute('DELETE FROM beach_furniture_daily_positions')
    db.execute('DELETE FROM beach_furniture_blocks')
    db.execute('DELETE FROM beach_furniture')
    print("  [OK] Mobiliario anterior eliminado")

    # Get zone 1 (Primera Línea) ID
    zone = db.execute('SELECT id FROM beach_zones WHERE display_order = 1').fetchone()
    if not zone:
        print("  [ERROR] Error: No se encontró la zona 'Primera Línea'")
        return False

    zone_id = zone[0]

    # Create 20 standard hamacas in a grid layout
    # Layout: 4 rows x 5 columns, spacing 100x80 pixels
    hamacas = []
    num = 1
    for row in range(4):
        for col in range(5):
            x = 50 + (col * 100)  # Start at x=50, 100px spacing
            y = 50 + (row * 80)   # Start at y=50, 80px spacing
            hamacas.append((
                f'H{num}',        # number
                zone_id,          # zone_id
                'hamaca',         # furniture_type
                2,                # capacity
                x,                # position_x
                y,                # position_y
                0,                # rotation
                60,               # width
                40,               # height
                'primera_linea'   # features
            ))
            num += 1

    # Insert all 20 hamacas
    db.executemany('''
        INSERT INTO beach_furniture
        (number, zone_id, furniture_type, capacity, position_x, position_y, rotation, width, height, features)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', hamacas)

    print(f"  [OK] {len(hamacas)} hamacas estándar creadas en Primera Línea")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Reset de datos de producción para PuroBeach',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos:
  python scripts/reset_production.py              # Limpia reservas y clientes
  python scripts/reset_production.py --all        # Reset completo con 20 hamacas
  python scripts/reset_production.py --dry-run    # Ver qué se eliminaría
        '''
    )
    parser.add_argument('--all', action='store_true',
                        help='Reset completo incluyendo mobiliario a 20 hamacas estándar')
    parser.add_argument('--keep-furniture', action='store_true', default=True,
                        help='Mantener layout actual de mobiliario (por defecto)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostrar qué se eliminaría sin ejecutar')
    parser.add_argument('--force', '-f', action='store_true',
                        help='No pedir confirmación')

    args = parser.parse_args()

    # If --all is specified, don't keep furniture
    if args.all:
        args.keep_furniture = False

    print("=" * 60)
    print("  PUROBEACH - Reset de Producción")
    print("=" * 60)

    with _app.app_context():
        with get_db() as db:
            # Show current state
            counts = count_records(db)
            print("\nEstado actual:")
            total = 0
            for name, count in counts.items():
                if count > 0:
                    print(f"  • {name}: {count}")
                    total += count

            if total == 0:
                print("  (Sin datos operacionales)")

            furniture_count = db.execute('SELECT COUNT(*) FROM beach_furniture').fetchone()[0]
            print(f"\n  • Mobiliario: {furniture_count} items")

            # Confirm unless --force or --dry-run
            if not args.dry_run and not args.force:
                print("\n" + "=" * 60)
                if args.all:
                    print("ADVERTENCIA: Esto eliminará TODOS los datos operacionales")
                    print("             y reseteará el mobiliario a 20 hamacas estándar.")
                else:
                    print("ADVERTENCIA: Esto eliminará reservas, clientes y lista de espera.")
                    print("             El mobiliario se mantendrá.")
                print("=" * 60)

                response = input("\n¿Continuar? (escribe 'SI' para confirmar): ")
                if response.strip().upper() != 'SI':
                    print("\nOperación cancelada.")
                    return 1

            # Execute reset
            try:
                db.execute('BEGIN IMMEDIATE')

                # Clear operational data
                if not clear_operational_data(db, args.dry_run):
                    db.execute('ROLLBACK')
                    return 1

                # Reset furniture if requested
                if args.all:
                    if not reset_furniture_to_standard(db, args.dry_run):
                        db.execute('ROLLBACK')
                        return 1

                if not args.dry_run:
                    db.execute('COMMIT')
                    print("\n" + "=" * 60)
                    print("  [OK] Reset completado exitosamente")
                    print("=" * 60)
                else:
                    db.execute('ROLLBACK')
                    print("\n[DRY RUN] No se realizaron cambios.")

                return 0

            except Exception as e:
                db.execute('ROLLBACK')
                print(f"\n[ERROR] Error durante el reset: {e}")
                return 1


if __name__ == '__main__':
    sys.exit(main())
