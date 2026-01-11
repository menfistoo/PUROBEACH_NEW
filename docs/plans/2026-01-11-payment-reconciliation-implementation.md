# Payment Reconciliation Report - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a daily payment reconciliation report page for cashier verification with filtering, summaries by payment method, and quick mark-as-paid functionality.

**Architecture:** New report route under `/beach/reports/payment-reconciliation` with model functions for queries, a template following design system patterns, and AJAX API for quick payment actions. Uses existing reservation and payment fields.

**Tech Stack:** Flask routes, SQLite queries, Jinja2 templates, Bootstrap 5, vanilla JavaScript for AJAX, Font Awesome 6 icons.

---

## Task 1: Create Model Functions for Payment Reconciliation

**Files:**
- Create: `models/reports/__init__.py`
- Create: `models/reports/payment_reconciliation.py`

**Step 1: Create the reports model directory and init file**

Create directory and `__init__.py`:

```python
"""Reports model module."""
from models.reports.payment_reconciliation import (
    get_reconciliation_data,
    get_payment_summary,
    mark_reservation_paid
)

__all__ = [
    'get_reconciliation_data',
    'get_payment_summary',
    'mark_reservation_paid'
]
```

**Step 2: Create the payment reconciliation model**

Create `models/reports/payment_reconciliation.py`:

```python
"""Payment reconciliation report queries."""
from typing import Any
from database import get_db


def get_reconciliation_data(
    date: str,
    payment_status: str | None = None,
    payment_method: str | None = None,
    zone_id: int | None = None,
    has_ticket: bool | None = None
) -> list[dict[str, Any]]:
    """
    Get reservations for payment reconciliation report.

    Args:
        date: Date string in YYYY-MM-DD format
        payment_status: 'paid', 'pending', or None for all
        payment_method: 'efectivo', 'tarjeta', 'cargo_habitacion', or None
        zone_id: Filter by zone ID, or None for all
        has_ticket: True for with ticket, False for without, None for all

    Returns:
        List of reservation dicts with customer, furniture, zone, payment info
    """
    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT
            r.id,
            r.reservation_type,
            r.final_price,
            r.paid,
            r.payment_method,
            r.payment_ticket_number,
            r.num_people,
            r.created_at,
            c.id as customer_id,
            c.first_name,
            c.last_name,
            c.customer_type,
            f.name as furniture_name,
            ft.name as furniture_type_name,
            z.id as zone_id,
            z.name as zone_name,
            p.name as package_name,
            rs.name as state_name,
            rs.color as state_color
        FROM beach_reservations r
        LEFT JOIN beach_customers c ON r.customer_id = c.id
        LEFT JOIN beach_reservation_furniture rf ON rf.reservation_id = r.id
            AND rf.assignment_date = r.start_date
        LEFT JOIN beach_furniture f ON rf.furniture_id = f.id
        LEFT JOIN beach_furniture_types ft ON f.furniture_type_id = ft.id
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        LEFT JOIN beach_packages p ON r.package_id = p.id
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        LEFT JOIN beach_reservation_states rs_check ON rs_check.id = r.state_id
        WHERE r.start_date = ?
        AND r.reservation_type IN ('paquete', 'consumo_minimo')
        AND COALESCE(rs_check.is_availability_releasing, 0) = 0
    """

    params: list[Any] = [date]

    if payment_status == 'paid':
        query += " AND r.paid = 1"
    elif payment_status == 'pending':
        query += " AND r.paid = 0"

    if payment_method:
        query += " AND r.payment_method = ?"
        params.append(payment_method)

    if zone_id:
        query += " AND z.id = ?"
        params.append(zone_id)

    if has_ticket is True:
        query += " AND r.payment_ticket_number IS NOT NULL AND r.payment_ticket_number != ''"
    elif has_ticket is False:
        query += " AND (r.payment_ticket_number IS NULL OR r.payment_ticket_number = '')"

    query += " ORDER BY r.paid ASC, r.created_at DESC"

    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]

    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_payment_summary(date: str) -> dict[str, Any]:
    """
    Get payment summary totals for a date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        Dict with totals by method and ticket counts
    """
    db = get_db()
    cursor = db.cursor()

    # Get totals by payment method
    cursor.execute("""
        SELECT
            r.payment_method,
            COUNT(*) as count,
            COALESCE(SUM(r.final_price), 0) as total
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.start_date = ?
        AND r.reservation_type IN ('paquete', 'consumo_minimo')
        AND COALESCE(rs.is_availability_releasing, 0) = 0
        AND r.paid = 1
        GROUP BY r.payment_method
    """, (date,))

    method_totals = {
        'efectivo': {'count': 0, 'total': 0.0},
        'tarjeta': {'count': 0, 'total': 0.0},
        'cargo_habitacion': {'count': 0, 'total': 0.0}
    }

    for row in cursor.fetchall():
        method = row[0]
        if method in method_totals:
            method_totals[method] = {'count': row[1], 'total': float(row[2])}

    # Get pending totals
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            COALESCE(SUM(r.final_price), 0) as total
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.start_date = ?
        AND r.reservation_type IN ('paquete', 'consumo_minimo')
        AND COALESCE(rs.is_availability_releasing, 0) = 0
        AND r.paid = 0
    """, (date,))

    pending_row = cursor.fetchone()
    pending = {'count': pending_row[0], 'total': float(pending_row[1])}

    # Get ticket counts (paid with ticket vs paid without)
    cursor.execute("""
        SELECT
            COUNT(*) as total_paid,
            SUM(CASE WHEN r.payment_ticket_number IS NOT NULL
                     AND r.payment_ticket_number != '' THEN 1 ELSE 0 END) as with_ticket
        FROM beach_reservations r
        LEFT JOIN beach_reservation_states rs ON r.state_id = rs.id
        WHERE r.start_date = ?
        AND r.reservation_type IN ('paquete', 'consumo_minimo')
        AND COALESCE(rs.is_availability_releasing, 0) = 0
        AND r.paid = 1
    """, (date,))

    ticket_row = cursor.fetchone()
    tickets = {
        'total_paid': ticket_row[0] or 0,
        'with_ticket': ticket_row[1] or 0,
        'missing': (ticket_row[0] or 0) - (ticket_row[1] or 0)
    }

    return {
        'by_method': method_totals,
        'pending': pending,
        'tickets': tickets
    }


def mark_reservation_paid(
    reservation_id: int,
    payment_method: str,
    ticket_number: str | None = None
) -> bool:
    """
    Mark a reservation as paid.

    Args:
        reservation_id: ID of the reservation
        payment_method: 'efectivo', 'tarjeta', or 'cargo_habitacion'
        ticket_number: Optional POS ticket number

    Returns:
        True if updated successfully
    """
    if payment_method not in ('efectivo', 'tarjeta', 'cargo_habitacion'):
        return False

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE beach_reservations
        SET paid = 1,
            payment_method = ?,
            payment_ticket_number = ?
        WHERE id = ?
        AND paid = 0
    """, (payment_method, ticket_number, reservation_id))

    db.commit()
    return cursor.rowcount > 0
```

