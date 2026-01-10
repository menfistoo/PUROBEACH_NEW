# Insights Module Design

**Date:** 2026-01-10
**Status:** Approved
**Author:** Claude + User

---

## Overview

Business intelligence module for the Beach Club Management System providing operational dashboards and advanced analytics for staff and management.

### Goals
- Provide staff with quick daily operational metrics
- Give management detailed analytics for decision-making
- Track occupancy, revenue (packages/minimum consumption), customer behavior, and booking patterns

### Non-Goals (Deferred)
- Export functionality (Excel/PDF)
- Audit log / user activity tracking
- Real-time auto-refresh

---

## Architecture

### Approach
Two separate pages with distinct purposes:
- **Dashboard Operativo** (`/beach/insights`) - Staff daily view
- **Analíticas Avanzadas** (`/beach/insights/analytics`) - Management detailed view

### File Structure

```
blueprints/beach/routes/
├── insights.py                 # Main routes for insights module

models/
├── insights.py                 # Analytics queries (new file)

templates/beach/insights/
├── dashboard.html              # Operational Dashboard (staff)
├── analytics.html              # Advanced Analytics (management)

static/js/insights/
├── chart-config.js             # Chart.js base configuration
├── dashboard.js                # Dashboard logic
└── analytics.js                # Analytics logic + charts
```

### Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/beach/insights` | GET | Operational Dashboard |
| `/beach/insights/analytics` | GET | Advanced Analytics |
| `/beach/api/insights/today` | GET | API: Today's data |
| `/beach/api/insights/occupancy` | GET | API: Occupancy stats (date range) |
| `/beach/api/insights/revenue` | GET | API: Beach club revenue |
| `/beach/api/insights/customers` | GET | API: Customer metrics |
| `/beach/api/insights/patterns` | GET | API: Booking patterns |

### Permissions

| Permission | Description |
|------------|-------------|
| `beach.insights.view` | Access to Operational Dashboard |
| `beach.insights.analytics` | Access to Advanced Analytics |

---

## Dashboard Operativo (Staff)

