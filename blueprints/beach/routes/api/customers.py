"""
Customer and hotel guest API routes.
"""

from flask import current_app, request
from flask_login import login_required
from utils.decorators import permission_required
from utils.audit import log_create, log_update
from utils.api_response import api_success, api_error
from models.customer import (
    find_duplicates, get_customer_by_id, get_customer_preferences,
    create_customer, set_customer_preferences, search_customers_unified,
    create_customer_from_hotel_guest, get_customers_filtered
)
from models.characteristic import get_all_characteristics
from models.reservation import sync_preferences_to_customer
from models.reservation import get_customer_reservation_history, get_customer_preferred_furniture
from models.hotel_guest import get_guests_by_room, search_guests
from utils.datetime_helpers import get_today


def register_routes(bp):
    """Register customer and hotel guest API routes on the blueprint."""

    # ============================================================================
    # CUSTOMER API ROUTES
    # ============================================================================

    @bp.route('/customers/list')
    @login_required
    @permission_required('beach.customers.view')
    def customers_list():
        """Get filtered customers list for auto-filter (AJAX endpoint)."""
        search = request.args.get('search', '')
        customer_type = request.args.get('type', '')
        vip_only = request.args.get('vip', '') == '1'

        # Pagination parameters with clamping
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        result = get_customers_filtered(
            search=search if search else None,
            customer_type=customer_type if customer_type else None,
            vip_only=vip_only,
            limit=limit,
            offset=offset
        )

        # Format customers for JSON response
        customers = []
        for c in result['customers']:
            customers.append({
                'id': c['id'],
                'first_name': c['first_name'],
                'last_name': c.get('last_name', ''),
                'customer_type': c['customer_type'],
                'phone': c.get('phone'),
                'email': c.get('email'),
                'room_number': c.get('room_number'),
                'vip_status': c.get('vip_status', 0),
                'reservation_count': c.get('reservation_count', 0)
            })

        return api_success(
            customers=customers,
            total=result['total'],
            pagination={
                'limit': limit,
                'offset': offset,
                'count': len(customers),
                'has_more': len(customers) == limit
            }
        )

    @bp.route('/customers/search')
    @login_required
    @permission_required('beach.customers.view')
    def customers_search():
        """Search customers and hotel guests for autocomplete (unified search)."""
        query = request.args.get('q', '')
        customer_type = request.args.get('type', None)

        if len(query) < 2:
            return api_success(customers=[])

        results = search_customers_unified(query, customer_type)

        formatted_results = []
        for c in results:
            if c.get('source') == 'hotel_guest':
                formatted_results.append({
                    'id': c['id'],
                    'source': 'hotel_guest',
                    'guest_name': c.get('guest_name', ''),
                    'display_name': f"{c.get('guest_name', '')} (Hab. {c['room_number']})",
                    'customer_type': 'interno',
                    'room_number': c['room_number'],
                    'phone': c.get('phone'),
                    'email': c.get('email'),
                    'vip_code': c.get('vip_code'),
                    'departure_date': c.get('departure_date'),
                    'arrival_date': c.get('arrival_date'),
                    'nationality': c.get('nationality'),
                    'num_adults': c.get('num_adults', 1),
                    'num_children': c.get('num_children', 0),
                    'notes': c.get('notes'),
                    'is_main_guest': c.get('is_main_guest', 0),
                    'room_guest_count': c.get('room_guest_count', 1),
                    'booking_reference': c.get('booking_reference'),
                    'is_checkin_today': c.get('is_checkin_today', False),
                    'is_checkout_today': c.get('is_checkout_today', False)
                })
            else:
                preferences = get_customer_preferences(c['id'])
                pref_codes = [p['code'] for p in preferences]

                customer_data = {
                    'id': c['id'],
                    'source': 'customer',
                    'first_name': c['first_name'],
                    'last_name': c.get('last_name', ''),
                    'display_name': f"{c['first_name']} {c.get('last_name', '')}".strip() +
                                   (f" (Hab. {c['room_number']})" if c.get('room_number') and c['room_number'] != 'None' else ''),
                    'customer_type': c['customer_type'],
                    'room_number': c.get('room_number') if c.get('room_number') != 'None' else None,
                    'phone': c.get('phone'),
                    'email': c.get('email'),
                    'vip_status': c.get('vip_status', 0),
                    'notes': c.get('notes'),
                    'total_visits': c.get('total_visits', 0),
                    'total_spent': c.get('total_spent', 0),
                    'last_visit': c.get('last_visit'),
                    'preferences': pref_codes,
                    'is_checkin_today': c.get('is_checkin_today', False),
                    'is_checkout_today': c.get('is_checkout_today', False)
                }

                if c['customer_type'] == 'interno' and c.get('room_number'):
                    hotel_guests = get_guests_by_room(c['room_number'], get_today())
                    if hotel_guests:
                        full_name = f"{c['first_name']} {c.get('last_name', '')}".strip().upper()
                        matching_guest = None
                        for hg in hotel_guests:
                            if hg['guest_name'].upper() == full_name:
                                matching_guest = hg
                                break
                        if not matching_guest:
                            matching_guest = next((hg for hg in hotel_guests if hg.get('is_main_guest')), hotel_guests[0])

                        customer_data['arrival_date'] = matching_guest.get('arrival_date')
                        customer_data['departure_date'] = matching_guest.get('departure_date')
                        customer_data['nationality'] = matching_guest.get('nationality')
                        customer_data['booking_reference'] = matching_guest.get('booking_reference')
                        customer_data['room_guest_count'] = len(hotel_guests)
                        customer_data['vip_code'] = matching_guest.get('vip_code')

                formatted_results.append(customer_data)

        return api_success(customers=formatted_results)

    @bp.route('/customers/check-duplicates')
    @login_required
    @permission_required('beach.customers.view')
    def customers_check_duplicates():
        """Check for duplicate customers."""
        phone = request.args.get('phone', '')
        customer_type = request.args.get('type', 'externo')
        room_number = request.args.get('room', '')

        duplicates = find_duplicates(phone, customer_type, room_number)

        return api_success(duplicates=[{
            'id': d['id'],
            'first_name': d['first_name'],
            'last_name': d['last_name'],
            'customer_type': d['customer_type'],
            'room_number': d['room_number'],
            'phone': d['phone'],
            'email': d['email']
        } for d in duplicates])

    @bp.route('/customers/from-hotel-guest', methods=['POST'])
    @login_required
    @permission_required('beach.customers.create')
    def customers_from_hotel_guest():
        """Convert a hotel guest to a beach customer with optional additional data."""
        data = request.get_json()
        hotel_guest_id = data.get('hotel_guest_id')

        if not hotel_guest_id:
            return api_error('ID de huésped requerido', 400)

        additional_data = {}
        if data.get('phone'):
            additional_data['phone'] = data['phone'].strip()
        if data.get('email'):
            additional_data['email'] = data['email'].strip()
        if data.get('language'):
            additional_data['language'] = data['language'].strip()
        if data.get('country_code'):
            additional_data['country_code'] = data['country_code'].strip()
        if data.get('notes'):
            additional_data['notes'] = data['notes'].strip()
        if data.get('preferences'):
            additional_data['preferences'] = [int(p) for p in data['preferences'] if p]

        try:
            result = create_customer_from_hotel_guest(hotel_guest_id, additional_data)
            customer = result['customer']

            preferences = get_customer_preferences(customer['id'])
            pref_codes = [p['code'] for p in preferences]

            return api_success(action=result['action'], customer={
                'id': customer['id'],
                'source': 'customer',
                'first_name': customer['first_name'],
                'last_name': customer.get('last_name', ''),
                'display_name': f"{customer['first_name']} {customer.get('last_name', '')}".strip(),
                'customer_type': customer['customer_type'],
                'room_number': customer.get('room_number'),
                'phone': customer.get('phone'),
                'email': customer.get('email'),
                'vip_status': customer.get('vip_status', 0),
                'language': customer.get('language'),
                'country_code': customer.get('country_code'),
                'notes': customer.get('notes'),
                'preferences': pref_codes
            })
        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Solicitud inválida', 400)
        except Exception:
            return api_error('Error al crear cliente', 500)

    @bp.route('/customers/create', methods=['POST'])
    @login_required
    @permission_required('beach.customers.create')
    def customers_create():
        """Create a new customer via API (for inline form)."""
        data = request.get_json()

        customer_type = data.get('customer_type')
        first_name = data.get('first_name', '').strip()

        if not customer_type or customer_type not in ['interno', 'externo']:
            return api_error('Tipo de cliente inválido', 400)

        if not first_name:
            return api_error('El nombre es requerido', 400)

        room_number = data.get('room_number', '').strip() or None
        if customer_type == 'interno' and not room_number:
            return api_error('El número de habitación es requerido para clientes internos', 400)

        phone = data.get('phone', '').strip() or None
        email = data.get('email', '').strip() or None
        if customer_type == 'externo' and not (phone or email):
            return api_error('Se requiere teléfono o email para clientes externos', 400)

        try:
            customer_id = create_customer(
                customer_type=customer_type,
                first_name=first_name,
                last_name=data.get('last_name', '').strip() or None,
                email=email,
                phone=phone,
                room_number=room_number,
                notes=data.get('notes', '').strip() or None,
                language=data.get('language', '').strip() or None,
                country_code=data.get('country_code', '+34').strip()
            )

            preference_ids = data.get('preferences', [])
            if preference_ids:
                set_customer_preferences(customer_id, [int(p) for p in preference_ids if p])

            customer = get_customer_by_id(customer_id)

            preferences = get_customer_preferences(customer_id)
            pref_codes = [p['code'] for p in preferences]

            # Log audit entry for customer creation
            log_create('customer', customer_id, data={
                'first_name': customer['first_name'],
                'last_name': customer.get('last_name'),
                'customer_type': customer['customer_type'],
                'room_number': customer.get('room_number'),
                'phone': customer.get('phone'),
                'email': customer.get('email'),
                'vip_status': customer.get('vip_status', 0),
                'preferences': pref_codes
            })

            return api_success(customer={
                'id': customer['id'],
                'source': 'customer',
                'first_name': customer['first_name'],
                'last_name': customer.get('last_name', ''),
                'display_name': f"{customer['first_name']} {customer.get('last_name', '')}".strip(),
                'customer_type': customer['customer_type'],
                'room_number': customer.get('room_number'),
                'phone': customer.get('phone'),
                'email': customer.get('email'),
                'vip_status': customer.get('vip_status', 0),
                'language': customer.get('language'),
                'country_code': customer.get('country_code'),
                'notes': customer.get('notes'),
                'preferences': pref_codes
            })
        except ValueError as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Solicitud inválida', 400)
        except Exception:
            return api_error('Error al crear cliente', 500)

    @bp.route('/customers/<int:customer_id>')
    @login_required
    @permission_required('beach.customers.view')
    def get_customer(customer_id):
        """Get customer by ID for JSON API."""
        customer = get_customer_by_id(customer_id)
        if not customer:
            return api_error('Cliente no encontrado', 404)

        preferences = get_customer_preferences(customer_id)
        pref_codes = [p['code'] for p in preferences]

        return api_success(customer={
            'id': customer['id'],
            'source': 'customer',
            'first_name': customer['first_name'],
            'last_name': customer.get('last_name', ''),
            'display_name': f"{customer['first_name']} {customer.get('last_name', '')}".strip(),
            'customer_type': customer['customer_type'],
            'room_number': customer.get('room_number'),
            'phone': customer.get('phone'),
            'email': customer.get('email'),
            'vip_status': customer.get('vip_status', 0),
            'language': customer.get('language'),
            'country_code': customer.get('country_code'),
            'notes': customer.get('notes'),
            'preferences': pref_codes
        })

    @bp.route('/customers/<int:customer_id>/history')
    @login_required
    @permission_required('beach.customers.view')
    def customer_history(customer_id):
        """Get reservation history for a customer."""
        limit = request.args.get('limit', 5, type=int)
        history = get_customer_reservation_history(customer_id, limit=min(limit, 20))

        return api_success(customer_id=customer_id, history=history, count=len(history))

    @bp.route('/customers/<int:customer_id>/preferred-furniture')
    @login_required
    @permission_required('beach.customers.view')
    def customer_preferred_furniture(customer_id):
        """Get customer's preferred furniture based on history."""
        limit = request.args.get('limit', 5, type=int)

        try:
            preferred = get_customer_preferred_furniture(customer_id, limit=limit)
            return api_success(preferred_furniture=preferred)
        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/customers/create-from-guest', methods=['POST'])
    @login_required
    @permission_required('beach.customers.create')
    def create_customer_from_guest():
        """Create a beach customer from a hotel guest."""
        data = request.get_json()
        hotel_guest_id = data.get('hotel_guest_id')

        if not hotel_guest_id:
            return api_error('hotel_guest_id requerido', 400)

        try:
            result = create_customer_from_hotel_guest(hotel_guest_id)

            if result:
                # Log audit entry for customer creation from hotel guest
                customer = result.get('customer', result)
                log_create('customer', customer.get('id', result.get('id')), data={
                    'first_name': customer.get('first_name'),
                    'last_name': customer.get('last_name'),
                    'customer_type': customer.get('customer_type'),
                    'room_number': customer.get('room_number'),
                    'phone': customer.get('phone'),
                    'email': customer.get('email'),
                    'source_hotel_guest_id': hotel_guest_id
                })

                return api_success(customer_id=result['id'], customer=result)
            else:
                return api_error('Error al crear cliente', 500)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    # ============================================================================
    # PREFERENCES API ROUTES
    # ============================================================================

    @bp.route('/preferences')
    @login_required
    @permission_required('beach.customers.view')
    def list_preferences():
        """Get all available characteristics (unified preferences)."""
        active_only = request.args.get('active', 'true').lower() == 'true'
        characteristics = get_all_characteristics(active_only=active_only)

        return api_success(preferences=[{
            'id': c['id'],
            'code': c['code'],
            'name': c['name'],
            'description': c.get('description'),
            'icon': c.get('icon'),
            'color': c.get('color')
        } for c in characteristics])

    @bp.route('/tags')
    @login_required
    @permission_required('beach.customers.view')
    def list_tags():
        """Get all available tags."""
        from models.tag import get_all_tags
        active_only = request.args.get('active', 'true').lower() == 'true'
        tags = get_all_tags(active_only=active_only)

        return api_success(tags=[{
            'id': t['id'],
            'name': t['name'],
            'color': t.get('color', '#6C757D'),
            'description': t.get('description')
        } for t in tags])

    @bp.route('/customers/<int:customer_id>/preferences', methods=['PUT'])
    @login_required
    @permission_required('beach.customers.edit')
    def update_customer_preferences(customer_id):
        """
        Update customer preferences with bidirectional sync.
        Updates the customer profile and syncs to all active/future reservations.

        Request body:
            preference_codes: List of preference codes (e.g., ['pref_sombra', 'pref_vip'])

        Returns:
            JSON with success status and number of reservations updated
        """
        data = request.get_json()

        if not data:
            return api_error('Datos requeridos', 400)

        preference_codes = data.get('preference_codes', [])

        # Validate customer exists
        customer = get_customer_by_id(customer_id)
        if not customer:
            return api_error('Cliente no encontrado', 404)

        # Validate preference codes
        if not isinstance(preference_codes, list):
            return api_error('preference_codes debe ser una lista', 400)

        try:
            # Capture before state for audit log
            current_prefs = get_customer_preferences(customer_id)
            before_pref_codes = [p['code'] for p in current_prefs]

            # Convert list to CSV for sync function
            preferences_csv = ','.join(preference_codes) if preference_codes else ''

            # Sync to customer profile
            success = sync_preferences_to_customer(customer_id, preferences_csv, replace=True)

            if success:
                # Also sync to all active/future reservations
                from models.characteristic_assignments import sync_customer_preferences_to_reservations
                reservations_updated = sync_customer_preferences_to_reservations(customer_id, preferences_csv)

                # Get updated preferences for response
                updated_prefs = get_customer_preferences(customer_id)

                # Log audit entry for customer preferences update
                log_update('customer', customer_id,
                    before={
                        'first_name': customer['first_name'],
                        'last_name': customer.get('last_name'),
                        'preferences': before_pref_codes
                    },
                    after={
                        'first_name': customer['first_name'],
                        'last_name': customer.get('last_name'),
                        'preferences': preference_codes
                    }
                )

                return api_success(
                    customer_id=customer_id,
                    preferences=[{
                        'id': p['id'],
                        'code': p['code'],
                        'name': p['name'],
                        'icon': p.get('icon')
                    } for p in updated_prefs],
                    reservations_updated=reservations_updated,
                    message=f'Preferencias actualizadas ({reservations_updated} reservas sincronizadas)'
                )
            else:
                return api_error('Error al actualizar preferencias', 500)

        except Exception as e:
            current_app.logger.error(f'Error: {e}', exc_info=True)
            return api_error('Error al actualizar preferencias', 500)

    # ============================================================================
    # HOTEL GUEST API ROUTES
    # ============================================================================

    @bp.route('/hotel-guests/lookup')
    @login_required
    @permission_required('beach.customers.view')
    def hotel_guest_lookup():
        """Lookup hotel guests by room number for auto-fill and guest selection."""
        room_number = request.args.get('room', '')
        if not room_number:
            return api_success(guests=[], guest_count=0)

        guests = get_guests_by_room(room_number, get_today())

        return api_success(guest_count=len(guests), guests=[{
            'id': g['id'],
            'source': 'hotel_guest',
            'customer_type': 'interno',
            'guest_name': g['guest_name'],
            'room_number': g['room_number'],
            'arrival_date': g['arrival_date'],
            'departure_date': g['departure_date'],
            'vip_code': g['vip_code'],
            'nationality': g['nationality'],
            'email': g['email'],
            'phone': g['phone'],
            'notes': g.get('notes'),
            'num_adults': g.get('num_adults', 1),
            'num_children': g.get('num_children', 0),
            'is_main_guest': g.get('is_main_guest', 0),
            'booking_reference': g.get('booking_reference')
        } for g in guests])

    @bp.route('/hotel-guests/search')
    @login_required
    @permission_required('beach.customers.view')
    def hotel_guest_search():
        """Search hotel guests for autocomplete - grouped by room."""
        query = request.args.get('q', '')
        if len(query) < 1:
            return api_success(guests=[])

        guests = search_guests(query, limit=20)

        # Group by room number, keeping main guest info
        rooms = {}
        for g in guests:
            room = g['room_number']
            if room not in rooms:
                rooms[room] = {
                    'id': g['id'],
                    'guest_name': g['guest_name'],
                    'room_number': room,
                    'arrival_date': g['arrival_date'],
                    'departure_date': g['departure_date'],
                    'phone': g.get('phone'),
                    'email': g.get('email'),
                    'is_main_guest': g.get('is_main_guest', 0),
                    'guest_count': 1
                }
            else:
                rooms[room]['guest_count'] += 1
                # If this guest is main guest, use their info
                if g.get('is_main_guest', 0) == 1:
                    rooms[room]['id'] = g['id']
                    rooms[room]['guest_name'] = g['guest_name']
                    rooms[room]['phone'] = g.get('phone')
                    rooms[room]['email'] = g.get('email')
                    rooms[room]['is_main_guest'] = 1

        # Sort by room number
        result = sorted(rooms.values(), key=lambda x: x['room_number'])

        return api_success(guests=result)
