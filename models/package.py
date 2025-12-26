"""
Package data access functions.
Handles CRUD operations for beach_packages table.
"""

from database import get_db
from datetime import datetime
from typing import Optional, List, Dict, Tuple


# =============================================================================
# QUERY OPERATIONS
# =============================================================================

def get_all_packages(
    active_only: bool = True,
    customer_type: Optional[str] = None,
    zone_id: Optional[int] = None
) -> List[Dict]:
    """
    Get all packages with optional filtering.

    Args:
        active_only: If True, only return active packages
        customer_type: Filter by customer type ('interno', 'externo', 'both')
        zone_id: Filter by zone ID

    Returns:
        List of package dicts with zone information
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT p.*,
               z.name as zone_name
        FROM beach_packages p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE 1=1
    '''

    params = []

    if active_only:
        query += ' AND p.active = 1'

    if customer_type:
        query += ' AND (p.customer_type = ? OR p.customer_type = "both")'
        params.append(customer_type)

    if zone_id:
        query += ' AND (p.zone_id = ? OR p.zone_id IS NULL)'
        params.append(zone_id)

    query += ' ORDER BY p.display_order ASC, p.package_name ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_package_by_id(package_id: int) -> Optional[Dict]:
    """
    Get a single package by ID.

    Args:
        package_id: Package ID

    Returns:
        Package dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT p.*,
               z.name as zone_name
        FROM beach_packages p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE p.id = ?
    ''', (package_id,))

    row = cursor.fetchone()
    return dict(row) if row else None


def get_applicable_packages(
    customer_type: str,
    zone_id: Optional[int] = None,
    reservation_date: Optional[str] = None,
    num_people: Optional[int] = None
) -> List[Dict]:
    """
    Get packages applicable for given criteria.

    Args:
        customer_type: 'interno' or 'externo'
        zone_id: Optional zone restriction
        reservation_date: Optional date to check validity (YYYY-MM-DD)
        num_people: Optional number of people for capacity filtering

    Returns:
        List of applicable package dicts
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT p.*,
               z.name as zone_name
        FROM beach_packages p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE p.active = 1
          AND (p.customer_type = ? OR p.customer_type = 'both')
    '''

    params = [customer_type]

    # Zone filter
    if zone_id:
        query += ' AND (p.zone_id = ? OR p.zone_id IS NULL)'
        params.append(zone_id)
    else:
        query += ' AND p.zone_id IS NULL'

    # Date validity filter
    if reservation_date:
        query += '''
            AND (
                (p.valid_from IS NULL OR p.valid_from <= ?)
                AND
                (p.valid_until IS NULL OR p.valid_until >= ?)
            )
        '''
        params.extend([reservation_date, reservation_date])

    # Capacity filter (at SQL level for min/max, client can check standard)
    if num_people:
        query += ' AND ? BETWEEN p.min_people AND p.max_people'
        params.append(num_people)

    query += ' ORDER BY p.display_order ASC, p.package_name ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_package_capacity(package_id: int, num_people: int) -> Tuple[bool, str]:
    """
    Validate if num_people fits package capacity.

    Args:
        package_id: Package ID
        num_people: Number of people

    Returns:
        (is_valid, error_message)
    """
    package = get_package_by_id(package_id)

    if not package:
        return False, "Paquete no encontrado"

    if num_people < package['min_people']:
        return False, f"Mínimo {package['min_people']} personas para este paquete"

    if num_people > package['max_people']:
        return False, f"Máximo {package['max_people']} personas para este paquete"

    # Warning if outside standard range (not an error, just info)
    if num_people != package['standard_people']:
        warning = f"Nota: Capacidad estándar es {package['standard_people']} personas"
        return True, warning

    return True, ""