### Purpose
Quick view of today's beach club status. No filters needed - shows current day only.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Dashboard del Día                        Hoy: 10 Ene 2026   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   72%       │  │    18       │  │    7        │             │
│  │  Ocupación  │  │   Libres    │  │  Reservas   │             │
│  │  del Día    │  │  Hamacas 12 │  │  Pendientes │             │
│  │             │  │  Balinesas 6│  │  de Check-in│             │
│  │  ▲ +5%      │  │             │  │             │             │
│  │  vs ayer    │  └─────────────┘  └─────────────┘             │
│  └─────────────┘                                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Ocupación por Zona                                         ││
│  │  ┌──────────────────────────────────────────┐              ││
│  │  │ VIP          ████████████████░░░░  80%   │              ││
│  │  │ Primera Línea ███████████████░░░░░  75%   │              ││
│  │  │ Segunda Línea ██████████░░░░░░░░░░  50%   │              ││
│  │  │ Jardín       ████████████████████  100%  │              ││
│  │  └──────────────────────────────────────────┘              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│         [ Ver Analíticas Avanzadas → ]                         │
└─────────────────────────────────────────────────────────────────┘
```

### Components

#### KPI Cards (3)
1. **Ocupación del Día** - Percentage with comparison vs yesterday (▲/▼)
2. **Mobiliario Libre** - Total free, breakdown by type (hamacas/balinesas)
3. **Reservas Pendientes** - Expected check-ins today

#### Occupancy by Zone
- Horizontal progress bars showing % per active zone
- Gold (#D4AF37) for filled, gray (#E8E8E8) for empty
- Percentage label on right side

### Data Refresh
- Manual refresh button (no auto-refresh)
- Data loaded on page open

---

## Analíticas Avanzadas (Management)

### Purpose
Detailed analytics with customizable date range for management decision-making.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  📈 Analíticas                    [  01/12/2025 - 10/01/2026  ] │
│                                   Quick: [7d] [30d] [Mes]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ▼ Ocupación           (collapsible section)                   │
│  ▼ Ingresos Beach Club (collapsible section)                   │
│  ▼ Clientes            (collapsible section)                   │
│  ▼ Patrones de Reserva (collapsible section)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Date Range Picker
- Custom date range input
- Quick buttons: "7 días", "30 días", "Este mes"
- Default: Last 30 days
- All sections update when dates change

### Navigation
- Single page with scroll
- Collapsible sections (all expanded by default)
- Click header to expand/collapse

---

### Section 1: Ocupación

#### KPIs (3 cards)
- **Ocupación Promedio** - Average occupancy % for period
- **Reservas Totales** - Count of non-cancelled reservations
- **Tasa No-Show** - No-show percentage

#### Line Chart: Occupancy Trend
- X-axis: Dates in range
- Y-axis: Occupancy percentage (0-100%)
- Single line in Deep Ocean (#1A3A5C)
- Tooltip with date and exact value

#### Bar Chart: Occupancy by Zone
- Horizontal bars showing average occupancy per zone
- Gold (#D4AF37) fill

---

### Section 2: Ingresos Beach Club

#### KPIs (3 cards)
- **Ingresos Totales** - Sum of calculated_price (paquete + consumo_minimo only)
- **Reservas de Pago** - Count of paid reservation types
- **Promedio por Reserva** - Average revenue per paid reservation

#### Donut Chart: By Reservation Type
- Paquete: Gold (#D4AF37)
- Consumo Mínimo: Info Blue (#4A90A4)
- Incluido: Neutral (#9CA3AF)

#### Donut Chart: By Customer Type
- Externo: Gold (#D4AF37)
- Interno: Deep Ocean (#1A3A5C)

#### Table: Top Packages
| # | Paquete | Vendidos | Ingresos | % Total |
|---|---------|----------|----------|---------|
| 1 | Paquete Premium | 45 | €4,005 | 32% |
| 2 | Día de Playa VIP | 28 | €4,200 | 34% |

- Max 5-10 rows
- Sorted by revenue descending

---

### Section 3: Clientes

#### KPIs (3 cards)
- **Clientes Únicos** - Distinct customers in period
- **Tamaño Promedio de Grupo** - Average num_people
- **% Clientes Recurrentes** - Customers with >1 historical reservation

#### Bar Charts (side by side)
- **Segmentación:** Nuevos vs Recurrentes
- **Tipo:** Interno vs Externo

#### Table: Top 10 Customers
| # | Cliente | Tipo | Reservas | Gasto Total |
|---|---------|------|----------|-------------|
| 1 | García, María | Externo | 8 | €712 |
| 2 | López, Juan (H.204) | Interno | 6 | €534 |

- Show room number for interno customers

#### Lists (side by side)
- **Preferencias Más Solicitadas** - From beach_preferences
- **Tags Más Usados** - From beach_tags

---

### Section 4: Patrones de Reserva

#### KPIs (3 cards)
- **Lead Time Promedio** - Average days between created_at and start_date
- **Tasa Cancelación** - Cancellation percentage
- **Tasa No-Show** - No-show percentage

#### Bar Chart: Reservations by Day of Week
- X-axis: Lun, Mar, Mié, Jue, Vie, Sáb, Dom
- Y-axis: Reservation count
- Highlight peak day
- Caption: "Promedio: X reservas/día | Pico: Sábado (Y)"

#### Histogram: Lead Time Distribution
- Ranges: Mismo día, 1-2 días, 3-7 días, 8-14 días, 15+ días
- Caption: "X% reservan el mismo día"

#### Line Chart: Cancellation Trend
- Cancellation rate over time in period

#### Breakdown Cards
- **By Customer Type:** Interno X% / Externo Y%
- **By Lead Time:** Mismo día X% / 1-7 días Y% / 8+ días Z%

---

## Database Queries

No schema changes required. All metrics calculated from existing tables.

### Occupancy

```sql
-- Daily occupancy rate
SELECT
    rf.assignment_date,
    COUNT(DISTINCT rf.furniture_id) as occupied,
    (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1) as total,
    ROUND(COUNT(DISTINCT rf.furniture_id) * 100.0 /
          (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1), 1) as rate
