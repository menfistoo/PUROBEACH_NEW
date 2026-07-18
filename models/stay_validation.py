"""
Validation of beach reservation dates against the hotel stay (interno guests).

Root cause this protects against (room 6103, 2026-07-12): on the guest's
checkout day staff selected the departing guest and created sunbed
reservations for dates AFTER the hotel departure. Those reservations stay
anchored to a finished booking, no post-import repair pass can fix them,
and every morning staff finds the wrong guest on the map.

Two layers:
- check_dates_within_stay(): called at reservation creation / date edit.
  Warns when requested dates fall outside the guest's hotel stay, so the
  frontend can ask for explicit confirmation (override allowed: e.g. the
  guest extended at reception and the PMS import hasn't run yet).
- find_out_of_stay_reservations(): post-import audit that lists current or
  future interno reservations whose hotel booking no longer covers the
  reservation date, so they surface in the import summary instead of being
  discovered on the map.
"""

from typing import Any, Dict, List, Optional

from database import get_db
from models.hotel_guest import booking_base, normalize_guest_name


def _stay_segments_for_customer(conn, customer: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    hotel_guests rows that belong to this interno customer's hotel stay.

    Primary match: all segments of the customer's booking base (this PMS
    re-books on room changes: base-1, base-2... are the same stay).
    Fallback (customer without anchor): rows for the customer's room whose
    normalized guest name matches the customer name.
    """
    ref = (customer.get('booking_reference') or '').strip()
    if ref:
        base = booking_base(ref)
        return conn.execute('''
            SELECT booking_reference, room_number, guest_name,
                   arrival_date, departure_date, nationality, vip_code
            FROM hotel_guests
            WHERE booking_reference = ? OR booking_reference LIKE ?
        ''', (base, base + '-%')).fetchall()

    room = (customer.get('room_number') or '').strip()
    if not room:
        return []
    name = normalize_guest_name(
        f"{customer.get('first_name') or ''} {customer.get('last_name') or ''}".strip()
    )
    if not name:
        return []
    rows = conn.execute('''
        SELECT booking_reference, room_number, guest_name,
               arrival_date, departure_date, nationality, vip_code
        FROM hotel_guests
        WHERE room_number = ?
    ''', (room,)).fetchall()
    matched = []
    for r in rows:
        gname = normalize_guest_name(r['guest_name'] or '')
        if not gname:
            continue
        if name in gname or gname in name:
            matched.append(r)
    return matched


def _iso(value) -> str:
    """Normalize DATE column values (date objects or strings) to YYYY-MM-DD."""
    if value is None:
        return ''
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)


def check_dates_within_stay(customer: Optional[Dict[str, Any]],
                            dates: List[str],
                            conn=None) -> Dict[str, Any]:
    """
    Check whether the requested reservation dates fall inside the interno
    customer's hotel stay.

    Returns a dict:
        applicable: False for externos / missing customer (nothing to check).
        known:      True when the guest was found in hotel_guests. When
                    False (pre-arrival booking not yet in the PMS export),
                    validation is skipped and ok=True.
        ok:         True when every date is covered by a stay segment.
        uncovered:  Dates (sorted) not covered by any segment.
        arrival / departure: overall stay window (min arrival, max departure).
        guest_name: display name from the PMS rows (best effort).
    """
    result = {
        'applicable': False, 'known': False, 'ok': True,
        'uncovered': [], 'arrival': None, 'departure': None,
        'guest_name': None,
    }
    if not customer or customer.get('customer_type') != 'interno' or not dates:
        return result
    result['applicable'] = True

    def _run(c):
        segments = _stay_segments_for_customer(c, customer)
        if not segments:
            return  # pre-arrival: PMS doesn't know this guest yet, allow
        result['known'] = True
        windows = []
        for s in segments:
            arr, dep = _iso(s['arrival_date']), _iso(s['departure_date'])
            if arr and dep:
                windows.append((arr, dep))
            if not result['guest_name'] and s['guest_name']:
                result['guest_name'] = s['guest_name']
        if not windows:
            return
        result['arrival'] = min(w[0] for w in windows)
        result['departure'] = max(w[1] for w in windows)
        uncovered = [d for d in dates
                     if not any(w[0] <= d <= w[1] for w in windows)]
        result['uncovered'] = sorted(uncovered)
        result['ok'] = not uncovered

    if conn is not None:
        _run(conn)
    else:
        with get_db() as c:
            _run(c)
    return result


def outside_stay_message(stay: Dict[str, Any]) -> str:
    """Build the Spanish warning message for an out-of-stay attempt."""
    fechas = ', '.join(_ddmm(d) for d in stay.get('uncovered', []))
    dep = _ddmm(stay.get('departure'))
    who = (stay.get('guest_name') or 'El huésped').strip()
    msg = f"{who} sale del hotel el {dep}" if dep else f"{who} no tiene estancia activa"
    return (f"{msg} según el PMS. Las fechas {fechas} quedan fuera de su "
            f"estancia. Verifique que el cliente seleccionado es el huésped "
            f"actual de la habitación.")


def _ddmm(iso_date: Optional[str]) -> str:
    """YYYY-MM-DD -> DD/MM (display helper, tolerant of bad input)."""
    if not iso_date:
        return ''
    parts = str(iso_date).split('-')
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}"
    return str(iso_date)


def get_customer_stay_summary(customer: Optional[Dict[str, Any]],
                              conn=None) -> Optional[Dict[str, Any]]:
    """
    Summary of the interno customer's OWN hotel stay, matched via booking
    segments (or room+name fallback) — never borrowed from whoever occupies
    the room today.

    Used by the reservation detail panel: it used to fall back to the
    room's current main guest, gluing another guest's dates/reservation
    number under a stale customer's name (room 6103 / Bingham case).

    Returns None when the guest is unknown to the PMS, else:
        {'arrival', 'departure', 'booking_reference', 'guest_name',
         'nationality', 'vip_code', 'status': 'current'|'departed'|'upcoming'}
    booking_reference/nationality/vip_code come from the segment covering
    today when there is one, else from the latest segment.
    """
    if not customer or customer.get('customer_type') != 'interno':
        return None
    from utils.datetime_helpers import get_today
    today = get_today().isoformat()

    def _run(c):
        segments = _stay_segments_for_customer(c, customer)
        if not segments:
            return None
        windows = [(_iso(s['arrival_date']), _iso(s['departure_date']), s)
                   for s in segments
                   if s['arrival_date'] and s['departure_date']]
        if not windows:
            return None
        arrival = min(w[0] for w in windows)
        departure = max(w[1] for w in windows)
        # Segment covering today, else the one ending last.
        seg = next((s for a, d, s in windows if a <= today <= d), None)
        if seg is None:
            seg = max(windows, key=lambda w: w[1])[2]
        if departure < today:
            status = 'departed'
        elif arrival > today:
            status = 'upcoming'
        else:
            status = 'current'
        return {
            'arrival': arrival,
            'departure': departure,
            'booking_reference': seg['booking_reference'],
            'guest_name': seg['guest_name'],
            'nationality': seg['nationality'],
            'vip_code': seg['vip_code'],
            'status': status,
        }

    if conn is not None:
        return _run(conn)
    with get_db() as c:
        return _run(c)


def find_out_of_stay_reservations(conn=None) -> List[Dict[str, Any]]:
    """
    Post-import audit: current/future interno reservations whose hotel
    booking is KNOWN to the PMS but has no segment covering the
    reservation date (e.g. sunbeds reserved past the guest's checkout).

    Reservations in availability-releasing states (cancelada, no-show,
    liberada) are excluded — those are already resolved.

    Each entry carries a 'severity':
      'departed':        the guest's last known departure is already in the
                         past — the guest is gone per PMS but still holds
                         sunbeds (high confidence, the room-6103 case).
      'beyond_departure': the reservation extends past a departure that is
                         still in the future — often self-heals when the PMS
                         emits the next segment (room change / extension),
                         so it is lower confidence.

    Returns a list of dicts: reservation_id, ticket_number,
    reservation_date, customer_id, customer_name, room_number,
    booking_reference, stay_departure, severity.
    """
    from utils.datetime_helpers import get_today
    today = get_today().isoformat()
    flagged: List[Dict[str, Any]] = []

    def _run(c):
        rows = c.execute('''
            SELECT r.id AS reservation_id, r.ticket_number, r.reservation_date,
                   r.booking_reference AS res_ref,
                   cu.id AS customer_id, cu.room_number,
                   cu.booking_reference AS cust_ref,
                   TRIM(cu.first_name || ' ' || COALESCE(cu.last_name, '')) AS customer_name,
                   cu.customer_type, cu.first_name, cu.last_name
            FROM beach_reservations r
            JOIN beach_customers cu ON cu.id = r.customer_id
            JOIN beach_reservation_states s ON s.id = r.state_id
            WHERE cu.customer_type = 'interno'
              AND r.reservation_date >= ?
              AND s.is_availability_releasing = 0
            ORDER BY r.reservation_date, r.id
        ''', (today,)).fetchall()

        for row in rows:
            customer = {
                'customer_type': 'interno',
                'booking_reference': row['res_ref'] or row['cust_ref'],
                'room_number': row['room_number'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
            }
            stay = check_dates_within_stay(
                customer, [_iso(row['reservation_date'])], conn=c)
            if stay['applicable'] and stay['known'] and not stay['ok']:
                departed = bool(stay['departure']) and stay['departure'] < today
                flagged.append({
                    'reservation_id': row['reservation_id'],
                    'ticket_number': row['ticket_number'],
                    'reservation_date': _iso(row['reservation_date']),
                    'customer_id': row['customer_id'],
                    'customer_name': row['customer_name'],
                    'room_number': row['room_number'],
                    'booking_reference': customer['booking_reference'],
                    'stay_departure': stay['departure'],
                    'severity': 'departed' if departed else 'beyond_departure',
                })

    if conn is not None:
        _run(conn)
    else:
        with get_db() as c:
            _run(c)
    return flagged