def validate_package_data(data: Dict) -> Tuple[bool, str]:
    """
    Validate package data before create/update.

    Args:
        data: Package data dict

    Returns:
        (is_valid, error_message)
    """
    # Required fields
    if not data.get('package_name'):
        return False, "Nombre del paquete es requerido"

    if not data.get('base_price') or float(data['base_price']) <= 0:
        return False, "Precio base debe ser mayor a 0"

    if data.get('price_type') not in ['per_package', 'per_person']:
        return False, "Tipo de precio debe ser 'per_package' o 'per_person'"

    # Capacity validation
    try:
        min_people = int(data.get('min_people', 1))
        standard_people = int(data.get('standard_people', 2))
        max_people = int(data.get('max_people', 4))

        if not (min_people <= standard_people <= max_people):
            return False, "Debe cumplirse: Mínimo ≤ Estándar ≤ Máximo"

        if min_people < 1:
            return False, "Mínimo de personas debe ser al menos 1"

    except (ValueError, TypeError):
        return False, "Valores de capacidad inválidos"

    # Customer type validation
    if data.get('customer_type') and data['customer_type'] not in ['interno', 'externo', 'both']:
        return False, "Tipo de cliente debe ser 'interno', 'externo' o 'both'"

    # Date validation
    if data.get('valid_from') and data.get('valid_until'):
        try:
            from_date = datetime.strptime(data['valid_from'], '%Y-%m-%d')
            until_date = datetime.strptime(data['valid_until'], '%Y-%m-%d')

            if from_date > until_date:
                return False, "Fecha 'Válido Desde' debe ser anterior a 'Válido Hasta'"
        except ValueError:
            return False, "Formato de fecha inválido (use YYYY-MM-DD)"

    return True, ""


# =============================================================================
# CREATE
# =============================================================================

def create_package(data: Dict) -> Tuple[bool, int, str]:
    """
    Create a new package.

    Args:
        data: Package data dict with keys:
            - package_name (required)
            - package_description
            - base_price (required)
            - price_type (required): 'per_package' or 'per_person'
            - min_people (default: 1)
            - standard_people (default: 2)
            - max_people (default: 4)
            - furniture_types_included
            - customer_type: 'interno', 'externo', or 'both'
            - zone_id
            - valid_from (YYYY-MM-DD)
            - valid_until (YYYY-MM-DD)
            - active (default: 1)
            - display_order (default: 0)

    Returns:
        (success, package_id, message)
    """
    # Validate data
    is_valid, error_msg = validate_package_data(data)
    if not is_valid:
        return False, 0, error_msg

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            INSERT INTO beach_packages (
                package_name, package_description, base_price, price_type,
                min_people, standard_people, max_people,
                furniture_types_included, customer_type, zone_id,
                valid_from, valid_until, active, display_order,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            data['package_name'],
            data.get('package_description'),
            data['base_price'],
            data['price_type'],
            data.get('min_people', 1),
            data.get('standard_people', 2),
            data.get('max_people', 4),
            data.get('furniture_types_included'),
            data.get('customer_type'),
            data.get('zone_id'),
            data.get('valid_from'),
            data.get('valid_until'),
            data.get('active', 1),
            data.get('display_order', 0)
        ))

        package_id = cursor.lastrowid
        db.commit()

        return True, package_id, "Paquete creado exitosamente"

    except Exception as e:
        db.rollback()
        return False, 0, f"Error al crear paquete: {str(e)}"


# =============================================================================
# UPDATE
# =============================================================================

def update_package(package_id: int, data: Dict) -> Tuple[bool, str]:
    """
    Update an existing package.

    Args:
        package_id: Package ID to update
        data: Package data dict (same fields as create_package)

    Returns:
        (success, message)
    """
    # Check if package exists
    existing = get_package_by_id(package_id)
    if not existing:
        return False, "Paquete no encontrado"

    # Validate data
    is_valid, error_msg = validate_package_data(data)
    if not is_valid:
        return False, error_msg

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            UPDATE beach_packages
            SET package_name = ?,
                package_description = ?,
                base_price = ?,
                price_type = ?,
                min_people = ?,
                standard_people = ?,
                max_people = ?,
                furniture_types_included = ?,
                customer_type = ?,
                zone_id = ?,
                valid_from = ?,
                valid_until = ?,
                active = ?,
                display_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data['package_name'],
            data.get('package_description'),
            data['base_price'],
            data['price_type'],
            data.get('min_people', 1),
            data.get('standard_people', 2),
            data.get('max_people', 4),
            data.get('furniture_types_included'),
            data.get('customer_type'),
            data.get('zone_id'),
            data.get('valid_from'),
            data.get('valid_until'),
            data.get('active', 1),
            data.get('display_order', 0),
            package_id
        ))

        db.commit()
        return True, "Paquete actualizado exitosamente"

    except Exception as e:
        db.rollback()
        return False, f"Error al actualizar paquete: {str(e)}"


