"""
Map reservation edit API routes - Field updates.
Partial updates and customer changes.
"""

from flask import current_app, request, jsonify, Response, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from models.reservation import get_beach_reservation_by_id
from models.customer import get_customer_by_id, create_customer_from_hotel_guest
from database import get_db


def register_routes(bp: Blueprint) -> None:
    """Register field update routes on the blueprint."""

    @bp.route('/map/reservations/<int:reservation_id>/update', methods=['PATCH'])
    @login_required
    @permission_required('beach.reservations.edit')
    def update_reservation_partial(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Partial update for in-place editing from the reservation panel.
        Only updates provided fields.

        Request body (all optional):
            num_people: int - Update headcount
            time_slot: str - 'all_day', 'morning', 'afternoon'
            observations: str - Notes/observations
            reservation_date: str - YYYY-MM-DD format

        Returns:
            JSON with success status and updated fields
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': True, 'message': 'Sin cambios'})

        # Get existing reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        # Allowed fields for partial update
        # Note: For date changes, use the dedicated /change-dates endpoint
        allowed_fields = [
            'num_people', 'time_slot', 'notes',
            'paid', 'payment_ticket_number', 'payment_method', 'preferences',
            # Pricing fields
            'price', 'final_price', 'package_id',
            'minimum_consumption_amount', 'minimum_consumption_policy_id'
        ]

        # Map frontend field names to database column names
        field_mapping = {
            'observations': 'notes',  # Frontend uses 'observations', DB uses 'notes'
            'total_price': 'final_price'  # Frontend uses 'total_price', DB uses 'final_price'
        }

        # Apply mapping and filter to allowed fields
        updates = {}
        for k, v in data.items():
            db_field = field_mapping.get(k, k)  # Map or use original
            if db_field in allowed_fields:
                updates[db_field] = v

        if not updates:
            return jsonify({'success': True, 'message': 'Sin cambios'})

        # Validate time_slot if provided
        if 'time_slot' in updates:
            if updates['time_slot'] not in ('all_day', 'morning', 'afternoon'):
                return jsonify({
                    'success': False,
                    'error': 'Valor de time_slot no valido'
                }), 400

        # Validate num_people if provided
        if 'num_people' in updates:
            try:
                updates['num_people'] = int(updates['num_people'])
                if updates['num_people'] < 1 or updates['num_people'] > 50:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Numero de personas no valido (1-50)'
                }), 400

        # Validate paid if provided (should be 0 or 1)
        if 'paid' in updates:
            updates['paid'] = 1 if updates['paid'] else 0

        # payment_ticket_number can be string or None
        if 'payment_ticket_number' in updates:
            if updates['payment_ticket_number'] == '':
                updates['payment_ticket_number'] = None

        # preferences should be comma-separated string or empty
        if 'preferences' in updates:
            if updates['preferences'] is None:
                updates['preferences'] = ''

        # Validate and convert pricing fields
        if 'final_price' in updates:
            try:
                updates['final_price'] = float(updates['final_price']) if updates['final_price'] else 0.0
            except (ValueError, TypeError):
                updates['final_price'] = 0.0

        if 'price' in updates:
            try:
                updates['price'] = float(updates['price']) if updates['price'] else 0.0
            except (ValueError, TypeError):
                updates['price'] = 0.0

        if 'minimum_consumption_amount' in updates:
            try:
                updates['minimum_consumption_amount'] = float(updates['minimum_consumption_amount']) if updates['minimum_consumption_amount'] else 0.0
            except (ValueError, TypeError):
                updates['minimum_consumption_amount'] = 0.0

        if 'package_id' in updates:
            # package_id can be None (no package) or a valid integer
            if updates['package_id'] in (None, '', 0, '0'):
                updates['package_id'] = None
            else:
                try:
                    updates['package_id'] = int(updates['package_id'])
                except (ValueError, TypeError):
                    updates['package_id'] = None

        if 'minimum_consumption_policy_id' in updates:
            if updates['minimum_consumption_policy_id'] in (None, '', 0, '0'):
                updates['minimum_consumption_policy_id'] = None
            else:
                try:
                    updates['minimum_consumption_policy_id'] = int(updates['minimum_consumption_policy_id'])
                except (ValueError, TypeError):
                    updates['minimum_consumption_policy_id'] = None

        try:
            with get_db() as conn:
                # Build dynamic UPDATE query
                set_clauses = ', '.join(f'{k} = ?' for k in updates.keys())
                values = list(updates.values()) + [reservation_id]

                conn.execute(f'''
                    UPDATE beach_reservations
                    SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', values)

                conn.commit()

            return jsonify({
                'success': True,
                'reservation_id': reservation_id,
                'updated_fields': list(updates.keys()),
                'message': 'Reserva actualizada'
            })

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500

    @bp.route('/map/reservations/<int:reservation_id>/change-customer', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def change_reservation_customer(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Change customer on an existing reservation.
        Can accept either a customer_id or hotel_guest_id (which creates a customer).

        Request body:
            customer_id: int - Existing customer ID (beach_customers)
            hotel_guest_id: int (optional) - Hotel guest ID to create customer from

        Validates:
            - Reservation exists
            - Customer exists (or is created from hotel guest)
            - No duplicate reservation for new customer on same date

        Returns:
            JSON with success status and updated customer data
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        new_customer_id = data.get('customer_id')
        hotel_guest_id = data.get('hotel_guest_id')

        if not new_customer_id and not hotel_guest_id:
            return jsonify({
                'success': False,
                'error': 'customer_id o hotel_guest_id requerido'
            }), 400

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        # If hotel_guest_id provided, create customer first
        if hotel_guest_id and not new_customer_id:
            try:
                result = create_customer_from_hotel_guest(hotel_guest_id, {})
                new_customer_id = result['customer_id']
            except ValueError as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'Error al crear cliente desde huesped'
                }), 500

        # Validate customer exists
        customer = get_customer_by_id(new_customer_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404

        # Check for duplicate reservation (same customer + date)
        reservation_date = reservation.get('reservation_date') or reservation.get('start_date')
        current_customer_id = reservation.get('customer_id')

        # Skip duplicate check if same customer
        if current_customer_id != new_customer_id:
            with get_db() as conn:
                cursor = conn.execute('''
                    SELECT id, ticket_number
                    FROM beach_reservations
                    WHERE customer_id = ?
                    AND reservation_date = ?
                    AND id != ?
                ''', (new_customer_id, reservation_date, reservation_id))
                existing = cursor.fetchone()

                if existing:
                    return jsonify({
                        'success': False,
                        'error': f'El cliente ya tiene reserva para esta fecha (#{existing["ticket_number"]})',
                        'existing_reservation_id': existing['id']
                    }), 409

        try:
            with get_db() as conn:
                conn.execute('''
                    UPDATE beach_reservations
                    SET customer_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_customer_id, reservation_id))
                conn.commit()

            return jsonify({
                'success': True,
                'reservation_id': reservation_id,
                'customer_id': new_customer_id,
                'customer': {
                    'id': customer['id'],
                    'first_name': customer.get('first_name'),
                    'last_name': customer.get('last_name'),
                    'full_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                    'customer_type': customer.get('customer_type'),
                    'room_number': customer.get('room_number'),
                    'vip_status': customer.get('vip_status'),
                    'phone': customer.get('phone')
                },
                'message': 'Cliente actualizado'
            })

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return jsonify({'success': False, 'error': 'Error al cambiar cliente'}), 500
