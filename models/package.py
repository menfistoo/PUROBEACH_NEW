"""
Beach package data access functions.

Handles package CRUD operations for configuration UI.
Provides functions for package management and queries.
"""

from database import get_db


def get_all_packages(active_only: bool = True) -> list:
    """
    Get all packages.

    Args:
        active_only: If True, return only active packages

    Returns:
        List of package dictionaries ordered by display_order
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT p.*,
                   (SELECT COUNT(*) FROM beach_reservations
                    WHERE package_id = p.id) as usage_count
            FROM beach_packages p
        '''

        if active_only:
            query += ' WHERE p.active = 1'

        query += ' ORDER BY p.display_order, p.package_name'

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def get_package_by_id(package_id: int) -> dict:
    """
    Get package by ID.

    Args:
        package_id: Package ID

    Returns:
        Package dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_packages WHERE id = ?', (package_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_package_by_name(name: str) -> dict:
    """
    Get package by name.

    Args:
        name: Package name

    Returns:
        Package dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM beach_packages WHERE package_name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_packages_by_zone(zone_id: int, active_only: bool = True) -> list:
    """
    Get packages for a specific zone.

    Args:
        zone_id: Zone ID (None for all zones)
        active_only: If True, return only active packages

    Returns:
        List of package dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM beach_packages WHERE (zone_id = ? OR zone_id IS NULL)'

        if active_only:
            query += ' AND active = 1'

        query += ' ORDER BY display_order, package_name'

        cursor.execute(query, (zone_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_packages_by_customer_type(customer_type: str, active_only: bool = True) -> list:
    """
    Get packages for a specific customer type.

    Args:
        customer_type: 'interno', 'externo', or None for all
        active_only: If True, return only active packages

    Returns:
        List of package dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT * FROM beach_packages
            WHERE (customer_type = ? OR customer_type = 'both' OR customer_type IS NULL)
        '''

        if active_only:
            query += ' AND active = 1'

        query += ' ORDER BY display_order, package_name'

        cursor.execute(query, (customer_type,))
        return [dict(row) for row in cursor.fetchall()]


def get_active_packages_for_date(date: str, customer_type: str = None, zone_id: int = None) -> list:
    """
    Get packages valid for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        customer_type: Optional customer type filter
        zone_id: Optional zone filter

    Returns:
        List of active package dictionaries valid for the date
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT * FROM beach_packages
            WHERE active = 1
            AND (valid_from IS NULL OR valid_from <= ?)
            AND (valid_until IS NULL OR valid_until >= ?)
        '''

        params = [date, date]

        if customer_type:
            query += ' AND (customer_type = ? OR customer_type = \'both\' OR customer_type IS NULL)'
            params.append(customer_type)

        if zone_id:
            query += ' AND (zone_id = ? OR zone_id IS NULL)'
            params.append(zone_id)

        query += ' ORDER BY display_order, package_name'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def create_package(package_name: str, base_price: float, price_type: str, **kwargs) -> int:
    """
    Create new package.

    Args:
        package_name: Package name (required)
        base_price: Base price (required, must be > 0)
        price_type: 'per_package' or 'per_person' (required)
        **kwargs: Optional fields (package_description, min_people, standard_people,
                  max_people, furniture_types_included, customer_type, zone_id,
                  valid_from, valid_until, active, display_order)

    Returns:
        New package ID

    Raises:
        ValueError: If validation fails
    """
    # Validate required fields
    if not package_name or not package_name.strip():
        raise ValueError("Package name is required")

    if base_price <= 0:
        raise ValueError("Base price must be greater than 0")

    if price_type not in ('per_package', 'per_person'):
        raise ValueError("Price type must be 'per_package' or 'per_person'")

    # Validate people range
    min_people = kwargs.get('min_people', 1)
    standard_people = kwargs.get('standard_people', 2)
    max_people = kwargs.get('max_people', 4)

    if not (min_people <= standard_people <= max_people):
        raise ValueError("Invalid people range: min <= standard <= max")

    # Validate customer type
    customer_type = kwargs.get('customer_type')
    if customer_type and customer_type not in ('interno', 'externo', 'both'):
        raise ValueError("Customer type must be 'interno', 'externo', or 'both'")

    # Check for duplicate name
    if get_package_by_name(package_name):
        raise ValueError(f"Package with name '{package_name}' already exists")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO beach_packages (
                package_name, package_description, base_price, price_type,
                min_people, standard_people, max_people, furniture_types_included,
                customer_type, zone_id, valid_from, valid_until,
                active, display_order, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            package_name.strip(),
            kwargs.get('package_description', '').strip() or None,
            base_price,
            price_type,
            min_people,
            standard_people,
            max_people,
            kwargs.get('furniture_types_included'),
            customer_type,
            kwargs.get('zone_id'),
            kwargs.get('valid_from'),
            kwargs.get('valid_until'),
            kwargs.get('active', 1),
            kwargs.get('display_order', 0)
        ))

        conn.commit()
        return cursor.lastrowid


def update_package(package_id: int, **kwargs) -> bool:
    """
    Update existing package.

    Args:
        package_id: Package ID
        **kwargs: Fields to update

    Returns:
        True if successful

    Raises:
        ValueError: If package not found or validation fails
    """
    package = get_package_by_id(package_id)
    if not package:
        raise ValueError(f"Package with ID {package_id} not found")

    # Validate fields if provided
    if 'package_name' in kwargs:
        name = kwargs['package_name']
        if not name or not name.strip():
            raise ValueError("Package name cannot be empty")

        # Check for duplicate (exclude current package)
        existing = get_package_by_name(name.strip())
        if existing and existing['id'] != package_id:
            raise ValueError(f"Package with name '{name}' already exists")

    if 'base_price' in kwargs and kwargs['base_price'] <= 0:
        raise ValueError("Base price must be greater than 0")

    if 'price_type' in kwargs and kwargs['price_type'] not in ('per_package', 'per_person'):
        raise ValueError("Price type must be 'per_package' or 'per_person'")

    if 'customer_type' in kwargs:
        ct = kwargs['customer_type']
        if ct and ct not in ('interno', 'externo', 'both'):
            raise ValueError("Customer type must be 'interno', 'externo', or 'both'")

    # Validate people range if any of these fields are updated
    min_people = kwargs.get('min_people', package['min_people'])
    standard_people = kwargs.get('standard_people', package['standard_people'])
    max_people = kwargs.get('max_people', package['max_people'])

    if not (min_people <= standard_people <= max_people):
        raise ValueError("Invalid people range: min <= standard <= max")

    # Build dynamic UPDATE query
    allowed_fields = [
        'package_name', 'package_description', 'base_price', 'price_type',
        'min_people', 'standard_people', 'max_people', 'furniture_types_included',
        'customer_type', 'zone_id', 'valid_from', 'valid_until', 'active', 'display_order'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            value = kwargs[field]
            # Strip string fields
            if field in ('package_name', 'package_description') and value:
                value = value.strip() or None
            values.append(value)

    if not updates:
        return True  # Nothing to update

    # Always update updated_at
    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(package_id)

    with get_db() as conn:
        cursor = conn.cursor()

        query = f'UPDATE beach_packages SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, values)
        conn.commit()

        return True


def delete_package(package_id: int) -> bool:
    """
    Soft delete package (set active = 0).

    Args:
        package_id: Package ID

    Returns:
        True if successful

    Raises:
        ValueError: If package not found
    """
    package = get_package_by_id(package_id)
    if not package:
        raise ValueError(f"Package with ID {package_id} not found")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE beach_packages
            SET active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (package_id,))

        conn.commit()
        return True


def reorder_packages(package_ids: list) -> bool:
    """
    Update display_order for packages based on provided order.

    Args:
        package_ids: List of package IDs in desired order

    Returns:
        True if successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        for idx, package_id in enumerate(package_ids):
            cursor.execute('''
                UPDATE beach_packages
                SET display_order = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (idx, package_id))

        conn.commit()
        return True