FROM beach_reservation_furniture rf
JOIN beach_reservations r ON rf.reservation_id = r.id
JOIN beach_reservation_states s ON r.state_id = s.id
WHERE rf.assignment_date BETWEEN :start_date AND :end_date
  AND s.is_availability_releasing = 0
GROUP BY rf.assignment_date
ORDER BY rf.assignment_date
```

```sql
-- Occupancy by zone
SELECT
    z.id,
    z.name as zone_name,
    COUNT(DISTINCT rf.furniture_id) as occupied,
    (SELECT COUNT(*) FROM beach_furniture f WHERE f.zone_id = z.id AND f.is_active = 1) as total
FROM beach_zones z
LEFT JOIN beach_furniture f ON f.zone_id = z.id AND f.is_active = 1
LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id
    AND rf.assignment_date = :date
LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
LEFT JOIN beach_reservation_states s ON r.state_id = s.id
    AND s.is_availability_releasing = 0
WHERE z.is_active = 1
GROUP BY z.id, z.name
ORDER BY z.display_order
```

### Revenue

```sql
-- Revenue by reservation type
SELECT
    reservation_type,
    COUNT(*) as count,
    COALESCE(SUM(calculated_price), 0) as revenue
FROM beach_reservations
WHERE start_date BETWEEN :start_date AND :end_date
  AND state_id NOT IN (SELECT id FROM beach_reservation_states WHERE is_availability_releasing = 1)
GROUP BY reservation_type
```

```sql
-- Top packages
SELECT
    p.id,
    p.package_name,
    COUNT(r.id) as sold_count,
    SUM(r.calculated_price) as revenue
FROM beach_packages p
JOIN beach_reservations r ON r.package_id = p.id
WHERE r.start_date BETWEEN :start_date AND :end_date
  AND r.reservation_type = 'paquete'
GROUP BY p.id, p.package_name
ORDER BY revenue DESC
LIMIT 10
```

### Customers

```sql
-- Customer segmentation
SELECT
    c.customer_type,
    CASE
        WHEN hist.booking_count = 1 THEN 'new'
        ELSE 'returning'
    END as segment,
    COUNT(DISTINCT c.id) as customer_count
FROM beach_customers c
JOIN beach_reservations r ON r.customer_id = c.id
JOIN (
    SELECT customer_id, COUNT(*) as booking_count
    FROM beach_reservations
    GROUP BY customer_id
) hist ON hist.customer_id = c.id
WHERE r.start_date BETWEEN :start_date AND :end_date
GROUP BY c.customer_type, segment
```

### Patterns

```sql
-- Lead time distribution
SELECT
    CASE
        WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) = 0 THEN 'same_day'
        WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 2 THEN '1_2_days'
        WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 7 THEN '3_7_days'
        WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 14 THEN '8_14_days'
        ELSE '15_plus_days'
    END as lead_time_bucket,
    COUNT(*) as count
FROM beach_reservations
WHERE start_date BETWEEN :start_date AND :end_date
GROUP BY lead_time_bucket
```

```sql
-- Reservations by day of week
SELECT
    CAST(strftime('%w', start_date) AS INTEGER) as day_of_week,
    COUNT(*) as reservation_count
FROM beach_reservations
WHERE start_date BETWEEN :start_date AND :end_date
  AND state_id NOT IN (SELECT id FROM beach_reservation_states WHERE is_availability_releasing = 1)
GROUP BY day_of_week
ORDER BY day_of_week
```

---

## Design System Compliance

### Color Palette

| Usage | Color | CSS Variable |
|-------|-------|--------------|
| KPI highlights | `#D4AF37` | `--color-primary` |
| Section headers | `#1A3A5C` | `--color-secondary` |
| Section header bg | `#F5E6D3` | `--color-accent` |
| Card backgrounds | `#FFFFFF` | - |
| Page background | `#FAFAFA` | `--color-background` |
| Trend up | `#4A7C59` | `--color-success` |
| Trend down | `#C1444F` | `--color-error` |

### Chart Colors