**Step 3: Verify the module loads without errors**

Run: `python -c "from models.reports import get_reconciliation_data, get_payment_summary, mark_reservation_paid; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add models/reports/
git commit -m "feat(reports): add payment reconciliation model functions"
```

---

## Task 2: Create Permission Migration

**Files:**
- Modify: `database/migrations/permissions.py`

**Step 1: Read current permissions migration file**

Read file to understand existing migration patterns.

**Step 2: Add payment reconciliation permission migration function**

Add to `database/migrations/permissions.py`:

```python
def migrate_add_payment_reconciliation_permission() -> bool:
    """
    Add payment reconciliation report permission.

    Creates:
    - beach.reports.payment_reconciliation permission
    - Assigns to admin and manager roles
    - Adds to menu under Informes section

    Returns:
        True if migration applied, False if already exists
    """
    db = get_db()
    cursor = db.cursor()

    # Check if already exists
    cursor.execute(
        "SELECT id FROM permissions WHERE code = ?",
        ('beach.reports.payment_reconciliation',)
    )
    if cursor.fetchone():
        print("Payment reconciliation permission already exists")
        return False

    # Find or create Informes parent menu
    cursor.execute(
        "SELECT id FROM permissions WHERE code = ?",
        ('menu.reports',)
    )
    parent_row = cursor.fetchone()

    if not parent_row:
        # Create parent menu item for reports
        cursor.execute("""
            INSERT INTO permissions (code, name, module, is_menu_item, menu_order, menu_icon)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('menu.reports', 'Informes', 'operations', 1, 60, 'fa-chart-bar'))
        parent_id = cursor.lastrowid
    else:
        parent_id = parent_row[0]

    # Create the permission
    cursor.execute("""
        INSERT INTO permissions (
            code, name, module, is_menu_item,
            menu_order, menu_icon, menu_url, parent_permission_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'beach.reports.payment_reconciliation',
        'Conciliacion de Pagos',
        'operations',
        1,
        61,
        'fa-cash-register',
        '/beach/reports/payment-reconciliation',
        parent_id
    ))

    permission_id = cursor.lastrowid

    # Assign to admin and manager roles
    for role_name in ['admin', 'manager']:
        cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
        role_row = cursor.fetchone()
        if role_row:
            cursor.execute("""
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            """, (role_row[0], permission_id))
            print(f"  Assigned to {role_name} role")

    # Also assign parent menu to these roles if not already
    for role_name in ['admin', 'manager']:
        cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
        role_row = cursor.fetchone()
        if role_row:
            cursor.execute("""
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            """, (role_row[0], parent_id))

    db.commit()
    print("Payment reconciliation permission created successfully")
    return True
```

