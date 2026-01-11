"""Payment reconciliation report routes."""
from datetime import date
from flask import render_template, request, jsonify
from flask_login import login_required

from utils.decorators import permission_required
from models.reports.payment_reconciliation import (
    get_reconciliation_data,
    get_payment_summary,
    mark_reservation_paid
)
from models.zone import get_all_zones


def register_routes(bp):
    """Register payment reconciliation routes."""

    @bp.route('/payment-reconciliation')
    @login_required
    @permission_required('beach.reports.payment_reconciliation')
    def payment_reconciliation_view():
        """Render payment reconciliation report page."""
        selected_date = request.args.get('date', date.today().isoformat())
        zones = get_all_zones()

        return render_template(
            'beach/reports/payment_reconciliation.html',
            selected_date=selected_date,
            zones=zones
        )

    @bp.route('/api/payment-reconciliation')
    @login_required
    @permission_required('beach.reports.payment_reconciliation')
    def payment_reconciliation_data():
        """Get payment reconciliation data as JSON."""
        selected_date = request.args.get('date', date.today().isoformat())
        payment_status = request.args.get('status')
        payment_method = request.args.get('method')
        zone_id = request.args.get('zone_id', type=int)
        has_ticket = request.args.get('has_ticket')

        # Convert has_ticket string to boolean
        if has_ticket == 'true':
            has_ticket = True
        elif has_ticket == 'false':
            has_ticket = False
        else:
            has_ticket = None

        reservations = get_reconciliation_data(
            date=selected_date,
            payment_status=payment_status,
            payment_method=payment_method,
            zone_id=zone_id,
            has_ticket=has_ticket
        )

        summary = get_payment_summary(selected_date)

        return jsonify({
            'success': True,
            'reservations': reservations,
            'summary': summary
        })

    @bp.route('/api/payment-reconciliation/mark-paid', methods=['POST'])
    @login_required
    @permission_required('beach.reports.payment_reconciliation')
    def mark_paid():
        """Mark a reservation as paid."""
        data = request.get_json()

        reservation_id = data.get('reservation_id')
        payment_method = data.get('payment_method')
        ticket_number = data.get('ticket_number', '').strip() or None

        if not reservation_id or not payment_method:
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400

        success = mark_reservation_paid(
            reservation_id=reservation_id,
            payment_method=payment_method,
            ticket_number=ticket_number
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Pago registrado correctamente'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No se pudo registrar el pago'
            }), 400