| Chart Element | Color |
|---------------|-------|
| Occupancy bars (filled) | `#D4AF37` |
| Occupancy bars (empty) | `#E8E8E8` |
| Trend line | `#1A3A5C` |
| Donut - Paquete | `#D4AF37` |
| Donut - Consumo Mínimo | `#4A90A4` |
| Donut - Incluido | `#9CA3AF` |
| Donut - Externo | `#D4AF37` |
| Donut - Interno | `#1A3A5C` |

### Components

#### KPI Card

```html
<div class="card kpi-card">
    <div class="card-body text-center">
        <div class="kpi-value">72%</div>
        <div class="kpi-label">Ocupación del Día</div>
        <div class="kpi-trend trend-up">
            <i class="fas fa-arrow-up"></i> +5% vs ayer
        </div>
    </div>
</div>
```

```css
.kpi-card {
    border-radius: 12px;
    border: 1px solid #E8E8E8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.kpi-value {
    font-size: 36px;
    font-weight: 700;
    color: #1A3A5C;
}
.kpi-label {
    font-size: 14px;
    color: #4B5563;
    margin-top: 4px;
}
.kpi-trend {
    font-size: 13px;
    margin-top: 8px;
}
.trend-up { color: #4A7C59; }
.trend-down { color: #C1444F; }
```

#### Collapsible Section

```html
<div class="insights-section" id="occupancy-section">
    <div class="section-header" data-bs-toggle="collapse"
         data-bs-target="#occupancy-content" aria-expanded="true">
        <i class="fas fa-chevron-down section-toggle"></i>
        <h4 class="section-title">Ocupación</h4>
    </div>
    <div class="collapse show" id="occupancy-content">
        <div class="section-body">
            <!-- Charts & KPIs -->
        </div>
    </div>
</div>
```

```css
.section-header {
    background: #F5E6D3;
    padding: 16px 24px;
    border-radius: 12px 12px 0 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: background 0.2s ease;
}
.section-header:hover {
    background: #EDD9C0;
}
.section-title {
    color: #1A3A5C;
    font-weight: 600;
    font-size: 18px;
    margin: 0;
}
.section-toggle {
    color: #D4AF37;
    transition: transform 0.2s ease;
}
.section-header.collapsed .section-toggle {
    transform: rotate(-90deg);
}
.section-body {
    padding: 24px;
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-top: none;
    border-radius: 0 0 12px 12px;
}
```

#### Date Range Picker

```html
<div class="date-range-picker">
    <div class="quick-filters mb-2">
        <button class="btn btn-sm btn-outline-primary" data-days="7">7 días</button>
        <button class="btn btn-sm btn-primary" data-days="30">30 días</button>
        <button class="btn btn-sm btn-outline-primary" data-days="month">Este mes</button>
    </div>
    <div class="custom-range d-flex align-items-center gap-2">
        <input type="date" class="form-control form-control-sm" id="start-date">
        <span class="text-muted">—</span>
        <input type="date" class="form-control form-control-sm" id="end-date">
        <button class="btn btn-sm btn-primary" id="apply-dates" aria-label="Aplicar fechas">
            <i class="fas fa-check"></i>
        </button>
    </div>
</div>
```

### Chart.js Configuration

```javascript
// static/js/insights/chart-config.js
const INSIGHT_COLORS = {
    primary: '#D4AF37',
    secondary: '#1A3A5C',
    accent: '#F5E6D3',
    success: '#4A7C59',
    error: '#C1444F',
    info: '#4A90A4',
    neutral: '#9CA3AF',
    grid: '#E8E8E8',
    text: '#4B5563'
};

const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                font: { family: 'Inter', size: 12 },
                color: INSIGHT_COLORS.text
            }
        },
        tooltip: {
            backgroundColor: INSIGHT_COLORS.secondary,
            titleFont: { family: 'Inter', weight: '600' },
            bodyFont: { family: 'Inter' },
            cornerRadius: 8,
            padding: 12
        }
    }
};

const LINE_CHART_OPTIONS = {
    ...CHART_DEFAULTS,
    scales: {
        x: {
            grid: { color: INSIGHT_COLORS.grid },
            ticks: { font: { family: 'Inter', size: 12 }, color: INSIGHT_COLORS.text }
        },
        y: {
            grid: { color: INSIGHT_COLORS.grid },
            ticks: { font: { family: 'Inter', size: 12 }, color: INSIGHT_COLORS.text }
        }
    }
};

const DONUT_CHART_OPTIONS = {
    ...CHART_DEFAULTS,
    cutout: '60%',
    plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: {
            position: 'bottom',
            labels: {
                font: { family: 'Inter', size: 12 },
                color: INSIGHT_COLORS.text,
                padding: 16
            }
        }
    }
};
```