**Step 3: Run the migration**

Run: `python -c "from database.migrations.permissions import migrate_add_payment_reconciliation_permission; migrate_add_payment_reconciliation_permission()"`

Expected: Permission created message

**Step 4: Commit**

```bash
git add database/migrations/permissions.py
git commit -m "feat(permissions): add payment reconciliation report permission"
```

---

## Task 3: Create Report Routes

**Files:**
- Create: `blueprints/beach/routes/reports/__init__.py`
- Create: `blueprints/beach/routes/reports/payment_reconciliation.py`
- Modify: `blueprints/beach/__init__.py` (register routes)

**Step 1: Create reports routes directory and init**

Create `blueprints/beach/routes/reports/__init__.py`:

```python
"""Beach reports routes."""
from flask import Blueprint

reports_bp = Blueprint('beach_reports', __name__, url_prefix='/reports')

from blueprints.beach.routes.reports import payment_reconciliation
payment_reconciliation.register_routes(reports_bp)
```

**Step 2: Create payment reconciliation routes**

Create `blueprints/beach/routes/reports/payment_reconciliation.py`:

```python
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
```

**Step 3: Register reports blueprint in beach module**

Read `blueprints/beach/__init__.py` to find registration point, then add:

```python
# Import and register reports blueprint
from blueprints.beach.routes.reports import reports_bp
beach_bp.register_blueprint(reports_bp)
```

**Step 4: Verify routes load**

Run: `python -c "from blueprints.beach.routes.reports import reports_bp; print('Routes OK')"`

Expected: `Routes OK`

**Step 5: Commit**

```bash
git add blueprints/beach/routes/reports/ blueprints/beach/__init__.py
git commit -m "feat(routes): add payment reconciliation report routes"
```

---

## Task 4: Create Report Template

**Files:**
- Create: `templates/beach/reports/payment_reconciliation.html`

**Step 1: Create the template**

Create `templates/beach/reports/payment_reconciliation.html`:

