"""
Map reservation details API routes.
Reservation panel details and furniture move operations.
"""

from flask import current_app, request
from flask_login import login_required
from datetime import date, datetime
from utils.datetime_helpers import get_today

from utils.decorators import permission_required
from utils.api_response import api_success, api_error


def _format_date_iso(value):
    """
    Format a date value to ISO format (YYYY-MM-DD) string.
    Handles datetime objects, date objects, and string values.
    Returns None if value is None or empty.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    # If it's already a string, try to parse and reformat it
    if isinstance(value, str):
        # Check if it's already in YYYY-MM-DD format
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            return value
        # Try to parse various date formats
        for fmt in ['%Y-%m-%d', '%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%d %H:%M:%S']:
            try:
                parsed = datetime.strptime(value.strip(), fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        # Return as-is if we can't parse
        return value[:10] if len(value) >= 10 else value
    return str(value)


from models.furniture import get_all_furniture
from models.reservation import (
    check_furniture_availability_bulk,
    get_beach_reservation_by_id
)
from models.customer import get_customer_by_id
from models.characteristic_assignments import get_customer_characteristics, get_reservation_characteristics
from database import get_db


def register_routes(bp):
    """Register map reservation details routes on the blueprint."""

    @bp.route('/map/reservations/<int:reservation_id>/details')
    @login_required
    @permission_required('beach.reservations.view')
    def get_reservation_panel_details(reservation_id):
        """
        Get full reservation details for the reservation panel.
        Includes reservation, customer, and furniture data.

        Query params:
            date: Date string YYYY-MM-DD (for multi-day context)

        Returns:
            JSON with complete reservation, customer, and furniture info
        """
        date_str = request.args.get('date', get_today().strftime('%Y-%m-%d'))

        # Get reservation with details
        from models.reservation import get_reservation_with_details
        reservation = get_reservation_with_details(reservation_id)

        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # Get reservation-specific characteristics (always, regardless of customer)
        reservation_characteristics = get_reservation_characteristics(reservation_id)

        # Get customer details
        customer = None
        customer_preferences = []
        hotel_guest_info = {}
        customer_id = reservation.get('customer_id')
        if customer_id:
            customer = get_customer_by_id(customer_id)
            customer_preferences = get_customer_characteristics(customer_id)

            # For interno customers with room number, fetch hotel guest info
            if customer and customer.get('customer_type') == 'interno' and customer.get('room_number'):
                from models.hotel_guest import get_guests_by_room
                guests = get_guests_by_room(customer['room_number'], get_today())
                if guests:
                    # Try to find matching guest by name
                    full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip().upper()
                    matching_guest = None
                    for g in guests:
                        if g['guest_name'].upper() == full_name:
                            matching_guest = g
                            break
                    # Fall back to main guest or first guest
                    if not matching_guest:
                        matching_guest = next((g for g in guests if g.get('is_main_guest')), guests[0])

                    if matching_guest:
                        hotel_guest_info = {
                            'arrival_date': matching_guest.get('arrival_date'),
                            'departure_date': matching_guest.get('departure_date'),
                            'booking_reference': matching_guest.get('booking_reference'),
                            'nationality': matching_guest.get('nationality'),
                            'vip_code': matching_guest.get('vip_code')
                        }

        # Build customer data
        customer_data = {
            'id': customer['id'],
            'first_name': customer.get('first_name'),
            'last_name': customer.get('last_name'),
            'full_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
            'customer_type': customer.get('customer_type'),
            'room_number': customer.get('room_number'),
            'phone': customer.get('phone'),
            'email': customer.get('email'),
            'vip_status': customer.get('vip_status', 0),
            'total_visits': customer.get('total_visits', 0),
            'notes': customer.get('notes'),
            'preferences': [{
                'id': p['id'],
                'code': p.get('code'),
                'name': p.get('name'),
                'icon': p.get('icon')
            } for p in customer_preferences],
            # Hotel guest info for interno customers
            'arrival_date': _format_date_iso(hotel_guest_info.get('arrival_date')),
            'departure_date': _format_date_iso(hotel_guest_info.get('departure_date')),
            'booking_reference': hotel_guest_info.get('booking_reference'),
            'nationality': hotel_guest_info.get('nationality'),
            'vip_code': hotel_guest_info.get('vip_code')
        } if customer else None

        # Build response
        return api_success(
            date=date_str,
            reservation={
                'id': reservation['id'],
                'ticket_number': reservation.get('ticket_number'),
                'current_state': reservation.get('current_state'),
                'current_states': reservation.get('current_states'),
                'display_color': reservation.get('display_color'),
                'num_people': reservation.get('num_people'),
                'time_slot': reservation.get('time_slot'),
                'notes': reservation.get('notes') or reservation.get('observations'),
                'reservation_date': _format_date_iso(reservation.get('reservation_date')),
                'start_date': _format_date_iso(reservation.get('start_date')),
                'end_date': _format_date_iso(reservation.get('end_date')),
                'created_at': reservation.get('created_at'),
                'furniture': reservation.get('furniture', []),
                'tags': reservation.get('tags', []),
                'preferences': reservation.get('preferences'),
                'is_furniture_locked': reservation.get('is_furniture_locked', 0),
                # Pricing fields
                'price': reservation.get('price', 0.0),
                'final_price': reservation.get('final_price', 0.0),
                'package_id': reservation.get('package_id'),
                'package_name': reservation.get('package_name'),
                'minimum_consumption_amount': reservation.get('minimum_consumption_amount', 0.0),
                'minimum_consumption_policy_id': reservation.get('minimum_consumption_policy_id'),
                'minimum_consumption_policy_name': reservation.get('minimum_consumption_policy_name'),
                'paid': reservation.get('paid', 0),
                'payment_ticket_number': reservation.get('payment_ticket_number'),
                'payment_method': reservation.get('payment_method')
            },
            customer=customer_data,
            reservation_characteristics=[{
                'id': c['id'],
                'code': c.get('code'),
                'name': c.get('name'),
                'icon': c.get('icon')
            } for c in reservation_characteristics]
        )

    @bp.route('/map/move-reservation-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def move_reservation_furniture():
        """
        Move a reservation from one furniture to another for a specific date.
        Used for quick swap during conflict resolution.

        Request body:
            reservation_id: int - Reservation to move
            date: str - Date YYYY-MM-DD
            from_furniture_id: int - Current furniture ID
            to_furniture_id: int - Destination furniture ID

        Returns:
            JSON with success status
        """
        data = request.get_json()

        if not data:
            return api_error('Datos requeridos')

        reservation_id = data.get('reservation_id')
        date_str = data.get('date')
        from_furniture_id = data.get('from_furniture_id')
        to_furniture_id = data.get('to_furniture_id')

        # Validation
        if not all([reservation_id, date_str, from_furniture_id, to_furniture_id]):
            return api_error('Faltan parametros requeridos')

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # Check destination furniture is available
        availability = check_furniture_availability_bulk(
            furniture_ids=[to_furniture_id],
            dates=[date_str],
            exclude_reservation_id=reservation_id
        )

        if not availability.get('all_available'):
            # Get details about who's blocking
            unavailable = availability.get('unavailable', [])
            if unavailable:
                blocker = unavailable[0]
                return api_error(
                    f'Mobiliario ocupado por {blocker.get("customer_name", "otra reserva")}',
                    409,
                    conflict=blocker
                )
            return api_error('Mobiliario de destino no disponible', 409)

        try:
            with get_db() as conn:
                # Check that the reservation actually has the from_furniture on this date
                cursor = conn.execute('''
                    SELECT id FROM beach_reservation_furniture
                    WHERE reservation_id = ?
                      AND assignment_date = ?
                      AND furniture_id = ?
                ''', (reservation_id, date_str, from_furniture_id))

                assignment = cursor.fetchone()
                if not assignment:
                    return api_error('La reserva no tiene este mobiliario asignado para esta fecha')

                # Update the furniture assignment
                conn.execute('''
                    UPDATE beach_reservation_furniture
                    SET furniture_id = ?
                    WHERE reservation_id = ?
                      AND assignment_date = ?
                      AND furniture_id = ?
                ''', (to_furniture_id, reservation_id, date_str, from_furniture_id))

                conn.commit()

            # Get furniture info for response
            furniture_list = get_all_furniture(active_only=True)
            furniture_map = {f['id']: f for f in furniture_list}
            from_furniture = furniture_map.get(from_furniture_id, {})
            to_furniture = furniture_map.get(to_furniture_id, {})

            return api_success(
                message=f'Reserva movida de {from_furniture.get("number", from_furniture_id)} a {to_furniture.get("number", to_furniture_id)}',
                reservation_id=reservation_id,
                date=date_str,
                from_furniture={
                    'id': from_furniture_id,
                    'number': from_furniture.get('number', str(from_furniture_id))
                },
                to_furniture={
                    'id': to_furniture_id,
                    'number': to_furniture.get('number', str(to_furniture_id))
                }
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error al mover la reserva', 500)
