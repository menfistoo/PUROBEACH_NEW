"""
Map reservation creation API routes.
Quick reservation creation from the map interface.
"""

from flask import current_app, request, jsonify
from flask_login import login_required, current_user

from utils.decorators import permission_required
from utils.audit import log_create
from utils.api_response import api_success, api_error
from utils.validators import (
    validate_positive_integer, validate_integer_list,
    validate_date_list, validate_furniture_by_date,
    validate_start_end_dates
)
from models.furniture import get_all_furniture
from models.reservation import (
    create_beach_reservation, check_furniture_availability_bulk
)
from models.reservation_multiday import create_linked_multiday_reservations
from models.customer import get_customer_by_id
from models.characteristic_assignments import set_customer_characteristics_by_codes, set_reservation_characteristics_by_codes
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
                return api_error('Datos requeridos', 400)

            # ---- Input validation ----

            # Validate customer_id: required, positive integer
            valid, customer_id, err = validate_positive_integer(
                data.get('customer_id'), 'customer_id'
            )
            if not valid:
                return api_error(err, 400)

            furniture_ids = data.get('furniture_ids', [])
            furniture_by_date = data.get('furniture_by_date')  # Per-day furniture selections
            dates = data.get('dates', [])
            date_str = data.get('date')

            # Handle single date or array of dates (build early for validation)
            if not dates and date_str:
                dates = [date_str]

            # Validate dates: required, valid YYYY-MM-DD format
            if not dates:
                return api_error('El campo fecha es obligatorio', 400)
            valid, dates, err = validate_date_list(dates, 'fechas')
            if not valid:
                return api_error(err, 400)

            # Validate start <= end when multiple dates
            if len(dates) > 1:
                sorted_dates = sorted(dates)
                valid, err = validate_start_end_dates(sorted_dates[0], sorted_dates[-1])
                if not valid:
                    return api_error(err, 400)

            # Validate furniture_ids or furniture_by_date: at least one required
            if furniture_by_date:
                valid, furniture_by_date, err = validate_furniture_by_date(
                    furniture_by_date, 'furniture_by_date'
                )
                if not valid:
                    return api_error(err, 400)
            elif furniture_ids:
                valid, furniture_ids, err = validate_integer_list(
                    furniture_ids, 'furniture_ids'
                )
                if not valid:
                    return api_error(err, 400)
            else:
                return api_error('Mobiliario requerido', 400)

            # Validate num_people: optional, but must be positive integer if provided
            num_people = data.get('num_people')
            if num_people is not None:
                valid, num_people, err = validate_positive_integer(num_people, 'num_people')
                if not valid:
                    return api_error(err, 400)

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

            # Validate time_slot
            if time_slot not in ('all_day', 'morning', 'afternoon'):
                time_slot = 'all_day'

            # Check customer exists
            customer = get_customer_by_id(customer_id)
            if not customer:
                return api_error('Cliente no encontrado', 404)

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
                    return api_error(
                        'Mobiliario no disponible para algunas fechas', 409,
                        unavailable=all_unavailable,
                        availability_matrix={}
                    )

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
                    return api_error(
                        'Mobiliario no disponible para algunas fechas', 409,
                        unavailable=availability.get('unavailable', []),
                        availability_matrix=availability.get('availability_matrix', {})
                    )

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
            pricing_warning = None

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
                    # Log error and flag the warning for the API response
                    current_app.logger.error(f'Pricing calculation failed: {pricing_error}', exc_info=True)
                    pricing_warning = 'No se pudo calcular el precio. Revise la configuración de precios.'

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

                        # Also save characteristics to each reservation
                        for res_id in result.get('reservation_ids', []):
                            set_reservation_characteristics_by_codes(res_id, preferences)

                    # Save tags to each reservation and sync to customer
                    tag_ids = data.get('tag_ids', [])
                    if tag_ids:
                        from models.tag import set_reservation_tags, sync_reservation_tags_to_customer
                        for res_id in result.get('reservation_ids', []):
                            set_reservation_tags(res_id, tag_ids)
                        # Sync to customer (use first reservation for customer lookup)
                        if result.get('reservation_ids'):
                            sync_reservation_tags_to_customer(result['reservation_ids'][0], tag_ids)

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

                    response_data = {
                        'success': True,
                        'reservation_id': result['parent_id'],
                        'ticket_number': result['parent_ticket'],
                        'total_days': result['total_created'],
                        'message': f"Reserva {result['parent_ticket']} creada para {result['total_created']} dias"
                    }
                    if pricing_warning:
                        response_data['warning'] = pricing_warning
                    return jsonify(response_data)
                else:
                    return api_error(
                        result.get('error', 'Error al crear reserva multi-dia'), 400
                    )

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

                    # Also save characteristics to the reservation
                    set_reservation_characteristics_by_codes(reservation_id, preferences)

                # Save tags to reservation and sync to customer
                tag_ids = data.get('tag_ids', [])
                if tag_ids:
                    from models.tag import set_reservation_tags, sync_reservation_tags_to_customer
                    set_reservation_tags(reservation_id, tag_ids)
                    sync_reservation_tags_to_customer(reservation_id, tag_ids)

                # Log audit entry for single-day reservation
                reservation_data = {
                    'customer_id': customer_id,
                    'date': dates[0],
                    'num_people': num_people,
                    'furniture_ids': furniture_ids,
                    'ticket_number': ticket_number
                }
                log_create('reservation', reservation_id, data=reservation_data)

                response_data = {
                    'success': True,
                    'reservation_id': reservation_id,
                    'ticket_number': ticket_number,
                    'message': f'Reserva {ticket_number} creada exitosamente'
                }
                if pricing_warning:
                    response_data['warning'] = pricing_warning
                return jsonify(response_data)

        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Solicitud inválida', 400)
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)
