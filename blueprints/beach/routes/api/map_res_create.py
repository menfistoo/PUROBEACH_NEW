"""
Map reservation creation API routes.
Quick reservation creation from the map interface.
"""

from flask import current_app, request, jsonify
from flask_login import login_required, current_user

from utils.decorators import permission_required
from utils.audit import log_create
from models.furniture import get_all_furniture
from models.reservation import (
    create_beach_reservation, check_furniture_availability_bulk
)
from models.reservation_multiday import create_linked_multiday_reservations
from models.customer import get_customer_by_id
from models.characteristic_assignments import set_customer_characteristics_by_codes
from blueprints.beach.services.pricing_service import calculate_reservation_pricing


def register_routes(bp):
    """Register map reservation creation routes on the blueprint."""

    @bp.route('/map/quick-reservation', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.create')
    def quick_reservation():
        """
        Create a quick reservation from the map.
        Supports single-day and multi-day reservations.

        Request body:
            customer_id: Customer ID
            furniture_ids: List of furniture IDs
            date: Reservation date YYYY-MM-DD (for single day)
            dates: List of dates YYYY-MM-DD (for multi-day, overrides date)
            num_people: Number of people (optional, default: capacity)
            time_slot: 'all_day', 'morning', 'afternoon' (optional)
            preferences: List of preference codes (optional)
            notes: Notes (optional)

        Returns:
            JSON with reservation_id(s) and ticket_number
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

            customer_id = data.get('customer_id')
            furniture_ids = data.get('furniture_ids', [])
            furniture_by_date = data.get('furniture_by_date')  # Per-day furniture selections
            dates = data.get('dates', [])
            date_str = data.get('date')
            num_people = data.get('num_people')
            time_slot = data.get('time_slot', 'all_day')
            preferences = data.get('preferences', [])
            notes = data.get('notes', '')
            # SG-06: Charge to room option (only for hotel guests)
            charge_to_room = 1 if data.get('charge_to_room') else 0

            # Pricing fields from frontend
            package_id = data.get('package_id')
            if package_id:
                try:
                    package_id = int(package_id)
                except (ValueError, TypeError):
                    package_id = None

            price_override = data.get('price_override')
            if price_override:
                try:
                    price_override = float(price_override)
                except (ValueError, TypeError):
                    price_override = None

            # Payment tracking fields
            payment_ticket_number = data.get('payment_ticket_number')
            if payment_ticket_number:
                payment_ticket_number = str(payment_ticket_number).strip() or None

            payment_method = data.get('payment_method')
            if payment_method and payment_method not in ('efectivo', 'tarjeta', 'cargo_habitacion'):
                payment_method = None

            # Paid status (auto-toggled when payment details provided)
            paid = 1 if data.get('paid') else 0

            # Handle single date or array of dates
            if not dates and date_str:
                dates = [date_str]

            # Validation
            if not customer_id:
                return jsonify({'success': False, 'error': 'Cliente requerido'}), 400

            # Need either furniture_ids or furniture_by_date
            if not furniture_ids and not furniture_by_date:
                return jsonify({'success': False, 'error': 'Mobiliario requerido'}), 400

            if not dates:
                return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

            # Validate time_slot
            if time_slot not in ('all_day', 'morning', 'afternoon'):
                time_slot = 'all_day'

            # Check customer exists
            customer = get_customer_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404

            # Check furniture availability
            if furniture_by_date:
                # Per-date availability check when using furniture_by_date
                # Each date has specific furniture, check only those for that date
                all_unavailable = []
                all_available = True

                for check_date, date_furniture_ids in furniture_by_date.items():
                    availability = check_furniture_availability_bulk(
                        furniture_ids=date_furniture_ids,
                        dates=[check_date]
                    )
                    if not availability.get('all_available'):
                        all_available = False
                        all_unavailable.extend(availability.get('unavailable', []))

                if not all_available:
                    return jsonify({
                        'success': False,
                        'error': 'Mobiliario no disponible para algunas fechas',
                        'unavailable': all_unavailable,
                        'availability_matrix': {}
                    }), 409

                # Collect all furniture IDs for capacity calculation
                all_furniture_ids = set()
                for date_furniture in furniture_by_date.values():
                    all_furniture_ids.update(date_furniture)
                all_furniture_ids = list(all_furniture_ids)
            else:
                all_furniture_ids = furniture_ids

                # Check furniture availability for all dates
                availability = check_furniture_availability_bulk(
                    furniture_ids=all_furniture_ids,
                    dates=dates
                )

                if not availability.get('all_available'):
                    # Return detailed conflict information for the frontend
                    return jsonify({
                        'success': False,
                        'error': 'Mobiliario no disponible para algunas fechas',
                        'unavailable': availability.get('unavailable', []),
                        'availability_matrix': availability.get('availability_matrix', {})
                    }), 409

            # Calculate num_people from furniture capacity if not provided
            if not num_people:
                furniture_list = get_all_furniture(active_only=True)
                furniture_map = {f['id']: f for f in furniture_list}
                num_people = sum(
                    furniture_map.get(fid, {}).get('capacity', 2)
                    for fid in all_furniture_ids
                )

            # Convert preferences list to comma-separated string
            preferences_str = ','.join(preferences) if preferences else None

            # Calculate pricing
            calculated_price = 0.0
            calculated_min_consumption = 0.0
            min_consumption_policy_id = None

            if price_override is not None:
                # Manual price override - use it directly
                calculated_price = price_override
            else:
                # Calculate pricing based on package or minimum consumption
                from datetime import datetime
                try:
                    first_date = datetime.strptime(dates[0], '%Y-%m-%d').date()
                    pricing = calculate_reservation_pricing(
                        customer_id=customer_id,
                        furniture_ids=all_furniture_ids,
                        reservation_date=first_date,
                        num_people=num_people,
                        package_id=package_id
                    )

                    if pricing.get('has_package'):
                        calculated_price = pricing.get('package_price', 0.0)
                    elif pricing.get('has_minimum_consumption'):
                        calculated_min_consumption = pricing.get('minimum_consumption_amount', 0.0)
                        min_consumption_policy_id = pricing.get('minimum_consumption', {}).get('policy_id')
                        calculated_price = calculated_min_consumption

                except Exception as pricing_error:
                    # Log error but continue with zero price
                    current_app.logger.error(f'Pricing calculation failed: {pricing_error}', exc_info=True)

            # Multi-day reservation
            if len(dates) > 1:
                result = create_linked_multiday_reservations(
                    customer_id=customer_id,
                    dates=dates,
                    num_people=num_people,
                    furniture_ids=furniture_ids if not furniture_by_date else None,
                    furniture_by_date=furniture_by_date,
                    time_slot=time_slot,
                    charge_to_room=charge_to_room,
                    preferences=preferences_str,
                    observations=notes,
                    created_by=current_user.username if current_user else 'system',
                    # Pricing fields from calculation
                    price=calculated_price,
                    final_price=calculated_price,
                    paid=paid,
                    package_id=package_id,
                    payment_ticket_number=payment_ticket_number,
                    payment_method=payment_method,
                    minimum_consumption_amount=calculated_min_consumption,
                    minimum_consumption_policy_id=min_consumption_policy_id
                )

                if result.get('success'):
                    # Two-way sync: Update customer preferences from reservation
                    if preferences:
                        set_customer_characteristics_by_codes(customer_id, preferences)

                    # Log audit entry for each created reservation
                    if result.get('reservation_ids'):
                        for res_id in result['reservation_ids']:
                            reservation_data = {
                                'customer_id': customer_id,
                                'dates': dates,
                                'num_people': num_people,
                                'furniture_ids': furniture_ids or furniture_by_date,
                                'ticket_number': result.get('parent_ticket')
                            }
                            log_create('reservation', res_id, data=reservation_data)

                    return jsonify({
                        'success': True,
                        'reservation_id': result['parent_id'],
                        'ticket_number': result['parent_ticket'],
                        'total_days': result['total_created'],
                        'message': f"Reserva {result['parent_ticket']} creada para {result['total_created']} dias"
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Error al crear reserva multi-dia')
                    }), 400

            # Single-day reservation
            else:
                reservation_id, ticket_number = create_beach_reservation(
                    customer_id=customer_id,
                    reservation_date=dates[0],
                    num_people=num_people,
                    furniture_ids=furniture_ids,
                    time_slot=time_slot,
                    charge_to_room=charge_to_room,
                    preferences=preferences_str,
                    observations=notes,
                    created_by=current_user.username if current_user else 'system',
                    # Pricing fields from calculation
                    price=calculated_price,
                    final_price=calculated_price,
                    paid=paid,
                    package_id=package_id,
                    payment_ticket_number=payment_ticket_number,
                    payment_method=payment_method,
                    minimum_consumption_amount=calculated_min_consumption,
                    minimum_consumption_policy_id=min_consumption_policy_id
                )

                # Two-way sync: Update customer preferences from reservation
                if preferences:
                    set_customer_characteristics_by_codes(customer_id, preferences)

                # Log audit entry for single-day reservation
                reservation_data = {
                    'customer_id': customer_id,
                    'date': dates[0],
                    'num_people': num_people,
                    'furniture_ids': furniture_ids,
                    'ticket_number': ticket_number
                }
                log_create('reservation', reservation_id, data=reservation_data)

                return jsonify({
                    'success': True,
                    'reservation_id': reservation_id,
                    'ticket_number': ticket_number,
                    'message': f'Reserva {ticket_number} creada exitosamente'
                })

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
