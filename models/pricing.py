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
