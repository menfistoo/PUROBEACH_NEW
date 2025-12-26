"""
Map reservation edit API routes.
Furniture reassignment, partial updates, and customer changes.
"""

from flask import request, jsonify
from flask_login import login_required

from utils.decorators import permission_required
from models.furniture import get_all_furniture
from models.reservation import (
    check_furniture_availability_bulk,
    get_beach_reservation_by_id
)
from models.customer import get_customer_by_id, create_customer_from_hotel_guest
from database import get_db


def register_routes(bp):
    """Register map reservation edit routes on the blueprint."""

    @bp.route('/map/reservations/<int:reservation_id>/reassign-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def reassign_furniture(reservation_id):
        """
        Reassign furniture to an existing reservation.
        Used from the map to change furniture positions.

        Request body:
            furniture_ids: List of new furniture IDs
            date: Date YYYY-MM-DD (for multi-day reservations, which day to update)

        Returns:
            JSON with success status and updated furniture list
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        furniture_ids = data.get('furniture_ids', [])
        date_str = data.get('date')

        # Validation
        if not furniture_ids or not isinstance(furniture_ids, list):
            return jsonify({'success': False, 'error': 'Mobiliario requerido'}), 400

        # Get existing reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        # Use reservation date if not provided
        if not date_str:
            date_str = reservation.get('reservation_date')

        # Check new furniture availability (excluding current reservation)
        with get_db() as conn:
            # Get current furniture for this reservation on this date
            cursor = conn.execute('''
                SELECT furniture_id
                FROM beach_reservation_furniture
                WHERE reservation_id = ? AND assignment_date = ?
            ''', (reservation_id, date_str))
            current_furniture_ids = [row['furniture_id'] for row in cursor.fetchall()]

            # Check if new furniture is available (excluding what's already assigned to this reservation)
            new_furniture_ids = [fid for fid in furniture_ids if fid not in current_furniture_ids]

            if new_furniture_ids:
                availability = check_furniture_availability_bulk(
                    furniture_ids=new_furniture_ids,
                    dates=[date_str],
                    exclude_reservation_id=reservation_id
                )

                if availability.get('conflicts'):
                    conflict_ids = list(availability['conflicts'].keys())
                    return jsonify({
                        'success': False,
                        'error': 'Algunos mobiliarios no estan disponibles',
                        'conflicts': conflict_ids
                    }), 409

        try:
            # Update furniture assignments for this date
            with get_db() as conn:
                # Delete existing assignments for this date
                conn.execute('''
                    DELETE FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND assignment_date = ?
                ''', (reservation_id, date_str))

                # Insert new assignments
                for furniture_id in furniture_ids:
                    conn.execute('''
                        INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                        VALUES (?, ?, ?)
                    ''', (reservation_id, furniture_id, date_str))

                conn.commit()

            # Get updated furniture info for response
            furniture_list = get_all_furniture(active_only=True)
            furniture_map = {f['id']: f for f in furniture_list}
            updated_furniture = [
                {
                    'id': fid,
                    'number': furniture_map.get(fid, {}).get('number', str(fid))
                }
                for fid in furniture_ids
            ]

            return jsonify({
                'success': True,
                'reservation_id': reservation_id,
                'date': date_str,
                'furniture': updated_furniture,
                'message': 'Mobiliario actualizado exitosamente'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': 'Error al actualizar mobiliario'}), 500

    @bp.route('/map/reservations/<int:reservation_id>/update', methods=['PATCH'])
    @login_required
    @permission_required('beach.reservations.edit')
    def update_reservation_partial(reservation_id):
        """
        Partial update for in-place editing from the reservation panel.
        Only updates provided fields.

        Request body (all optional):
            num_people: int - Update headcount
            time_slot: str - 'all_day', 'morning', 'afternoon'
            observations: str - Notes/observations

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
        allowed_fields = ['num_people', 'time_slot', 'observations']
        updates = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

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
            return jsonify({'success': False, 'error': 'Error al actualizar reserva'}), 500

    @bp.route('/map/reservations/<int:reservation_id>/change-customer', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def change_reservation_customer(reservation_id):
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
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
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
            return jsonify({'success': False, 'error': 'Error al cambiar cliente'}), 500
