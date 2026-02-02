"""
Map reservation edit API routes - Date operations.
Availability checking and date changes.
"""

from datetime import datetime

from flask import current_app, request, Response, Blueprint
from flask_login import login_required

from utils.decorators import permission_required
from utils.validators import validate_integer_list, validate_date_string
from utils.api_response import api_success, api_error
from models.furniture import get_all_furniture
from models.reservation import (
    check_furniture_availability_bulk,
    get_beach_reservation_by_id
)
from database import get_db


def register_routes(bp: Blueprint) -> None:
    """Register date-related reservation edit routes on the blueprint."""

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
            return api_error('Datos requeridos')

        # Validate new_date: required, valid YYYY-MM-DD
        valid, new_date, err = validate_date_string(data.get('new_date'), 'new_date')
        if not valid:
            return api_error(err)

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

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
            return api_success(
                all_available=False,
                some_available=False,
                available_furniture=[],
                unavailable_furniture=[],
                conflicts=[],
                warning='No hay mobiliario asignado'
            )

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

        return api_success(
            all_available=all_available,
            some_available=some_available,
            available_furniture=available,
            unavailable_furniture=unavailable,
            conflicts=conflicts,
            total_furniture=len(furniture_ids),
            has_alternatives=has_alternatives,
            needs_reassignment=not all_available and some_available
        )

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
            return api_error('Datos requeridos')

        new_furniture_ids = data.get('furniture_ids')
        clear_furniture = data.get('clear_furniture', False)

        # Validate new_date: required, valid YYYY-MM-DD
        valid, new_date, err = validate_date_string(data.get('new_date'), 'new_date')
        if not valid:
            return api_error(err)

        # Validate furniture_ids if provided: must be list of positive integers
        if new_furniture_ids is not None:
            valid, new_furniture_ids, err = validate_integer_list(
                new_furniture_ids, 'furniture_ids', allow_empty=True
            )
            if not valid:
                return api_error(err)

        # Get reservation
        reservation = get_beach_reservation_by_id(reservation_id)
        if not reservation:
            return api_error('Reserva no encontrada', 404)

        current_date = reservation.get('reservation_date') or reservation.get('start_date')

        # If same date, no change needed
        if new_date == current_date:
            return api_success(message='Sin cambios')

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

                    return api_success(
                        cleared_furniture=True,
                        new_date=new_date,
                        reservation_id=reservation_id
                    )

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
                        return api_error(
                            'El mobiliario no esta disponible en la nueva fecha',
                            409,
                            conflicts=conflict_ids
                        )

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

            return api_success(
                message='Fecha actualizada',
                reservation_id=reservation_id,
                old_date=current_date,
                new_date=new_date
            )

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)
