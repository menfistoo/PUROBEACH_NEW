# Payment Reconciliation Report - Design Document

**Date:** 2026-01-11
**Status:** Approved
**Feature:** Daily payment reconciliation report for cashier verification

## Overview

New report page to track daily payments, verify ticket numbers, and reconcile with cashier records. Shows all reservations involving money (packages + minimum consumption) with filtering and quick payment actions.

## Requirements Summary

- View all paid and unpaid reservations for a selected date
- Filter by: payment status, payment method, zone, ticket presence
- Summary totals by payment method
- Track ticket registration (how many paid reservations have ticket numbers)
- Quick action to mark unpaid reservations as paid with ticket number

## Data Model

**Source:** `beach_reservations` table

**Filter criteria:**
- `reservation_type` IN ('paquete', 'consumo_minimo')
- Excludes states with `is_availability_releasing = 1` (cancelled, no-show, etc.)
- `start_date` = selected date

**Fields used:**
- `paid` (INTEGER 0/1) - Payment status
- `payment_method` (TEXT) - 'efectivo', 'tarjeta', 'cargo_habitacion'
- `payment_ticket_number` (TEXT) - Free text POS/PMS ticket
- `final_price` (REAL) - Amount to pay
- Zone derived from furniture assignment via `beach_reservation_furniture`

## Page Layout

### URL
`/beach/reports/payment-reconciliation`

### Header
- Title: "Conciliación de Pagos"
- Date picker (defaults to today)
- Refresh button

### Filter Bar
Horizontal pill-style filter buttons:

| Filter | Options |
|--------|---------|
| Payment status | Todos \| Pagado \| Pendiente |
| Payment method | Todos \| Efectivo \| Tarjeta \| Cargo Habitación |
| Zone | Todos \| [Dropdown with zones] |
| Ticket | Todos \| Con ticket \| Sin ticket |

### Summary Cards
Four cards showing totals:

| Efectivo | Tarjeta | Cargo Habitación | Pendiente |
|----------|---------|------------------|-----------|
| €XXX (N) | €XXX (N)| €XXX (N)         | €XXX (N)  |

Plus indicator: "Tickets: X/Y registrados"

### Data Table

| Column | Description |
|--------|-------------|
| Cliente | Customer full name |
| Tipo | Reservation type (Paquete/Consumo Mín.) |
| Mobiliario | Assigned furniture name |
| Zona | Zone name |
| Importe | Amount (final_price) |
| Estado | Pagado (✓) or Pendiente (⏳) |
| Método | Payment method or "-" |
| Ticket | Ticket number or "-" |
| Acciones | "Cobrar" button for unpaid |

**Default sort:** Pending first, then by creation time

## Quick Payment Modal

Triggered by "Cobrar" button on unpaid rows.

**Fields:**
- Customer name and amount (read-only, for confirmation)
- Método de pago: Radio buttons (required)
  - Efectivo
  - Tarjeta
  - Cargo Habitación
- Nº Ticket: Text input (optional)

**Buttons:**
- "Confirmar Pago" (primary)
- "Cancelar" (secondary)

**Behavior:**
- Updates reservation: `paid = 1`, `payment_method`, `payment_ticket_number`
- Row updates in-place via AJAX (no page reload)
- Summary cards recalculate
- Success toast notification

## Technical Implementation

### Backend Files

```
blueprints/beach/routes/reports/
├── __init__.py
└── payment_reconciliation.py    # Routes

models/reports/
├── __init__.py
└── payment_reconciliation.py    # Query functions

templates/beach/reports/
└── payment_reconciliation.html  # Template
```

### Routes

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/beach/reports/payment-reconciliation` | Main page |
| GET | `/beach/api/reports/payment-reconciliation` | Data API (JSON) |
| POST | `/beach/api/reports/payment-reconciliation/mark-paid` | Mark as paid |

### Model Functions

```python
def get_payment_reconciliation_data(date: str, filters: dict) -> dict:
    """Get reservations and summary for reconciliation report."""

def get_payment_summary(date: str) -> dict:
    """Get totals by payment method and ticket counts."""

def mark_reservation_paid(
    reservation_id: int,
    payment_method: str,
    ticket_number: str | None
) -> bool:
    """Update reservation payment status."""
```

### Permissions

- New permission: `beach.reports.payment_reconciliation`
- Display name: "Conciliación de Pagos"
- Assigned to: admin, manager roles

### Menu Integration

Added to "Informes" section in sidebar navigation.

## UI/UX Notes

- Follows existing design system (DESIGN_SYSTEM.md)
- Gold primary buttons, sand table headers
- Responsive design for tablet use
- Instant feedback on payment actions (no page reload)
- Clear visual distinction between paid (green check) and pending (orange clock)

## Testing Considerations

- Filter combinations work correctly
- Summary totals match filtered data
- Quick payment updates all relevant displays
- Permission check enforced
- Date picker handles edge cases (no data, future dates)
