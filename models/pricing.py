"""
Pricing data access functions.
Handles price catalog and minimum consumption policies.
"""

from database import get_db


# =============================================================================
# MINIMUM CONSUMPTION POLICIES - CRUD OPERATIONS
# =============================================================================

def get_all_minimum_consumption_policies(active_only: bool = True) -> list:
    """
    Get all minimum consumption policies.

    Args:
        active_only: If True, return only active policies

    Returns:
        List of policy dictionaries ordered by priority_order
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = '''
            SELECT p.*,
                   (SELECT COUNT(*) FROM beach_reservations
                    WHERE minimum_consumption_policy_id = p.id) as usage_count
            FROM beach_minimum_consumption_policies p
        '''

        if active_only:
            query += ' WHERE p.is_active = 1'

        query += ' ORDER BY p.priority_order DESC, p.policy_name'

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def get_minimum_consumption_policy_by_id(policy_id: int) -> dict:
    """
    Get minimum consumption policy by ID.

    Args:
        policy_id: Policy ID

    Returns:
        Policy dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM beach_minimum_consumption_policies WHERE id = ?
        ''', (policy_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_minimum_consumption_policy_by_name(name: str, active_only: bool = True) -> dict:
    """
    Get minimum consumption policy by name.

    Args:
        name: Policy name
        active_only: If True, only search active policies (default True)

    Returns:
        Policy dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM beach_minimum_consumption_policies WHERE policy_name = ?'
        if active_only:
            query += ' AND is_active = 1'
        cursor.execute(query, (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_applicable_minimum_consumption_policy(
    furniture_type: str = None,
    customer_type: str = None,
    zone_id: int = None
) -> dict:
    """
    Get the most applicable minimum consumption policy based on priority matching.

    Priority order (highest to lowest):
    1. Exact match: furniture_type + customer_type + zone
    2. furniture_type + customer_type
    3. furniture_type + zone
    4. customer_type + zone
    5. furniture_type only
    6. customer_type only
    7. zone only
    8. Default (all NULL)

    Args:
        furniture_type: Furniture type code (optional)
        customer_type: Customer type ('interno'/'externo', optional)
        zone_id: Zone ID (optional)

    Returns:
        Most specific matching policy dictionary or None
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query with priority-based ordering
        query = '''
            SELECT *,
                   CASE
                       WHEN furniture_type IS NOT NULL AND customer_type IS NOT NULL AND zone_id IS NOT NULL THEN 7
                       WHEN furniture_type IS NOT NULL AND customer_type IS NOT NULL THEN 6
                       WHEN furniture_type IS NOT NULL AND zone_id IS NOT NULL THEN 5
                       WHEN customer_type IS NOT NULL AND zone_id IS NOT NULL THEN 4
                       WHEN furniture_type IS NOT NULL THEN 3
                       WHEN customer_type IS NOT NULL THEN 2
                       WHEN zone_id IS NOT NULL THEN 1
                       ELSE 0
                   END as match_priority
            FROM beach_minimum_consumption_policies
            WHERE is_active = 1
            AND (furniture_type = ? OR furniture_type IS NULL)
            AND (customer_type = ? OR customer_type IS NULL)
            AND (zone_id = ? OR zone_id IS NULL)
            ORDER BY match_priority DESC, priority_order DESC
            LIMIT 1
        '''

        cursor.execute(query, (furniture_type, customer_type, zone_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_minimum_consumption_policy(
    policy_name: str,
    minimum_amount: float,
    **kwargs
) -> int:
    """
    Create new minimum consumption policy.

    Args:
        policy_name: Policy name (required)
        minimum_amount: Minimum consumption amount (required, must be > 0)
        **kwargs: Optional fields (policy_description, calculation_type,
                  furniture_type, customer_type, zone_id, priority_order, is_active)

    Returns:
        New policy ID

    Raises:
        ValueError: If validation fails
    """
    # Validate required fields
    if not policy_name or not policy_name.strip():
        raise ValueError("Policy name is required")

    if minimum_amount < 0:
        raise ValueError("Minimum amount cannot be negative")

    # Validate calculation_type
    calculation_type = kwargs.get('calculation_type', 'per_reservation')
    if calculation_type not in ('per_reservation', 'per_person'):
        raise ValueError("Calculation type must be 'per_reservation' or 'per_person'")

    # Validate customer_type
    customer_type = kwargs.get('customer_type')
    if customer_type and customer_type not in ('interno', 'externo'):
        raise ValueError("Customer type must be 'interno' or 'externo'")

    # Check for duplicate name
    if get_minimum_consumption_policy_by_name(policy_name):
        raise ValueError(f"Policy with name '{policy_name}' already exists")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO beach_minimum_consumption_policies (
                policy_name, policy_description, minimum_amount, calculation_type,
                furniture_type, customer_type, zone_id, priority_order, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            policy_name.strip(),
            kwargs.get('policy_description', '').strip() or None,
            minimum_amount,
            calculation_type,
            kwargs.get('furniture_type'),
            customer_type,
            kwargs.get('zone_id'),
            kwargs.get('priority_order', 0),
            kwargs.get('is_active', 1)
        ))

        conn.commit()
        return cursor.lastrowid


def update_minimum_consumption_policy(policy_id: int, **kwargs) -> bool:
    """
    Update existing minimum consumption policy.

    Args:
        policy_id: Policy ID
        **kwargs: Fields to update

    Returns:
        True if successful

    Raises:
        ValueError: If policy not found or validation fails
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy:
        raise ValueError(f"Policy with ID {policy_id} not found")

    # Validate fields if provided
    if 'policy_name' in kwargs:
        name = kwargs['policy_name']
        if not name or not name.strip():
            raise ValueError("Policy name cannot be empty")

        # Check for duplicate (exclude current policy)
        existing = get_minimum_consumption_policy_by_name(name.strip())
        if existing and existing['id'] != policy_id:
            raise ValueError(f"Policy with name '{name}' already exists")

    if 'minimum_amount' in kwargs and kwargs['minimum_amount'] < 0:
        raise ValueError("Minimum amount cannot be negative")

    if 'calculation_type' in kwargs:
        ct = kwargs['calculation_type']
        if ct not in ('per_reservation', 'per_person'):
            raise ValueError("Calculation type must be 'per_reservation' or 'per_person'")

    if 'customer_type' in kwargs:
        ct = kwargs['customer_type']
        if ct and ct not in ('interno', 'externo'):
            raise ValueError("Customer type must be 'interno' or 'externo'")

    # Build dynamic UPDATE query
    allowed_fields = [
        'policy_name', 'policy_description', 'minimum_amount', 'calculation_type',
        'furniture_type', 'customer_type', 'zone_id', 'priority_order', 'is_active'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            value = kwargs[field]
            # Strip string fields
            if field in ('policy_name', 'policy_description') and value:
                value = value.strip() or None
            values.append(value)

    if not updates:
        return True  # Nothing to update

    values.append(policy_id)

    with get_db() as conn:
        cursor = conn.cursor()

        query = f'UPDATE beach_minimum_consumption_policies SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, values)
        conn.commit()

        return True


def delete_minimum_consumption_policy(policy_id: int) -> bool:
    """
    Soft delete minimum consumption policy (set is_active = 0).

    Args:
        policy_id: Policy ID

    Returns:
        True if successful

    Raises:
        ValueError: If policy not found
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy:
        raise ValueError(f"Policy with ID {policy_id} not found")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE beach_minimum_consumption_policies
            SET is_active = 0
            WHERE id = ?
        ''', (policy_id,))

        conn.commit()
        return True


