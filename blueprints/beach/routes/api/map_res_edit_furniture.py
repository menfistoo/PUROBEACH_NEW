"""
Map reservation edit API routes - Furniture operations.
Furniture reassignment and lock toggle.
"""

from flask import current_app, request, Response, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from utils.api_response import api_success, api_error
from models.furniture import get_all_furniture
from models.reservation import (
    check_furniture_availability_bulk,
    get_beach_reservation_by_id
)
from database import get_db


def register_routes(bp: Blueprint) -> None:
    """Register furniture-related reservation edit routes on the blueprint."""

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
            return api_error('Datos requeridos')

        furniture_ids = data.get('furniture_ids', [])
        date_str = data.get('date')

        # Validation
        if not furniture_ids or not isinstance(furniture_ids, list):
            return api_error('Mobiliario requerido')

        # Get existing reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        # Check if furniture is locked
        if reservation.get('is_furniture_locked'):
            return api_error(
                'locked', 403,
                message='El mobiliario de esta reserva esta bloqueado'
            )

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
                    return api_error(
                        'Algunos mobiliarios no estan disponibles',
                        409,
                        conflicts=conflict_ids
                    )

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
            return api_error(
                f'Capacidad insuficiente: {total_capacity} personas vs {num_people} requeridas',
                400,
                total_capacity=total_capacity,
                num_people=num_people
            )

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

            return api_success(
                message='Mobiliario actualizado exitosamente',
                warning=capacity_warning,
                reservation_id=reservation_id,
                date=date_str,
                furniture=updated_furniture,
                total_capacity=total_capacity,
                num_people=num_people
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error al actualizar mobiliario', 500)

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
            return api_error('Campo "locked" requerido')

        locked = bool(data['locked'])

        from models.reservation_crud import toggle_furniture_lock
        result = toggle_furniture_lock(reservation_id, locked)

        if not result['success']:
            return api_error(result.get('error', 'Error desconocido'), 404)

        return api_success(
            message=result.get('message'),
            reservation_id=result.get('reservation_id'),
            is_furniture_locked=result.get('is_furniture_locked')
        )
