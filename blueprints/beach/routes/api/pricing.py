"""
Pricing API endpoints for real-time pricing calculations.
"""

from flask import current_app, request, Response
from flask_login import login_required
from datetime import datetime
from utils.api_response import api_success, api_error
from blueprints.beach.services.pricing_service import (
    get_eligible_packages,
    calculate_reservation_pricing
)
from models.pricing import get_all_minimum_consumption_policies


def register_routes(bp):
    """Register pricing API routes on the blueprint."""

    @bp.route('/pricing/packages/available', methods=['POST'])
    @login_required
    def get_available_packages():
        """
        Get packages available for selection based on reservation details.

        Request JSON:
        {
            "customer_type": "interno"|"externo",
            "furniture_ids": [1, 2, 3],
            "reservation_date": "2025-12-26",
            "num_people": 4
        }

        Response JSON:
        {
            "success": true,
            "packages": [
                {
                    "id": 1,
                    "package_name": "Classic Package",
                    "package_description": "...",
                    "calculated_price": 120.00,
                    "price_breakdown": "Paquete Classic: €120 (30€ × 4 personas)",
                    ...
                },
                ...
            ]
        }
        """
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = ["customer_type", "furniture_ids", "reservation_date", "num_people"]
            for field in required_fields:
                if field not in data:
                    return api_error(f"Campo requerido: {field}")

            # Parse date
            try:
                reservation_date = datetime.strptime(data["reservation_date"], "%Y-%m-%d").date()
            except ValueError:
                return api_error("Formato de fecha inválido. Use YYYY-MM-DD")

            # Validate customer_type
            if data["customer_type"] not in ["interno", "externo"]:
                return api_error("customer_type debe ser 'interno' o 'externo'")

            # Get eligible packages
            packages = get_eligible_packages(
                customer_type=data["customer_type"],
                furniture_ids=data["furniture_ids"],
                reservation_date=reservation_date,
                num_people=data["num_people"]
            )

            return api_success(packages=packages)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error("Error interno del servidor", 500)

    @bp.route('/pricing/calculate', methods=['POST'])
    @login_required
    def calculate_pricing():
        """
        Calculate complete pricing for a reservation.

        Request JSON:
        {
            "customer_id": 123,
            "furniture_ids": [1, 2],
            "reservation_date": "2025-12-26",
            "num_people": 4,
            "package_id": 5,  // optional
            "customer_source": "customer" | "hotel_guest"  // optional
        }

        Response JSON:
        {
            "success": true,
            "pricing": {
                "package": {...} or null,
                "package_price": 120.00,
                "minimum_consumption": {...} or null,
                "minimum_consumption_amount": 0.00,
                "calculated_price": 120.00,
                "breakdown": "Paquete Classic: €120 (30€ × 4 personas)",
                "has_package": true,
                "has_minimum_consumption": false
            }
        }
        """
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = ["customer_id", "furniture_ids", "reservation_date", "num_people"]
            for field in required_fields:
                if field not in data:
                    return api_error(f"Campo requerido: {field}")

            # Parse date
            try:
                reservation_date = datetime.strptime(data["reservation_date"], "%Y-%m-%d").date()
            except ValueError:
                return api_error("Formato de fecha inválido. Use YYYY-MM-DD")

            # Calculate pricing
            pricing = calculate_reservation_pricing(
                customer_id=data["customer_id"],
                furniture_ids=data["furniture_ids"],
                reservation_date=reservation_date,
                num_people=data["num_people"],
                package_id=data.get("package_id"),
                customer_source=data.get("customer_source", "customer"),
                minimum_consumption_policy_id=data.get("minimum_consumption_policy_id")
            )

            return api_success(pricing=pricing)

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error("Error interno del servidor")
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error("Error interno del servidor", 500)

    @bp.route('/pricing/minimum-consumption-policies', methods=['GET'])
    @login_required
    def list_minimum_consumption_policies() -> Response:
        """
        Get active minimum consumption policies, optionally filtered by customer type.

        Query params:
            customer_type (optional): 'interno' or 'externo' - filters to matching + universal policies

        Response JSON:
        {
            "success": true,
            "policies": [...]
        }
        """
        try:
            customer_type = request.args.get('customer_type')
            policies = get_all_minimum_consumption_policies(active_only=True)

            # Filter by customer type if provided
            if customer_type in ('interno', 'externo'):
                policies = [
                    p for p in policies
                    if p.get('customer_type') == customer_type or p.get('customer_type') is None
                ]

            return api_success(policies=policies)
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error("Error interno del servidor", 500)
