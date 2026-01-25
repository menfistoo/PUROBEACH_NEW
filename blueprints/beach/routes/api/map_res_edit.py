"""
Map reservation edit API routes.
Furniture reassignment, partial updates, and customer changes.
"""

from flask import request, jsonify, Response, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from models.furniture import get_all_furniture
from models.reservation import (
    check_furniture_availability_bulk,
    get_beach_reservation_by_id
)
from models.customer import get_customer_by_id, create_customer_from_hotel_guest
from database import get_db


def register_routes(bp: Blueprint) -> None:
    """Register map reservation edit routes on the blueprint."""

    @bp.route('/map/reservations/<int:reservation_id>/reassign-furniture', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def reassign_furniture(reservation_id: int) -> tuple[Response, int] | Response:
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

        # Check if furniture is locked
        if reservation.get('is_furniture_locked'):
            return jsonify({
                'success': False,
                'error': 'locked',
                'message': 'El mobiliario de esta reserva esta bloqueado'
            }), 403

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

                # Check for unavailable furniture (function returns 'unavailable' list, not 'conflicts')
                unavailable = availability.get('unavailable', [])
                if unavailable:
                    conflict_ids = list(set(item['furniture_id'] for item in unavailable))
                    return jsonify({
                        'success': False,
                        'error': 'Algunos mobiliarios no estan disponibles',
                        'conflicts': conflict_ids
                    }), 409

        # Get furniture capacities and validate against num_people
        furniture_list = get_all_furniture(active_only=True)
        furniture_map = {f['id']: f for f in furniture_list}

        total_capacity = 0
        for fid in furniture_ids:
            furniture_info = furniture_map.get(fid)
            if furniture_info:
                total_capacity += furniture_info.get('capacity', 2)

        num_people = reservation.get('num_people', 1)
        capacity_warning = None

        # CRITICAL: Block if capacity is smaller than num_people
        if total_capacity < num_people:
            return jsonify({
                'success': False,
                'error': f'Capacidad insuficiente: {total_capacity} personas vs {num_people} requeridas',
                'total_capacity': total_capacity,
                'num_people': num_people
            }), 400

        # Warn if capacity is larger than num_people (but allow the operation)
        if total_capacity > num_people:
            capacity_warning = f'La capacidad total ({total_capacity} personas) es mayor que el numero de personas ({num_people})'

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
            updated_furniture = [
                {
                    'id': fid,
                    'number': furniture_map.get(fid, {}).get('number', str(fid)),
                    'capacity': furniture_map.get(fid, {}).get('capacity', 2)
                }
                for fid in furniture_ids
            ]

            response_data = {
                'success': True,
                'reservation_id': reservation_id,
                'date': date_str,
                'furniture': updated_furniture,
                'total_capacity': total_capacity,
                'num_people': num_people,
                'message': 'Mobiliario actualizado exitosamente'
            }

            # Add warning if capacity is larger
            if capacity_warning:
                response_data['warning'] = capacity_warning

            return jsonify(response_data)

        except Exception as e:
            return jsonify({'success': False, 'error': 'Error al actualizar mobiliario'}), 500

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
            return jsonify({'success': False, 'error': f'Error al actualizar reserva: {str(e)}'}), 500

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

    @bp.route('/map/reservations/<int:reservation_id>/check-date-availability', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def check_date_availability(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Check if reservation's furniture is available on a new date.

        Request body:
            new_date: str - YYYY-MM-DD format

        Returns:
            JSON with availability status:
            - all_available: True if all furniture is available
            - some_available: True if at least some furniture is available (but not all)
            - available_furniture: List of furniture IDs that are available
            - unavailable_furniture: List of furniture IDs that are not available
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        new_date = data.get('new_date')
        if not new_date:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(new_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        current_date = reservation.get('reservation_date') or reservation.get('start_date')

        # Get current furniture for this reservation with details
        with get_db() as conn:
            cursor = conn.execute('''
                SELECT rf.furniture_id, f.number as furniture_number
                FROM beach_reservation_furniture rf
                JOIN beach_furniture f ON rf.furniture_id = f.id
                WHERE rf.reservation_id = ? AND rf.assignment_date = ?
            ''', (reservation_id, current_date))
            furniture_rows = cursor.fetchall()
            furniture_ids = [row['furniture_id'] for row in furniture_rows]
            furniture_details = {row['furniture_id']: row['furniture_number'] for row in furniture_rows}

        if not furniture_ids:
            return jsonify({
                'success': True,
                'all_available': False,
                'some_available': False,
                'available_furniture': [],
                'unavailable_furniture': [],
                'conflicts': [],
                'error': 'No hay mobiliario asignado'
            })

        # Check availability on new date
        availability = check_furniture_availability_bulk(
            furniture_ids=furniture_ids,
            dates=[new_date],
            exclude_reservation_id=reservation_id
        )

        # Function returns 'unavailable' list, not 'conflicts' dict
        unavailable_list = availability.get('unavailable', [])
        unavailable_ids = set(item['furniture_id'] for item in unavailable_list)
        unavailable = [fid for fid in furniture_ids if fid in unavailable_ids]
        available = [fid for fid in furniture_ids if fid not in unavailable_ids]

        all_available = len(unavailable) == 0
        some_same_available = len(available) > 0

        # If none of the same furniture is available, check if there's ANY furniture
        # available on that date that could be used as an alternative
        has_alternatives = False
        if not all_available and not some_same_available:
            # Get all active furniture and check availability
            from models.furniture import get_all_furniture
            all_furniture = get_all_furniture(active_only=True)
            all_furniture_ids = [f['id'] for f in all_furniture]

            # Check which are available on the new date
            alt_availability = check_furniture_availability_bulk(
                furniture_ids=all_furniture_ids,
                dates=[new_date],
                exclude_reservation_id=reservation_id
            )
            alt_unavailable = alt_availability.get('unavailable', [])
            alt_unavailable_ids = set(item['furniture_id'] for item in alt_unavailable)

            # Count how many alternatives are available
            available_alternatives = [
                fid for fid in all_furniture_ids
                if fid not in alt_unavailable_ids
            ]
            has_alternatives = len(available_alternatives) > 0

        # some_available is True if:
        # 1. Some of the same furniture is available, OR
        # 2. None of the same is available but alternatives exist
        some_available = some_same_available or has_alternatives

        # Build conflicts list with furniture numbers for UI display
        conflicts = [
            {
                'furniture_id': fid,
                'furniture_number': furniture_details.get(fid, f'#{fid}')
            }
            for fid in unavailable
        ]

        return jsonify({
            'success': True,
            'all_available': all_available,
            'some_available': some_available,
            'available_furniture': available,
            'unavailable_furniture': unavailable,
            'conflicts': conflicts,
            'total_furniture': len(furniture_ids),
            'has_alternatives': has_alternatives,
            'needs_reassignment': not all_available and some_available
        })

    @bp.route('/map/reservations/<int:reservation_id>/change-date', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def change_reservation_date(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Change reservation date (moves furniture assignments to new date).

        Request body:
            new_date: str - YYYY-MM-DD format
            furniture_ids: list (optional) - New furniture IDs if different from current
            clear_furniture: bool (optional) - If true, clear furniture assignments
                (used when furniture unavailable and user wants to continue without)

        Pre-requisite: Should call check-date-availability first to verify.

        Returns:
            JSON with success status
        """
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        new_date = data.get('new_date')
        new_furniture_ids = data.get('furniture_ids')
        clear_furniture = data.get('clear_furniture', False)

        if not new_date:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400

        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(new_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return jsonify({'success': False, 'error': 'Reserva no encontrada'}), 404

        current_date = reservation.get('reservation_date') or reservation.get('start_date')

        # If same date, no change needed
        if new_date == current_date:
            return jsonify({'success': True, 'message': 'Sin cambios'})

        try:
            with get_db() as conn:
                # If clear_furniture is true, skip availability check and don't assign furniture
                if clear_furniture:
                    # Update reservation date
                    conn.execute('''
                        UPDATE beach_reservations
                        SET reservation_date = ?, start_date = ?, end_date = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_date, new_date, new_date, reservation_id))

                    # Delete old furniture assignments
                    conn.execute('''
                        DELETE FROM beach_reservation_furniture
                        WHERE reservation_id = ? AND assignment_date = ?
                    ''', (reservation_id, current_date))

                    # Update daily states if any
                    conn.execute('''
                        UPDATE beach_reservation_daily_states
                        SET date = ?
                        WHERE reservation_id = ? AND date = ?
                    ''', (new_date, reservation_id, current_date))

                    conn.commit()

                    return jsonify({
                        'success': True,
                        'cleared_furniture': True,
                        'new_date': new_date,
                        'reservation_id': reservation_id
                    })

                # Normal flow: Get current furniture if not provided
                if not new_furniture_ids:
                    cursor = conn.execute('''
                        SELECT furniture_id
                        FROM beach_reservation_furniture
                        WHERE reservation_id = ? AND assignment_date = ?
                    ''', (reservation_id, current_date))
                    new_furniture_ids = [row['furniture_id'] for row in cursor.fetchall()]

                # Verify availability on new date
                if new_furniture_ids:
                    availability = check_furniture_availability_bulk(
                        furniture_ids=new_furniture_ids,
                        dates=[new_date],
                        exclude_reservation_id=reservation_id
                    )

                    # Function returns 'unavailable' list, not 'conflicts' dict
                    unavailable_list = availability.get('unavailable', [])
                    if unavailable_list:
                        conflict_ids = list(set(item['furniture_id'] for item in unavailable_list))
                        return jsonify({
                            'success': False,
                            'error': 'El mobiliario no está disponible en la nueva fecha',
                            'conflicts': conflict_ids
                        }), 409

                # Update reservation date
                conn.execute('''
                    UPDATE beach_reservations
                    SET reservation_date = ?, start_date = ?, end_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_date, new_date, new_date, reservation_id))

                # Delete old furniture assignments for the old date
                conn.execute('''
                    DELETE FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND assignment_date = ?
                ''', (reservation_id, current_date))

                # Create new furniture assignments for the new date
                for fid in new_furniture_ids:
                    conn.execute('''
                        INSERT INTO beach_reservation_furniture (reservation_id, furniture_id, assignment_date)
                        VALUES (?, ?, ?)
                    ''', (reservation_id, fid, new_date))

                # Update daily states if any (column is 'date', not 'state_date')
                conn.execute('''
                    UPDATE beach_reservation_daily_states
                    SET date = ?
                    WHERE reservation_id = ? AND date = ?
                ''', (new_date, reservation_id, current_date))

                conn.commit()

            return jsonify({
                'success': True,
                'reservation_id': reservation_id,
                'old_date': current_date,
                'new_date': new_date,
                'message': 'Fecha actualizada'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': f'Error al cambiar fecha: {str(e)}'}), 500

    @bp.route('/map/reservations/<int:reservation_id>/toggle-lock', methods=['PATCH'])
    @login_required
    @permission_required('beach.reservations.edit')
    def toggle_reservation_lock(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Toggle the furniture lock status for a reservation.

        Request body:
            locked: bool - True to lock, False to unlock

        Returns:
            JSON with success status and new lock state
        """
        data = request.get_json()

        if data is None or 'locked' not in data:
            return jsonify({
                'success': False,
                'error': 'Campo "locked" requerido'
            }), 400

        locked = bool(data['locked'])

        from models.reservation_crud import toggle_furniture_lock
        result = toggle_furniture_lock(reservation_id, locked)

        if not result['success']:
            return jsonify(result), 404

        return jsonify(result)