def toggle_package_active(package_id: int) -> Tuple[bool, str]:
    """
    Toggle package active status.

    Args:
        package_id: Package ID

    Returns:
        (success, message)
    """
    package = get_package_by_id(package_id)
    if not package:
        return False, "Paquete no encontrado"

    db = get_db()
    cursor = db.cursor()

    new_status = 0 if package['active'] == 1 else 1

    try:
        cursor.execute('''
            UPDATE beach_packages
            SET active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, package_id))

        db.commit()

        status_text = "activado" if new_status == 1 else "desactivado"
        return True, f"Paquete {status_text} exitosamente"

    except Exception as e:
        db.rollback()
        return False, f"Error al cambiar estado: {str(e)}"


# =============================================================================
# DELETE
# =============================================================================

def delete_package(package_id: int) -> Tuple[bool, str]:
    """
    Soft delete a package (set active=0).

    Note: We don't hard delete to preserve reservation history.

    Args:
        package_id: Package ID

    Returns:
        (success, message)
    """
    package = get_package_by_id(package_id)
    if not package:
        return False, "Paquete no encontrado"

    # Check if package is used in any reservations
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_reservations
        WHERE package_id = ?
    ''', (package_id,))

    result = cursor.fetchone()
    if result['count'] > 0:
        # Package is used, just deactivate
        return toggle_package_active(package_id)

    # Package not used, can soft delete
    try:
        cursor.execute('''
            UPDATE beach_packages
            SET active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (package_id,))

        db.commit()
        return True, "Paquete eliminado exitosamente"

    except Exception as e:
        db.rollback()
        return False, f"Error al eliminar paquete: {str(e)}"


# =============================================================================
# PRICE CALCULATION
# =============================================================================

def calculate_package_price(package_id: int, num_people: int) -> Optional[Dict]:
    """
    Calculate price for package with given number of people.

    Args:
        package_id: Package ID
        num_people: Number of people

    Returns:
        Dict with calculation details or None if invalid:
        {
            'base_price': float,
            'price_type': str,
            'num_people': int,
            'total_price': float,
            'price_per_person': float,
            'breakdown': str
        }
    """
    package = get_package_by_id(package_id)
    if not package:
        return None

    base_price = float(package['base_price'])
    price_type = package['price_type']

    if price_type == 'per_person':
        total_price = base_price * num_people
        price_per_person = base_price
        breakdown = f"€{base_price:.2f} × {num_people} personas = €{total_price:.2f}"
    else:  # per_package
        total_price = base_price
        price_per_person = base_price / num_people if num_people > 0 else 0
        breakdown = f"€{base_price:.2f} (precio fijo por paquete)"

    return {
        'package_id': package_id,
        'package_name': package['package_name'],
        'base_price': base_price,
        'price_type': price_type,
        'num_people': num_people,
        'total_price': total_price,
        'price_per_person': price_per_person,
        'breakdown': breakdown,
        'min_people': package['min_people'],
        'standard_people': package['standard_people'],
        'max_people': package['max_people']
    }


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Query
    'get_all_packages',
    'get_package_by_id',
    'get_applicable_packages',

    # Validation
    'validate_package_capacity',
    'validate_package_data',

    # Create/Update/Delete
    'create_package',
    'update_package',
    'toggle_package_active',
    'delete_package',

    # Calculation
    'calculate_package_price',
]
