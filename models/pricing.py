"""
Pricing data access functions.
Handles price catalog and minimum consumption policies (stub for future phases).
"""

from database import get_db


def get_price_catalog() -> list:
    """
    Get all active price catalog entries.

    Returns:
        List of price catalog dicts
    """
    db = get_db()
    cursor = db.cursor()
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
    Get minimum consumption amount for furniture (legacy function).

    Args:
        furniture_type: Furniture type code
        customer_type: Customer type ('interno'/'externo')
        zone_id: Zone ID

    Returns:
        Minimum consumption amount
    """
    policy = get_applicable_minimum_consumption_policy(furniture_type, customer_type, zone_id)
    if policy:
        return float(policy['minimum_amount'])
    return 0.0


def get_all_minimum_consumption_policies(active_only: bool = True) -> list:
    """
    Get all minimum consumption policies.

    Args:
        active_only: If True, only return active policies

    Returns:
        List of policy dicts
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT p.*,
               z.name as zone_name
        FROM beach_minimum_consumption_policies p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE 1=1
    '''

    if active_only:
        query += ' AND p.is_active = 1'

    query += ' ORDER BY p.priority_order ASC, p.policy_name ASC'

    cursor.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_minimum_consumption_policy_by_id(policy_id: int) -> dict:
    """
    Get a minimum consumption policy by ID.

    Args:
        policy_id: Policy ID

    Returns:
        Policy dict or None
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT p.*,
               z.name as zone_name
        FROM beach_minimum_consumption_policies p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE p.id = ?
    ''', (policy_id,))

    row = cursor.fetchone()
    return dict(row) if row else None


def get_applicable_minimum_consumption_policy(
    furniture_type: str = None,
    customer_type: str = None,
    zone_id: int = None
) -> dict:
    """
    Get the most applicable minimum consumption policy based on priority.

    Priority matching (lowest priority_order wins):
    1. Specific furniture type + zone + customer type
    2. Furniture type + customer type
    3. Zone + customer type
    4. Customer type only
    5. Default policy (no restrictions)

    Args:
        furniture_type: Optional furniture type code
        customer_type: Optional customer type ('interno'/'externo')
        zone_id: Optional zone ID

    Returns:
        Best matching policy dict or None
    """
    db = get_db()
    cursor = db.cursor()

    # Build query with scoring for best match
    query = '''
        SELECT p.*,
               z.name as zone_name,
               (
                   CASE
                       WHEN p.furniture_type IS NOT NULL AND p.furniture_type = ? THEN 4
                       ELSE 0
                   END +
                   CASE
                       WHEN p.customer_type IS NOT NULL AND p.customer_type = ? THEN 2
                       ELSE 0
                   END +
                   CASE
                       WHEN p.zone_id IS NOT NULL AND p.zone_id = ? THEN 1
                       ELSE 0
                   END
               ) as match_score
        FROM beach_minimum_consumption_policies p
        LEFT JOIN beach_zones z ON p.zone_id = z.id
        WHERE p.is_active = 1
          AND (p.furniture_type IS NULL OR p.furniture_type = ?)
          AND (p.customer_type IS NULL OR p.customer_type = ?)
          AND (p.zone_id IS NULL OR p.zone_id = ?)
        ORDER BY match_score DESC, p.priority_order ASC
        LIMIT 1
    '''

    params = [
        furniture_type, customer_type, zone_id,  # For scoring
        furniture_type, customer_type, zone_id   # For filtering
    ]

    cursor.execute(query, params)
    row = cursor.fetchone()
    return dict(row) if row else None


