"""
Beach reservation routes.
Handles reservation list view, quick edit, and Excel export.
Creation is done via the LiveMap.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from utils.decorators import permission_required
from models.reservation import (
    get_reservations_filtered, get_reservation_with_details,
    get_reservation_stats, get_reservation_states,
    delete_reservation, cancel_beach_reservation, get_status_history
)
from datetime import date
import io

reservations_bp = Blueprint('reservations', __name__)


@reservations_bp.route('/')
@login_required
@permission_required('beach.reservations.view')
def list():
    """Display reservation list with filters."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    customer_type = request.args.get('type', '')
    state = request.args.get('state', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    if not date_from:
        date_from = date.today().strftime('%Y-%m-%d')

    result = get_reservations_filtered(
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        customer_type=customer_type if customer_type else None,
        state=state if state else None,
        search=search if search else None,
        page=page
    )

    stats = get_reservation_stats(date_from, date_to if date_to else date_from)
    states = get_reservation_states()

    return render_template(
        'beach/reservations.html',
        reservations=result['items'],
        total=result['total'],
        page=result['page'],
        pages=result['pages'],
        stats=stats,
        states=states,
        date_from=date_from,
        date_to=date_to,
        type_filter=customer_type,
        state_filter=state,
        search=search
    )


@reservations_bp.route('/create')
@login_required
@permission_required('beach.reservations.create')
def create():
    """Redirect to map for reservation creation."""
    # Pass any query params to the map (date, customer_id, etc.)
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    flash('Use el mapa interactivo para crear nuevas reservas', 'info')
    return redirect(url_for('beach.map', date=selected_date))


@reservations_bp.route('/export')
@login_required
@permission_required('beach.reservations.view')
def export():
    """Export reservations to Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        flash('Error: openpyxl no está instalado', 'error')
        return redirect(url_for('beach.reservations'))

    # Get filter parameters
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    customer_type = request.args.get('type', '')
    state = request.args.get('state', '')
    search = request.args.get('search', '')

    if not date_from:
        date_from = date.today().strftime('%Y-%m-%d')

    # Get all reservations (no pagination for export)
    result = get_reservations_filtered(
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        customer_type=customer_type if customer_type else None,
        state=state if state else None,
        search=search if search else None,
        page=1,
        per_page=10000  # Large number to get all
    )

    reservations = result['items']

    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Reservas"

    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A3A5C", end_color="1A3A5C", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Headers
    headers = [
        "Ticket", "Cliente", "Tipo", "Habitación", "Fecha",
        "Personas", "Estado", "Mobiliario", "Precio", "Pagado", "Notas"
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Data rows
    for row_idx, res in enumerate(reservations, 2):
        ws.cell(row=row_idx, column=1, value=res.get('ticket_number') or f"#{res['id']}")
        ws.cell(row=row_idx, column=2, value=res.get('customer_name', ''))
        ws.cell(row=row_idx, column=3, value=res.get('customer_type', ''))
        ws.cell(row=row_idx, column=4, value=res.get('room_number', ''))
        ws.cell(row=row_idx, column=5, value=res.get('reservation_date') or res.get('start_date', ''))
        ws.cell(row=row_idx, column=6, value=res.get('num_people', 0))
        ws.cell(row=row_idx, column=7, value=res.get('current_state', ''))
        ws.cell(row=row_idx, column=8, value=res.get('furniture_names', ''))
        ws.cell(row=row_idx, column=9, value=res.get('final_price', 0))
        ws.cell(row=row_idx, column=10, value="Sí" if res.get('paid') else "No")
        ws.cell(row=row_idx, column=11, value=res.get('observations', ''))

        # Apply border to data cells
        for col in range(1, 12):
            ws.cell(row=row_idx, column=col).border = thin_border

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width

    # Save to buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Generate filename
    filename = f"reservas_{date_from}"
    if date_to and date_to != date_from:
        filename += f"_a_{date_to}"
    filename += ".xlsx"

    return Response(
        output.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reservations_bp.route('/<int:reservation_id>')
@login_required
@permission_required('beach.reservations.view')
def detail(reservation_id):
    """Display reservation detail page."""
    reservation = get_reservation_with_details(reservation_id)
    if not reservation:
        flash('Reserva no encontrada', 'error')
        return redirect(url_for('beach.reservations'))

    states = get_reservation_states()
    history = get_status_history(reservation_id)

    return render_template(
        'beach/reservation_unified.html',
        reservation=reservation,
        states=states,
        history=history
    )


@reservations_bp.route('/<int:reservation_id>/edit', methods=['GET'])
@login_required
@permission_required('beach.reservations.edit')
def edit(reservation_id):
    """Redirect to unified detail/edit page."""
    # Unified page handles both view and edit
    return redirect(url_for('beach.reservations_detail', reservation_id=reservation_id))


@reservations_bp.route('/<int:reservation_id>/delete', methods=['POST'])
@login_required
@permission_required('beach.reservations.delete')
def delete(reservation_id):
    """Delete reservation."""
    try:
        delete_reservation(reservation_id)
        flash('Reserva eliminada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('beach.reservations'))


@reservations_bp.route('/<int:reservation_id>/cancel', methods=['POST'])
@login_required
@permission_required('beach.reservations.change_state')
def cancel(reservation_id):
    """Cancel reservation."""
    reason = request.form.get('reason', '')

    try:
        cancel_beach_reservation(
            reservation_id,
            cancelled_by=current_user.username if current_user else 'system',
            notes=reason
        )
        flash('Reserva cancelada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al cancelar: {str(e)}', 'error')

    return redirect(url_for('beach.reservations_detail', reservation_id=reservation_id))
