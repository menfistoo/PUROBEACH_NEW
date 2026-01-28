"""
Pricing Service - Business logic for reservation pricing calculations.

Handles:
- Package eligibility filtering
- Package price calculations
- Minimum consumption matching and calculations
- Complete reservation pricing orchestration
"""

from typing import Optional, Dict, List, Any
from datetime import date as Date
from models.package import (
    get_active_packages_for_date,
    get_package_by_id
)
from models.pricing import (
    get_applicable_minimum_consumption_policy,
    get_minimum_consumption_policy_by_id
)
from models.furniture import get_furniture_by_id
from models.customer import get_customer_by_id
from models.hotel_guest import get_hotel_guest_by_id


def get_furniture_details(furniture_ids: List[int]) -> Dict[str, Any]:
    """
    Get furniture details for pricing calculations.

    Args:
        furniture_ids: List of furniture IDs

    Returns:
        dict with furniture_types (list), zone_id (first furniture's zone)
    """
    if not furniture_ids:
        return {"furniture_types": [], "zone_id": None}

    furniture_types = []
    zone_id = None

    for furniture_id in furniture_ids:
        furniture = get_furniture_by_id(furniture_id)
        if furniture:
            furniture_types.append(furniture["furniture_type"])
            if zone_id is None:
                zone_id = furniture["zone_id"]

    return {
        "furniture_types": furniture_types,
        "zone_id": zone_id
    }


def get_eligible_packages(
    customer_type: str,
    furniture_ids: List[int],
    reservation_date: Date,
    num_people: int
) -> List[Dict[str, Any]]:
    """
    Get packages available for this reservation based on restrictions.

    Filters by:
    - customer_type (interno/externo/both)
    - furniture_type (must match at least one selected furniture)
    - date validity
    - zone (if package has zone restriction)
    - people capacity (min/max people)

    Args:
        customer_type: 'interno' or 'externo'
        furniture_ids: List of selected furniture IDs
        reservation_date: Date of reservation
        num_people: Number of people

    Returns:
        List of eligible packages with calculated prices
    """
    import logging
    logger = logging.getLogger(__name__)

    furniture_details = get_furniture_details(furniture_ids)
    furniture_types = furniture_details["furniture_types"]
    zone_id = furniture_details["zone_id"]

    logger.info(f"[Pricing] get_eligible_packages - customer_type={customer_type}, furniture_types={furniture_types}, zone_id={zone_id}, num_people={num_people}, date={reservation_date}")

    # Get packages matching customer type and date
    packages = get_active_packages_for_date(
        date=reservation_date,
        customer_type=customer_type,
        zone_id=zone_id
    )

    logger.info(f"[Pricing] Found {len(packages)} packages from database")
    for pkg in packages:
        logger.info(f"[Pricing]   - {pkg['package_name']}: furniture_types={pkg.get('furniture_types_included')}, min={pkg['min_people']}, max={pkg['max_people']}")

    eligible_packages = []

    for package in packages:
        # Check people capacity
        if num_people < package["min_people"] or num_people > package["max_people"]:
            logger.info(f"[Pricing] Filtered out {package['package_name']}: people count {num_people} not in range [{package['min_people']}, {package['max_people']}]")
            continue

        # Check furniture type compatibility
        # Skip if furniture_types_included is None, empty, or the string 'None'
        furniture_types_str = package["furniture_types_included"]
        if furniture_types_str and str(furniture_types_str).lower() != 'none':
            included_types = [t.strip().lower() for t in furniture_types_str.split(",")]

            # At least one selected furniture must match an included type (case-insensitive)
            if not any(ftype.lower() in included_types for ftype in furniture_types):
                logger.info(f"[Pricing] Filtered out {package['package_name']}: furniture types {furniture_types} not in {included_types}")
                continue

        # Calculate price for this package
        price = calculate_package_price(package["id"], num_people)

        # Add price breakdown
        if package["price_type"] == "per_person":
            breakdown = f"Paquete {package['package_name']}: €{price:.2f} ({package['base_price']:.2f}€ × {num_people} personas)"
        else:
            breakdown = f"Paquete {package['package_name']}: €{price:.2f} (precio fijo)"

        eligible_packages.append({
            **package,
            "calculated_price": price,
            "price_breakdown": breakdown
        })

    # Sort by price (ascending)
    eligible_packages.sort(key=lambda x: x["calculated_price"])

    return eligible_packages


def calculate_package_price(package_id: int, num_people: int) -> float:
    """
    Calculate price based on package pricing type.

    Args:
        package_id: Package ID
        num_people: Number of people

    Returns:
        Calculated price (float)
    """
    package = get_package_by_id(package_id)
    if not package:
        return 0.0

    if package["price_type"] == "per_person":
        return package["base_price"] * num_people
    else:  # per_package
        return package["base_price"]