def calculate_minimum_consumption(policy_id: int, num_people: int) -> dict:
    """
    Calculate minimum consumption amount based on policy.

    Args:
        policy_id: Policy ID
        num_people: Number of people

    Returns:
        Dict with calculation details:
        {
            'policy_id': int,
            'policy_name': str,
            'minimum_amount': float,
            'calculation_type': str,
            'num_people': int,
            'total_minimum': float,
            'per_person': float,
            'breakdown': str
        }
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy:
        return None

    minimum_amount = float(policy['minimum_amount'])
    calculation_type = policy.get('calculation_type', 'per_reservation')

    if calculation_type == 'per_person':
        total_minimum = minimum_amount * num_people
        per_person = minimum_amount
        breakdown = f"€{minimum_amount:.2f} por persona × {num_people} = €{total_minimum:.2f}"
    else:  # per_reservation
        total_minimum = minimum_amount
        per_person = minimum_amount / num_people if num_people > 0 else 0
        breakdown = f"€{minimum_amount:.2f} por reserva (€{per_person:.2f} por persona)"

    return {
        'policy_id': policy_id,
        'policy_name': policy['policy_name'],
        'minimum_amount': minimum_amount,
        'calculation_type': calculation_type,
        'num_people': num_people,
        'total_minimum': total_minimum,
        'per_person': per_person,
        'breakdown': breakdown
    }


def create_minimum_consumption_policy(data: dict) -> tuple:
    """
    Create a new minimum consumption policy.

    Args:
        data: Policy data dict with keys:
            - policy_name (required)
            - policy_description
            - minimum_amount (required)
            - calculation_type: 'per_reservation' or 'per_person'
            - furniture_type
            - customer_type: 'interno', 'externo', or 'both'
            - zone_id
            - priority_order (default: 0)
            - is_active (default: 1)

    Returns:
        (success, policy_id, message)
    """
    if not data.get('policy_name'):
        return False, 0, "Nombre de política es requerido"

    if not data.get('minimum_amount') or float(data['minimum_amount']) <= 0:
        return False, 0, "Monto mínimo debe ser mayor a 0"

    calculation_type = data.get('calculation_type', 'per_reservation')
    if calculation_type not in ['per_reservation', 'per_person']:
        return False, 0, "Tipo de cálculo debe ser 'per_reservation' o 'per_person'"

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            INSERT INTO beach_minimum_consumption_policies (
                policy_name, policy_description, minimum_amount, calculation_type,
                furniture_type, customer_type, zone_id,
                priority_order, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data['policy_name'],
            data.get('policy_description'),
            data['minimum_amount'],
            calculation_type,
            data.get('furniture_type'),
            data.get('customer_type'),
            data.get('zone_id'),
            data.get('priority_order', 0),
            data.get('is_active', 1)
        ))

        policy_id = cursor.lastrowid
        db.commit()

        return True, policy_id, "Política creada exitosamente"

    except Exception as e:
        db.rollback()
        return False, 0, f"Error al crear política: {str(e)}"


def update_minimum_consumption_policy(policy_id: int, data: dict) -> tuple:
    """
    Update an existing minimum consumption policy.

    Args:
        policy_id: Policy ID to update
        data: Policy data dict (same fields as create)

    Returns:
        (success, message)
    """
    existing = get_minimum_consumption_policy_by_id(policy_id)
    if not existing:
        return False, "Política no encontrada"

    if not data.get('policy_name'):
        return False, "Nombre de política es requerido"

    if not data.get('minimum_amount') or float(data['minimum_amount']) <= 0:
        return False, "Monto mínimo debe ser mayor a 0"

    calculation_type = data.get('calculation_type', 'per_reservation')
    if calculation_type not in ['per_reservation', 'per_person']:
        return False, "Tipo de cálculo debe ser 'per_reservation' o 'per_person'"

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            UPDATE beach_minimum_consumption_policies
            SET policy_name = ?,
                policy_description = ?,
                minimum_amount = ?,
                calculation_type = ?,
                furniture_type = ?,
                customer_type = ?,
                zone_id = ?,
                priority_order = ?,
                is_active = ?
            WHERE id = ?
        ''', (
            data['policy_name'],
            data.get('policy_description'),
            data['minimum_amount'],
            calculation_type,
            data.get('furniture_type'),
            data.get('customer_type'),
            data.get('zone_id'),
            data.get('priority_order', 0),
            data.get('is_active', 1),
            policy_id
        ))

        db.commit()
        return True, "Política actualizada exitosamente"

    except Exception as e:
        db.rollback()
        return False, f"Error al actualizar política: {str(e)}"


def delete_minimum_consumption_policy(policy_id: int) -> tuple:
    """
    Delete a minimum consumption policy.

    Args:
        policy_id: Policy ID

    Returns:
        (success, message)
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy:
        return False, "Política no encontrada"

    db = get_db()
    cursor = db.cursor()

    # Check if policy is used in any reservations
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM beach_reservations
        WHERE minimum_consumption_policy_id = ?
    ''', (policy_id,))

    result = cursor.fetchone()
    if result['count'] > 0:
        # Policy is used, just deactivate
        try:
            cursor.execute('''
                UPDATE beach_minimum_consumption_policies
                SET is_active = 0
                WHERE id = ?
            ''', (policy_id,))
            db.commit()
            return True, "Política desactivada (está en uso en reservas existentes)"
        except Exception as e:
            db.rollback()
            return False, f"Error al desactivar política: {str(e)}"

    # Policy not used, can delete
    try:
        cursor.execute('DELETE FROM beach_minimum_consumption_policies WHERE id = ?', (policy_id,))
        db.commit()
        return True, "Política eliminada exitosamente"

    except Exception as e:
        db.rollback()
        return False, f"Error al eliminar política: {str(e)}"
