"""
Map reservation edit API routes - Field updates.
Partial updates and customer changes.
"""

from flask import current_app, request, Response, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from utils.validators import validate_positive_integer
from utils.api_response import api_success, api_error
from models.reservation import get_beach_reservation_by_id
from models.customer import get_customer_by_id, create_customer_from_hotel_guest
from database import get_db
from models.characteristic_assignments import set_reservation_characteristics_by_codes
from models.tag import set_reservation_tags, sync_reservation_tags_to_customer
from utils.audit import log_update


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
            return api_success(message='Sin cambios')

        # Get existing reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # Capture before-state for audit log
        before_state = dict(reservation) if reservation else {}

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

        # Check if only tag/state changes (handled separately below)
        has_tag_changes = 'tag_ids' in data
        has_state_changes = 'state_id' in data
        if not updates and not has_tag_changes and not has_state_changes:
            return api_success(message='Sin cambios')

        # Validate time_slot if provided
        if 'time_slot' in updates:
            if updates['time_slot'] not in ('all_day', 'morning', 'afternoon'):
                return api_error('Valor de time_slot no valido')

        # Validate num_people if provided
        if 'num_people' in updates:
            try:
                updates['num_people'] = int(updates['num_people'])
                if updates['num_people'] < 1 or updates['num_people'] > 50:
                    raise ValueError()
            except (ValueError, TypeError):
                return api_error('Numero de personas no valido (1-50)')

        # Validate paid if provided (should be 0 or 1)
        if 'paid' in updates:
            updates['paid'] = 1 if updates['paid'] else 0

        # Validate payment_method if provided
        if 'payment_method' in updates:
            if updates['payment_method'] and updates['payment_method'] not in (
                'efectivo', 'tarjeta', 'cargo_habitacion'
            ):
                return api_error('Metodo de pago no valido')

        # payment_ticket_number can be string or None
        if 'payment_ticket_number' in updates:
            if updates['payment_ticket_number'] == '':
                updates['payment_ticket_number'] = None

        # preferences - sync to junction table
        if 'preferences' in updates:
            pref_value = updates['preferences']
            if pref_value is None:
                pref_value = ''
            updates['preferences'] = pref_value

            # Also update junction table
            pref_codes = [c.strip() for c in pref_value.split(',') if c.strip()] if pref_value else []
            set_reservation_characteristics_by_codes(reservation_id, pref_codes)

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

        # Handle tag_ids separately (junction table, not a column)
        if 'tag_ids' in data:
            tag_ids = data['tag_ids']
            if isinstance(tag_ids, list):
                set_reservation_tags(reservation_id, tag_ids)
                sync_reservation_tags_to_customer(reservation_id, tag_ids, replace=True)

        # Validate state_id before the try block (early return on invalid)
        if 'state_id' in data:
            try:
                data['_validated_state_id'] = int(data['state_id'])
            except (ValueError, TypeError):
                return api_error('ID de estado no válido')

        try:
            # Handle state change (state_id = ID of the new state)
            if '_validated_state_id' in data:
                from flask_login import current_user
                from models.reservation import get_reservation_with_details
                from models.reservation_state import add_reservation_state, remove_reservation_state

                state_id = data['_validated_state_id']
                with get_db() as conn:
                    state = conn.execute(
                        'SELECT name FROM beach_reservation_states WHERE id = ?',
                        (state_id,)
                    ).fetchone()
                if not state:
                    return api_error('Estado no encontrado', 404)

                full_res = get_reservation_with_details(reservation_id)
                current_states = full_res.get('current_states', '') if full_res else ''
                current_state_list = [s.strip() for s in current_states.split(',') if s.strip()]
                changed_by = current_user.username if current_user else 'system'
                for existing_state in current_state_list:
                    remove_reservation_state(reservation_id, existing_state, changed_by=changed_by)
                add_reservation_state(reservation_id, state['name'], changed_by=changed_by)

            with get_db() as conn:
                if updates:
                    # Build dynamic UPDATE query
                    set_clauses = ', '.join(f'{k} = ?' for k in updates.keys())
                    values = list(updates.values()) + [reservation_id]

                    conn.execute(f'''
                        UPDATE beach_reservations
                        SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', values)
                elif has_tag_changes or has_state_changes:
                    # Only tags/state changed, just touch updated_at
                    conn.execute('''
                        UPDATE beach_reservations
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (reservation_id,))

                conn.commit()

            # Audit log
            after_reservation = get_beach_reservation_by_id(reservation_id)
            after_state = dict(after_reservation) if after_reservation else {}
            log_update('reservation', reservation_id, before=before_state, after=after_state)

            return api_success(
                message='Reserva actualizada',
                reservation_id=reservation_id,
                updated_fields=list(updates.keys())
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

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
            return api_error('Datos requeridos')

        raw_customer_id = data.get('customer_id')
        raw_guest_id = data.get('hotel_guest_id')

        if not raw_customer_id and not raw_guest_id:
            return api_error('customer_id o hotel_guest_id requerido')

        # Validate types: must be positive integers if provided
        new_customer_id = None
        hotel_guest_id = None

        if raw_customer_id:
            valid, new_customer_id, err = validate_positive_integer(
                raw_customer_id, 'customer_id'
            )
            if not valid:
                return api_error(err)

        if raw_guest_id:
            valid, hotel_guest_id, err = validate_positive_integer(
                raw_guest_id, 'hotel_guest_id'
            )
            if not valid:
                return api_error(err)

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # If hotel_guest_id provided, create customer first
        if hotel_guest_id and not new_customer_id:
            try:
                result = create_customer_from_hotel_guest(hotel_guest_id, {})
                new_customer_id = result['customer_id']
            except ValueError as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                return api_error('Solicitud inválida')
            except Exception as e:
                current_app.logger.error(f'Error: {e}', exc_info=True)
                return api_error('Error al crear cliente desde huesped', 500)

        # Validate customer exists
        customer = get_customer_by_id(new_customer_id)
        if not customer:
            return api_error('Cliente no encontrado', 404)

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
                    return api_error(
                        f'El cliente ya tiene reserva para esta fecha (#{existing["ticket_number"]})',
                        409,
                        existing_reservation_id=existing['id']
                    )

        try:
            with get_db() as conn:
                conn.execute('''
                    UPDATE beach_reservations
                    SET customer_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_customer_id, reservation_id))
                conn.commit()

            return api_success(
                message='Cliente actualizado',
                reservation_id=reservation_id,
                customer_id=new_customer_id,
                customer={
                    'id': customer['id'],
                    'first_name': customer.get('first_name'),
                    'last_name': customer.get('last_name'),
                    'full_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                    'customer_type': customer.get('customer_type'),
                    'room_number': customer.get('room_number'),
                    'vip_status': customer.get('vip_status'),
                    'phone': customer.get('phone')
                }
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error al cambiar cliente', 500)