def reorder_minimum_consumption_policies(policy_ids: list) -> bool:
    """
    Update priority_order for policies based on provided order.

    Args:
        policy_ids: List of policy IDs in desired priority order (highest first)

    Returns:
        True if successful
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Reverse enumerate to get higher priority for first items
        for idx, policy_id in enumerate(policy_ids):
            priority = len(policy_ids) - idx
            cursor.execute('''
                UPDATE beach_minimum_consumption_policies
                SET priority_order = ?
                WHERE id = ?
            ''', (priority, policy_id))

        conn.commit()
        return True


# =============================================================================
# PRICE CATALOG AND CALCULATION (EXISTING FUNCTIONS)
# =============================================================================


def get_price_catalog() -> list:
    """
    Get all active price catalog entries.

    Returns:
        List of price catalog dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pc.*,
                   z.name as zone_name,
                   ft.display_name as furniture_type_name
            FROM beach_price_catalog pc
            LEFT JOIN beach_zones z ON pc.zone_id = z.id
            LEFT JOIN beach_furniture_types ft ON pc.furniture_type = ft.type_code
            WHERE pc.active = 1
            ORDER BY pc.name
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def calculate_price(furniture_type: str, customer_type: str, zone_id: int, date: str) -> float:
    """
    Calculate price for furniture rental.
    Placeholder - will be implemented in future phases.

    Args:
        furniture_type: Furniture type code
        customer_type: Customer type ('interno'/'externo')
        zone_id: Zone ID
        date: Date for pricing (YYYY-MM-DD)

    Returns:
        Price amount (0.0 for now)
    """
    # TODO: Implement price calculation logic in Phase 8
    # Consider: base_price, weekend_price, holiday_price, date ranges
    return 0.0


def get_minimum_consumption(furniture_type: str, customer_type: str, zone_id: int) -> float:
    """
    Get minimum consumption amount for furniture.
    Placeholder - will be implemented in future phases.

    Args:
        furniture_type: Furniture type code
        customer_type: Customer type ('interno'/'externo')
        zone_id: Zone ID

    Returns:
        Minimum consumption amount (0.0 for now)
    """
    # TODO: Implement minimum consumption lookup in Phase 8
    return 0.0