```html
{% extends "base.html" %}

{% block title %}Conciliacion de Pagos{% endblock %}

{% block extra_css %}
<style>
    .summary-card {
        background: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E8E8E8;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .summary-card .amount {
        font-size: 24px;
        font-weight: 700;
        color: #1A3A5C;
    }
    .summary-card .label {
        font-size: 13px;
        color: #4B5563;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .summary-card .count {
        font-size: 14px;
        color: #9CA3AF;
    }
    .summary-card.efectivo { border-top: 4px solid #4A7C59; }
    .summary-card.tarjeta { border-top: 4px solid #4A90A4; }
    .summary-card.cargo { border-top: 4px solid #D4AF37; }
    .summary-card.pending { border-top: 4px solid #E5A33D; }

    .filter-pills {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .filter-pill {
        padding: 8px 16px;
        border-radius: 20px;
        border: 2px solid #E8E8E8;
        background: #FFFFFF;
        color: #4B5563;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .filter-pill:hover {
        border-color: #D4AF37;
        color: #D4AF37;
    }
    .filter-pill.active {
        background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
        border-color: #D4AF37;
        color: #FFFFFF;
    }

    .ticket-indicator {
        font-size: 13px;
        color: #4B5563;
        background: #F5E6D3;
        padding: 8px 16px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .ticket-indicator .count-good { color: #4A7C59; font-weight: 600; }
    .ticket-indicator .count-missing { color: #C1444F; font-weight: 600; }

    .status-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }
    .status-badge.paid {
        background: #D1FAE5;
        color: #065F46;
    }
    .status-badge.pending {
        background: #FEF3C7;
        color: #92400E;
    }

    .method-badge {
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
    }
    .method-badge.efectivo { background: #D1FAE5; color: #065F46; }
    .method-badge.tarjeta { background: #DBEAFE; color: #1E40AF; }
    .method-badge.cargo_habitacion { background: #FEF3C7; color: #92400E; }

    .btn-cobrar {
        background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
        color: #FFFFFF;
        border: none;
        padding: 6px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
    }
    .btn-cobrar:hover {
        background: linear-gradient(135deg, #E5C04A 0%, #C9A71D 100%);
        color: #FFFFFF;
    }

    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10;
    }
    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid #E8E8E8;
        border-top-color: #D4AF37;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #9CA3AF;
    }
    .empty-state i {
        font-size: 48px;
        margin-bottom: 16px;
        color: #E8E8E8;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h1 class="h3 mb-1" style="color: #1A3A5C;">Conciliacion de Pagos</h1>
            <p class="text-muted mb-0">Verificacion diaria de pagos y tickets</p>
        </div>
        <div class="d-flex align-items-center gap-3">
            <input type="date" id="date-picker" class="form-control"
                   value="{{ selected_date }}" style="width: 180px;">
            <button id="refresh-btn" class="btn btn-outline-primary" aria-label="Actualizar">
                <i class="fas fa-sync-alt"></i>
            </button>
        </div>
    </div>

    <!-- Summary Cards -->
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="summary-card efectivo">
                <div class="label">Efectivo</div>
                <div class="amount" id="summary-efectivo">€0.00</div>
                <div class="count" id="summary-efectivo-count">(0)</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="summary-card tarjeta">
                <div class="label">Tarjeta</div>
                <div class="amount" id="summary-tarjeta">€0.00</div>
                <div class="count" id="summary-tarjeta-count">(0)</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="summary-card cargo">
                <div class="label">Cargo Habitacion</div>
                <div class="amount" id="summary-cargo">€0.00</div>
                <div class="count" id="summary-cargo-count">(0)</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="summary-card pending">
                <div class="label">Pendiente</div>
                <div class="amount" id="summary-pending">€0.00</div>
                <div class="count" id="summary-pending-count">(0)</div>
            </div>
        </div>
    </div>

    <!-- Ticket Indicator -->
    <div class="mb-4">
        <span class="ticket-indicator">
            <i class="fas fa-ticket"></i>
            Tickets: <span class="count-good" id="tickets-registered">0</span>/<span id="tickets-total">0</span> registrados
            <span class="count-missing" id="tickets-missing-text"></span>
        </span>
    </div>

    <!-- Filters -->
    <div class="card mb-4">
        <div class="card-body py-3">
            <div class="row g-3 align-items-center">
                <div class="col-auto">
                    <label class="form-label mb-0 me-2" style="font-size: 13px; font-weight: 500;">Estado:</label>
                    <div class="filter-pills d-inline-flex" data-filter="status">
                        <button class="filter-pill active" data-value="">Todos</button>
                        <button class="filter-pill" data-value="paid">Pagado</button>
                        <button class="filter-pill" data-value="pending">Pendiente</button>
                    </div>
                </div>
                <div class="col-auto">
                    <label class="form-label mb-0 me-2" style="font-size: 13px; font-weight: 500;">Metodo:</label>
                    <div class="filter-pills d-inline-flex" data-filter="method">
                        <button class="filter-pill active" data-value="">Todos</button>
                        <button class="filter-pill" data-value="efectivo">Efectivo</button>
                        <button class="filter-pill" data-value="tarjeta">Tarjeta</button>
                        <button class="filter-pill" data-value="cargo_habitacion">Cargo Hab.</button>
                    </div>
                </div>
                <div class="col-auto">
                    <label class="form-label mb-0 me-2" style="font-size: 13px; font-weight: 500;">Zona:</label>
                    <select id="zone-filter" class="form-select form-select-sm" style="width: 150px;">
                        <option value="">Todas</option>
                        {% for zone in zones %}
                        <option value="{{ zone.id }}">{{ zone.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-auto">
                    <label class="form-label mb-0 me-2" style="font-size: 13px; font-weight: 500;">Ticket:</label>
                    <div class="filter-pills d-inline-flex" data-filter="ticket">
                        <button class="filter-pill active" data-value="">Todos</button>
                        <button class="filter-pill" data-value="true">Con ticket</button>
                        <button class="filter-pill" data-value="false">Sin ticket</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Data Table -->
    <div class="card position-relative">
        <div class="loading-overlay d-none" id="loading-overlay">
            <div class="spinner"></div>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>Cliente</th>
                            <th>Tipo</th>
                            <th>Mobiliario</th>
                            <th>Zona</th>
                            <th class="text-end">Importe</th>
                            <th class="text-center">Estado</th>
                            <th class="text-center">Metodo</th>
                            <th>Ticket</th>
                            <th class="text-center">Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="reservations-table">
                        <!-- Dynamic content -->
                    </tbody>
                </table>
            </div>
            <div id="empty-state" class="empty-state d-none">
                <i class="fas fa-receipt"></i>
                <p>No hay reservas con pagos para esta fecha</p>
            </div>
        </div>
    </div>
</div>

<!-- Payment Modal -->
<div class="modal fade" id="payment-modal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Registrar Pago</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="modal-reservation-id">

                <div class="mb-3 p-3" style="background: #F5E6D3; border-radius: 8px;">
                    <div class="d-flex justify-content-between">
                        <span id="modal-customer-name" style="font-weight: 500;"></span>
                        <span id="modal-amount" style="font-weight: 700; color: #1A3A5C;"></span>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Metodo de Pago <span class="text-danger">*</span></label>
                    <div class="d-flex gap-2">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="modal-payment-method"
                                   id="method-efectivo" value="efectivo">
                            <label class="form-check-label" for="method-efectivo">Efectivo</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="modal-payment-method"
                                   id="method-tarjeta" value="tarjeta">
                            <label class="form-check-label" for="method-tarjeta">Tarjeta</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="modal-payment-method"
                                   id="method-cargo" value="cargo_habitacion">
                            <label class="form-check-label" for="method-cargo">Cargo Hab.</label>
                        </div>
                    </div>
                </div>

                <div class="mb-3">
                    <label for="modal-ticket-number" class="form-label">Numero de Ticket</label>
                    <input type="text" class="form-control" id="modal-ticket-number"
                           placeholder="Opcional">
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
                    Cancelar
                </button>
                <button type="button" class="btn btn-primary" id="confirm-payment-btn">
                    <i class="fas fa-check me-2"></i>Confirmar Pago
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const datePicker = document.getElementById('date-picker');
    const refreshBtn = document.getElementById('refresh-btn');
    const zoneFilter = document.getElementById('zone-filter');
    const loadingOverlay = document.getElementById('loading-overlay');
    const reservationsTable = document.getElementById('reservations-table');
    const emptyState = document.getElementById('empty-state');
    const paymentModal = new bootstrap.Modal(document.getElementById('payment-modal'));

    let currentFilters = {
        status: '',
        method: '',
        zone_id: '',
        has_ticket: ''
    };

    // Filter pill clicks
    document.querySelectorAll('.filter-pills').forEach(group => {
        const filterType = group.dataset.filter;
        group.querySelectorAll('.filter-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                group.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                currentFilters[filterType === 'ticket' ? 'has_ticket' : filterType] = pill.dataset.value;
                loadData();
            });
        });
    });

    // Zone filter change
    zoneFilter.addEventListener('change', () => {
        currentFilters.zone_id = zoneFilter.value;
        loadData();
    });

    // Date picker change
    datePicker.addEventListener('change', () => loadData());

    // Refresh button
    refreshBtn.addEventListener('click', () => loadData());

    // Load data function
    async function loadData() {
        loadingOverlay.classList.remove('d-none');

        const params = new URLSearchParams({
            date: datePicker.value
        });

        if (currentFilters.status) params.append('status', currentFilters.status);
        if (currentFilters.method) params.append('method', currentFilters.method);
        if (currentFilters.zone_id) params.append('zone_id', currentFilters.zone_id);
        if (currentFilters.has_ticket) params.append('has_ticket', currentFilters.has_ticket);

        try {
            const response = await fetch(`/beach/reports/api/payment-reconciliation?${params}`);
            const data = await response.json();

            if (data.success) {
                updateSummary(data.summary);
                updateTable(data.reservations);
            }
        } catch (error) {
            console.error('Error loading data:', error);
            showToast('Error al cargar los datos', 'error');
        } finally {
            loadingOverlay.classList.add('d-none');
        }
    }

    // Update summary cards
    function updateSummary(summary) {
        const formatCurrency = (val) => '€' + (val || 0).toFixed(2);

        document.getElementById('summary-efectivo').textContent = formatCurrency(summary.by_method.efectivo.total);
        document.getElementById('summary-efectivo-count').textContent = `(${summary.by_method.efectivo.count})`;

        document.getElementById('summary-tarjeta').textContent = formatCurrency(summary.by_method.tarjeta.total);
        document.getElementById('summary-tarjeta-count').textContent = `(${summary.by_method.tarjeta.count})`;

        document.getElementById('summary-cargo').textContent = formatCurrency(summary.by_method.cargo_habitacion.total);
        document.getElementById('summary-cargo-count').textContent = `(${summary.by_method.cargo_habitacion.count})`;

        document.getElementById('summary-pending').textContent = formatCurrency(summary.pending.total);
        document.getElementById('summary-pending-count').textContent = `(${summary.pending.count})`;

        document.getElementById('tickets-registered').textContent = summary.tickets.with_ticket;
        document.getElementById('tickets-total').textContent = summary.tickets.total_paid;

        const missingText = summary.tickets.missing > 0
            ? `(${summary.tickets.missing} sin ticket)`
            : '';
        document.getElementById('tickets-missing-text').textContent = missingText;
    }

    // Update table
    function updateTable(reservations) {
        if (reservations.length === 0) {
            reservationsTable.innerHTML = '';
            emptyState.classList.remove('d-none');
            return;
        }

        emptyState.classList.add('d-none');

        const typeLabels = {
            'paquete': 'Paquete',
            'consumo_minimo': 'Consumo Min.'
        };

        const methodLabels = {
            'efectivo': 'Efectivo',
            'tarjeta': 'Tarjeta',
            'cargo_habitacion': 'Cargo Hab.'
        };

        reservationsTable.innerHTML = reservations.map(r => `
            <tr data-id="${r.id}">
                <td>
                    <span style="font-weight: 500;">${r.first_name || ''} ${r.last_name || ''}</span>
                    <br><small class="text-muted">${r.customer_type === 'interno' ? 'Interno' : 'Externo'}</small>
                </td>
                <td>
                    ${typeLabels[r.reservation_type] || r.reservation_type}
                    ${r.package_name ? `<br><small class="text-muted">${r.package_name}</small>` : ''}
                </td>
                <td>${r.furniture_name || '-'}</td>
                <td>${r.zone_name || '-'}</td>
                <td class="text-end" style="font-weight: 600;">€${(r.final_price || 0).toFixed(2)}</td>
                <td class="text-center">
                    <span class="status-badge ${r.paid ? 'paid' : 'pending'}">
                        ${r.paid ? '<i class="fas fa-check me-1"></i>Pagado' : '<i class="fas fa-clock me-1"></i>Pendiente'}
                    </span>
                </td>
                <td class="text-center">
                    ${r.payment_method
                        ? `<span class="method-badge ${r.payment_method}">${methodLabels[r.payment_method] || r.payment_method}</span>`
                        : '-'}
                </td>
                <td>${r.payment_ticket_number || '-'}</td>
                <td class="text-center">
                    ${!r.paid
                        ? `<button class="btn-cobrar btn-mark-paid"
                                   data-id="${r.id}"
                                   data-name="${r.first_name || ''} ${r.last_name || ''}"
                                   data-amount="${r.final_price || 0}">
                               <i class="fas fa-cash-register me-1"></i>Cobrar
                           </button>`
                        : ''}
                </td>
            </tr>
        `).join('');

        // Add click handlers for mark paid buttons
        document.querySelectorAll('.btn-mark-paid').forEach(btn => {
            btn.addEventListener('click', () => openPaymentModal(btn));
        });
    }

    // Open payment modal
    function openPaymentModal(btn) {
        document.getElementById('modal-reservation-id').value = btn.dataset.id;
        document.getElementById('modal-customer-name').textContent = btn.dataset.name;
        document.getElementById('modal-amount').textContent = '€' + parseFloat(btn.dataset.amount).toFixed(2);
        document.getElementById('modal-ticket-number').value = '';
        document.querySelectorAll('input[name="modal-payment-method"]').forEach(r => r.checked = false);
        paymentModal.show();
    }

    // Confirm payment
    document.getElementById('confirm-payment-btn').addEventListener('click', async () => {
        const reservationId = document.getElementById('modal-reservation-id').value;
        const paymentMethod = document.querySelector('input[name="modal-payment-method"]:checked')?.value;
        const ticketNumber = document.getElementById('modal-ticket-number').value;

        if (!paymentMethod) {
            showToast('Seleccione un metodo de pago', 'warning');
            return;
        }

        try {
            const response = await fetch('/beach/reports/api/payment-reconciliation/mark-paid', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    reservation_id: parseInt(reservationId),
                    payment_method: paymentMethod,
                    ticket_number: ticketNumber
                })
            });

            const data = await response.json();

            if (data.success) {
                paymentModal.hide();
                showToast('Pago registrado correctamente', 'success');
                loadData();
            } else {
                showToast(data.message || 'Error al registrar el pago', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error al registrar el pago', 'error');
        }
    });

    // Toast notification
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(container);
        }
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    // Initial load
    loadData();
});
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/beach/reports/
git commit -m "feat(ui): add payment reconciliation report template"
```