def get_applicable_minimum_consumption(
    furniture_ids: List[int],
    customer_type: str,
    num_people: int
) -> Optional[Dict[str, Any]]:
    """
    Find the highest-priority minimum consumption policy.

    Uses priority-based matching:
    1. furniture_type + customer_type + zone (highest priority)
    2. furniture_type + customer_type
    3. furniture_type + zone
    4. customer_type + zone
    5. furniture_type only
    6. customer_type only
    7. zone only
    8. Default (all NULL) (lowest priority)

    Args:
        furniture_ids: List of selected furniture IDs
        customer_type: 'interno' or 'externo'
        num_people: Number of people

    Returns:
        dict with policy details and calculated amount, or None
    """
    if not furniture_ids:
        return None

    furniture_details = get_furniture_details(furniture_ids)
    furniture_types = furniture_details["furniture_types"]
    zone_id = furniture_details["zone_id"]

    # Try to find applicable policy for each furniture type
    # Use the first match (highest priority)
    for furniture_type in furniture_types:
        policy = get_applicable_minimum_consumption_policy(
            furniture_type=furniture_type,
            customer_type=customer_type,
            zone_id=zone_id
        )

        if policy:
            # Calculate amount based on calculation_type
            if policy["calculation_type"] == "per_person":
                amount = policy["minimum_amount"] * num_people
                breakdown = f"Consumo mínimo: €{amount:.2f} ({policy['minimum_amount']:.2f}€ × {num_people} personas)"
            else:  # per_reservation
                amount = policy["minimum_amount"]
                breakdown = f"Consumo mínimo: €{amount:.2f} (fijo por reserva)"

            return {
                "policy_id": policy["id"],
                "policy_name": policy["policy_name"],
                "amount": amount,
                "breakdown": breakdown,
                "policy_description": policy.get("policy_description", "")
            }

    return None


def get_minimum_consumption_by_policy_id(
    policy_id: int,
    num_people: int
) -> Optional[Dict[str, Any]]:
    """
    Get minimum consumption details for a specific policy ID.

    Args:
        policy_id: Minimum consumption policy ID
        num_people: Number of people (for per_person calculation)

    Returns:
        dict with policy details and calculated amount, or None
    """
    policy = get_minimum_consumption_policy_by_id(policy_id)
    if not policy or not policy.get('is_active'):
        return None

    # Calculate amount based on calculation_type
    if policy["calculation_type"] == "per_person":
        amount = policy["minimum_amount"] * num_people
        breakdown = f"Consumo minimo: €{amount:.2f} ({policy['minimum_amount']:.2f}€ × {num_people} personas)"
    else:  # per_reservation
        amount = policy["minimum_amount"]
        breakdown = f"Consumo minimo: €{amount:.2f} (fijo por reserva)"

    return {
        "policy_id": policy["id"],
        "policy_name": policy["policy_name"],
        "amount": amount,
        "breakdown": breakdown,
        "policy_description": policy.get("policy_description", "")
    }


def calculate_reservation_pricing(
    customer_id: int,
    furniture_ids: List[int],
    reservation_date: Date,
    num_people: int,
    package_id: Optional[int] = None,
    customer_source: str = "customer",
    minimum_consumption_policy_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main pricing orchestrator. Calculates complete pricing for a reservation.

    Business Rules:
    - Package and minimum consumption are MUTUALLY EXCLUSIVE
    - If package selected: use package price (ignore minimum consumption)
    - If no package: use minimum consumption (if applicable)
    - Final price is editable by staff

    Args:
        customer_id: Customer ID (from beach_customers or hotel_guests)
        furniture_ids: List of selected furniture IDs
        reservation_date: Date of reservation
        num_people: Number of people
        package_id: Optional selected package ID
        customer_source: Source of customer ("customer" or "hotel_guest")
        minimum_consumption_policy_id: Optional manually selected policy ID (overrides auto-detection)

    Returns:
        dict with complete pricing information:
        {
            'package': {...} or None,
            'package_price': float,
            'minimum_consumption': {...} or None,
            'minimum_consumption_amount': float,
            'calculated_price': float,
            'breakdown': str,
            'has_package': bool,
            'has_minimum_consumption': bool
        }
    """
    # Get customer details based on source
    if customer_source == "hotel_guest":
        # Look up in hotel_guests table
        customer = get_hotel_guest_by_id(customer_id)
        if not customer:
            raise ValueError(f"Hotel guest {customer_id} not found")
        # Hotel guests are always 'interno'
        customer_type = "interno"
    else:
        # Look up in beach_customers table
        customer = get_customer_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        customer_type = customer["customer_type"]

    result = {
        "package": None,
        "package_price": 0.0,
        "minimum_consumption": None,
        "minimum_consumption_amount": 0.0,
        "calculated_price": 0.0,
        "breakdown": "",
        "has_package": False,
        "has_minimum_consumption": False
    }

    # If package selected, use package pricing (MUTUALLY EXCLUSIVE with minimum consumption)
    if package_id:
        package = get_package_by_id(package_id)
        if package:
            price = calculate_package_price(package_id, num_people)

            if package["price_type"] == "per_person":
                breakdown = f"Paquete {package['package_name']}: €{price:.2f} ({package['base_price']:.2f}€ × {num_people} personas)"
            else:
                breakdown = f"Paquete {package['package_name']}: €{price:.2f} (precio fijo)"

            result.update({
                "package": package,
                "package_price": price,
                "calculated_price": price,
                "breakdown": breakdown,
                "has_package": True
            })

            return result

    # No package selected, check for minimum consumption
    # Use manual policy selection if provided, otherwise auto-detect
    if minimum_consumption_policy_id:
        min_consumption = get_minimum_consumption_by_policy_id(
            policy_id=minimum_consumption_policy_id,
            num_people=num_people
        )
    else:
        min_consumption = get_applicable_minimum_consumption(
            furniture_ids=furniture_ids,
            customer_type=customer_type,
            num_people=num_people
        )

    if min_consumption:
        result.update({
            "minimum_consumption": min_consumption,
            "minimum_consumption_amount": min_consumption["amount"],
            "calculated_price": min_consumption["amount"],
            "breakdown": min_consumption["breakdown"],
            "has_minimum_consumption": True
        })
    else:
        result["breakdown"] = "Sin cargo (no aplica consumo mínimo)"

    return result