### Accessibility

- All charts have descriptive `aria-label`
- Tables include hidden `<caption>` for screen readers
- Minimum 4.5:1 color contrast ratio
- Visible focus indicators on interactive elements
- Icon-only buttons have `aria-label`

```html
<canvas id="occupancy-chart"
        aria-label="Gráfico de tendencia de ocupación del período seleccionado"
        role="img">
</canvas>

<button class="btn btn-sm btn-outline-primary" aria-label="Actualizar datos">
    <i class="fas fa-sync-alt"></i>
</button>
```

---

## Caching Strategy

Use existing `utils/cache.py` TTL cache for expensive queries:

```python
from utils.cache import ttl_cache

@ttl_cache(ttl_seconds=900)  # 15 minutes
def get_occupancy_stats(start_date: str, end_date: str) -> dict:
    ...

@ttl_cache(ttl_seconds=900)
def get_revenue_stats(start_date: str, end_date: str) -> dict:
    ...
```

Dashboard Operativo (today's data) uses shorter TTL (5 minutes) or no cache.

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Create `blueprints/beach/routes/insights.py`
- [ ] Create `models/insights.py` with base queries
- [ ] Create `templates/beach/insights/dashboard.html`
- [ ] Create `templates/beach/insights/analytics.html`
- [ ] Create `static/js/insights/chart-config.js`
- [ ] Add permissions to database
- [ ] Add navigation menu item

### Phase 2: Dashboard Operativo
- [ ] Implement `/beach/api/insights/today` endpoint
- [ ] Build KPI cards (occupancy, free furniture, pending check-ins)
- [ ] Build occupancy by zone bars
- [ ] Add refresh button functionality

### Phase 3: Analytics - Occupancy
- [ ] Implement `/beach/api/insights/occupancy` endpoint
- [ ] Build date range picker component
- [ ] Build occupancy KPIs
- [ ] Build occupancy trend line chart
- [ ] Build occupancy by zone chart

### Phase 4: Analytics - Revenue
- [ ] Implement `/beach/api/insights/revenue` endpoint
- [ ] Build revenue KPIs
- [ ] Build donut charts (by type, by customer)
- [ ] Build top packages table

### Phase 5: Analytics - Customers
- [ ] Implement `/beach/api/insights/customers` endpoint
- [ ] Build customer KPIs
- [ ] Build segmentation charts
- [ ] Build top customers table
- [ ] Build preferences/tags lists

### Phase 6: Analytics - Patterns
- [ ] Implement `/beach/api/insights/patterns` endpoint
- [ ] Build pattern KPIs
- [ ] Build day of week chart
- [ ] Build lead time histogram
- [ ] Build cancellation trend and breakdown

### Phase 7: Polish & Testing
- [ ] Add loading states
- [ ] Add empty states
- [ ] Test responsive design
- [ ] Test accessibility
- [ ] Performance optimization

---

## Success Criteria

- [ ] Staff can view today's occupancy in <2 seconds
- [ ] All charts render correctly with real data
- [ ] Date range changes update all sections
- [ ] Collapsible sections work smoothly
- [ ] Mobile responsive layout
- [ ] Accessibility audit passes
- [ ] Query performance <500ms for 30-day range

---

## Future Enhancements (Out of Scope)

- Excel/PDF export
- Scheduled email reports
- Real-time auto-refresh
- Audit log / user activity
- Weather correlation
- Demand forecasting