---

## Task 5: Wire Everything Together

**Files:**
- Modify: `blueprints/beach/__init__.py` (if not done in Task 3)

**Step 1: Read current beach blueprint init**

Read `blueprints/beach/__init__.py` to see current structure.

**Step 2: Register the reports blueprint**

Ensure this line is added after other route imports:

```python
# Reports routes
from blueprints.beach.routes.reports import reports_bp
beach_bp.register_blueprint(reports_bp)
```

**Step 3: Start server and test**

Run: `python app.py`

Navigate to: `http://localhost:5000/beach/reports/payment-reconciliation`

Expected: Page loads with filters, summary cards, and table.

**Step 4: Commit if any changes were needed**

```bash
git add blueprints/beach/__init__.py
git commit -m "feat: wire payment reconciliation report to beach blueprint"
```

---

## Task 6: Test the Complete Feature

**Step 1: Test page load**
- Navigate to `/beach/reports/payment-reconciliation`
- Verify summary cards show
- Verify filters are visible
- Verify table headers appear

**Step 2: Test filters**
- Click "Pagado" filter - should filter to paid only
- Click "Pendiente" - should filter to unpaid only
- Select a zone - should filter by zone
- Click "Sin ticket" - should show paid without ticket

**Step 3: Test date picker**
- Change date - data should reload
- Click refresh - should reload current date

**Step 4: Test payment modal (if unpaid reservations exist)**
- Click "Cobrar" on an unpaid row
- Modal should open with customer name and amount
- Select payment method
- Enter ticket number (optional)
- Click "Confirmar Pago"
- Row should update to "Pagado"
- Summary cards should update

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete payment reconciliation report

- New report page at /beach/reports/payment-reconciliation
- Filter by payment status, method, zone, ticket
- Summary totals by payment method
- Ticket registration tracking
- Quick mark-as-paid with modal
- Permission for admin/manager roles"
```

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `models/reports/` | Model functions for queries |
| 2 | `database/migrations/permissions.py` | Permission migration |
| 3 | `blueprints/beach/routes/reports/` | Route handlers |
| 4 | `templates/beach/reports/` | HTML template with JS |
| 5 | `blueprints/beach/__init__.py` | Blueprint wiring |
| 6 | - | Integration testing |

**Total estimated steps:** ~25 bite-sized actions
