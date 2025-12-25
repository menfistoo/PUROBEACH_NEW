# Beach Club Management System - Development Plan

**Last Updated:** 2025-12-25
**Current Phase:** Insights & Analytics Planning

---

## Table of Contents
1. [Insights & Analytics Planning](#insights--analytics-planning)
2. [Implementation Roadmap](#implementation-roadmap)
3. [Technical Decisions](#technical-decisions)
4. [Completed Items](#completed-items)

---

## Insights & Analytics Planning

### Overview
Business intelligence and analytics module to provide actionable insights for beach club operations, revenue optimization, and customer experience enhancement.

### Available Data Sources

Based on existing database schema:

**Operational Data:**
- `beach_reservations` - Booking history, dates, pricing
- `beach_reservation_furniture` - Daily furniture assignments
- `beach_reservation_daily_states` - State transitions per day
- `beach_reservation_states` - State definitions

**Customer Data:**
- `beach_customers` - Customer profiles (interno/externo)
- `hotel_guests` - PMS integration data
- `beach_customer_preferences` - Preference mappings
- `beach_customer_tags` - Segmentation tags

**Infrastructure Data:**
- `beach_furniture` - Furniture inventory with positions
- `beach_furniture_types` - Hamaca, balinesa, etc.
- `beach_zones` - Zone hierarchy
- `beach_furniture_blocks` - Decorative furniture

**Financial Data:**
- `beach_price_catalog` - Pricing rules by type/customer
- `beach_minimum_consumption_policies` - Minimum spend rules

**System Data:**
- `audit_log` - User actions and changes

---

### Insight Categories

#### 1. Occupancy & Capacity Analytics
**Business Value:** Optimize furniture placement, staffing, and capacity planning

**Key Metrics:**
- Daily/weekly/monthly occupancy rate (%)
- Peak vs. off-peak utilization
- Occupancy by zone
- Occupancy by furniture type
- Average booking lead time
- No-show rate by customer type

**Visualizations:**
- Heatmap: Occupancy by day of week × hour
- Line chart: Occupancy trends over time
- Bar chart: Zone comparison
- Donut chart: Furniture type distribution

**Data Queries:**
```sql
-- Occupancy rate by date
SELECT
    assignment_date,
    COUNT(DISTINCT furniture_id) as occupied_count,
    (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1) as total_furniture,
    ROUND(COUNT(DISTINCT furniture_id) * 100.0 /
          (SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1), 2) as occupancy_rate
FROM beach_reservation_furniture
WHERE assignment_date BETWEEN ? AND ?
GROUP BY assignment_date
```

---

#### 2. Revenue Analytics
**Business Value:** Track revenue performance, identify high-value segments

**Key Metrics:**
- Daily/weekly/monthly revenue
- Revenue by customer type (interno vs externo)
- Revenue by zone
- Revenue by furniture type
- Average revenue per reservation
- Revenue per available furniture unit (RevPAR equivalent)

**Visualizations:**
- Stacked area chart: Revenue breakdown by customer type
- Bar chart: Revenue by zone
- KPI cards: Total revenue, RevPAR, avg. booking value
- Comparison: Current period vs. previous period

**Data Queries:**
```sql
-- Revenue by customer type
SELECT
    c.customer_type,
    COUNT(r.id) as reservation_count,
    SUM(r.total_price) as total_revenue,
    AVG(r.total_price) as avg_revenue_per_reservation
FROM beach_reservations r
JOIN beach_customers c ON r.customer_id = c.id
WHERE r.start_date BETWEEN ? AND ?
    AND r.state_id NOT IN (SELECT id FROM beach_reservation_states WHERE is_availability_releasing = 1)
GROUP BY c.customer_type
```

---

#### 3. Customer Behavior Analytics
**Business Value:** Improve customer experience, personalization, and retention

**Key Metrics:**
- Customer segmentation (new vs. returning)
- Booking frequency per customer
- Average party size
- Preferred zones/furniture types
- Preference utilization rate
- Tag distribution

**Visualizations:**
- Pie chart: Customer type breakdown
- Histogram: Booking frequency distribution
- Tag cloud: Popular tags
- Table: Top customers by booking count/revenue

**Data Queries:**
```sql
-- Customer segmentation
SELECT
    customer_type,
    CASE
        WHEN booking_count = 1 THEN 'New'
        WHEN booking_count BETWEEN 2 AND 5 THEN 'Regular'
        ELSE 'VIP'
    END as segment,
    COUNT(*) as customer_count
FROM (
    SELECT c.id, c.customer_type, COUNT(r.id) as booking_count
    FROM beach_customers c
    LEFT JOIN beach_reservations r ON c.id = r.customer_id
    GROUP BY c.id, c.customer_type
)
GROUP BY customer_type, segment
```

---

#### 4. Booking Patterns & Trends
**Business Value:** Forecast demand, optimize pricing strategies

**Key Metrics:**
- Booking lead time distribution
- Cancellation rate by lead time
- Multi-day vs. single-day booking ratio
- Booking source analysis (if tracked)
- Seasonal trends
- Day-of-week patterns

**Visualizations:**
- Line chart: Bookings over time with trend line
- Histogram: Lead time distribution
- Heatmap: Bookings by month × day of week
- Funnel chart: Booking state transitions

---

#### 5. Operational Efficiency
**Business Value:** Streamline operations, reduce manual work

**Key Metrics:**
- State transition times (Pendiente → Confirmada → Check-in)
- Average check-in/check-out duration
- Cancellation rate by state
- Furniture change frequency (reassignments)
- User activity (from audit_log)

**Visualizations:**
- Sankey diagram: State flow
- Bar chart: Cancellation reasons (if tracked)
- Table: User activity summary

---

### Implementation Roadmap

#### Phase 1: Foundation (Week 1-2)
**Goal:** Basic analytics infrastructure

- [ ] Create `blueprints/beach/routes/insights.py` - Main insights routes
- [ ] Create `blueprints/beach/routes/api/insights.py` - API endpoints
- [ ] Create `models/insights.py` - Analytics queries
- [ ] Create base template `templates/beach/insights/dashboard.html`
- [ ] Add permission: `beach.insights.view`
- [ ] Navigation menu item for "Analíticas" / "Insights"

**Technical Decisions:**
- Use Chart.js for visualizations (already in stack, lightweight)
- Date range selector: Default to last 30 days
- Caching: 15-minute TTL for expensive queries
- Export: JSON API for all charts (future Excel/PDF export)

---

#### Phase 2: Core Metrics (Week 3-4)
**Goal:** Implement occupancy and revenue analytics

- [ ] Occupancy dashboard with date range filter
  - [ ] Occupancy rate KPI card
  - [ ] Occupancy by zone chart
  - [ ] Occupancy trend line
  - [ ] Occupancy heatmap (day × time)
- [ ] Revenue dashboard
  - [ ] Revenue KPI cards (total, RevPAR, avg booking)
  - [ ] Revenue by customer type chart
  - [ ] Revenue by zone chart
  - [ ] Period comparison (vs. previous period)

**Queries to implement:**
```python
# In models/insights.py
def get_occupancy_stats(start_date, end_date, zone_id=None)
def get_revenue_stats(start_date, end_date, group_by='day')
def get_revenue_by_customer_type(start_date, end_date)
def get_revenue_by_zone(start_date, end_date)
```

---

#### Phase 3: Customer Analytics (Week 5-6)
**Goal:** Customer segmentation and behavior insights

- [ ] Customer analytics dashboard
  - [ ] Customer segmentation chart
  - [ ] Top customers table (sortable)
  - [ ] Preference utilization stats
  - [ ] Tag distribution chart
- [ ] Customer detail insights (individual customer view)
  - [ ] Booking history timeline
  - [ ] Preference match rate
  - [ ] Revenue contribution

---

#### Phase 4: Advanced Analytics (Week 7-8)
**Goal:** Predictive insights and operational metrics

- [ ] Booking patterns dashboard
  - [ ] Lead time distribution
  - [ ] Seasonal trends
  - [ ] Day-of-week patterns
  - [ ] State transition funnel
- [ ] Operational dashboard
  - [ ] State transition times
  - [ ] Cancellation analysis
  - [ ] User activity summary
- [ ] Basic forecasting (moving average for demand prediction)

---

#### Phase 5: Reporting & Export (Week 9-10)
**Goal:** Shareable reports and data export

- [ ] Report builder interface
  - [ ] Select metrics and date ranges
  - [ ] Save custom report templates
  - [ ] Schedule reports (future: email delivery)
- [ ] Export functionality
  - [ ] Excel export (openpyxl)
  - [ ] PDF reports (ReportLab)
  - [ ] CSV data export
- [ ] Report templates
  - [ ] Daily operations summary
  - [ ] Weekly performance report
  - [ ] Monthly financial summary

---

### Design Considerations

**UI/UX:**
- Dashboard cards with clear KPIs and trend indicators (↑↓)
- Consistent color scheme: Gold (#D4AF37) for primary metrics
- Responsive charts (mobile-friendly)
- Loading states for async data fetching
- Empty states with helpful messages

**Performance:**
- Index optimization for date range queries
- Materialized views for complex aggregations (consider if needed)
- Pagination for large result sets
- Client-side chart rendering (reduce server load)

**Accessibility:**
- Screen reader support for charts (data tables as fallback)
- Keyboard navigation
- High contrast mode support

---

### Data Dictionary for Insights

**Key Calculated Fields:**

| Field | Formula | Description |
|-------|---------|-------------|
| `occupancy_rate` | `(occupied_furniture / total_active_furniture) × 100` | Percentage of furniture occupied |
| `revpar` | `total_revenue / total_active_furniture` | Revenue per available furniture unit |
| `no_show_rate` | `(no_show_count / total_reservations) × 100` | Percentage of no-shows |
| `cancellation_rate` | `(cancelled_count / total_reservations) × 100` | Percentage of cancellations |
| `avg_lead_time` | `AVG(start_date - created_at)` | Average booking advance notice |
| `avg_party_size` | `AVG(number_of_people)` | Average guests per reservation |
| `preference_match_rate` | `(preferences_matched / total_preferences) × 100` | How often preferences are met |

---

### Questions to Consider

**Business Questions:**
1. What are the 3 most important metrics for daily operations?
2. Who is the primary audience? (Manager, staff, admin, owner)
3. Should insights be role-based? (Different dashboards for different roles)
4. Are there specific benchmarks or targets to track against?
5. What time ranges are most important? (Daily, weekly, monthly, seasonal)

**Technical Questions:**
1. Should we implement real-time updates (WebSocket) or is periodic refresh sufficient?
2. Do we need drill-down capabilities? (Click chart → detailed view)
3. Should we track user interactions with insights? (Most viewed, most exported)
4. Data retention: How far back should analytics go?
5. Should we implement data warehouse/OLAP for historical analysis?

---

### Future Enhancements

**Advanced Analytics:**
- Machine learning for demand forecasting
- Anomaly detection (unusual booking patterns)
- Customer lifetime value (CLV) prediction
- Churn prediction for returning customers
- Dynamic pricing recommendations

**Integrations:**
- Google Analytics integration (if web bookings exist)
- Weather data correlation (occupancy vs. weather)
- Competitive benchmarking (if industry data available)
- Social media sentiment analysis

**Visualizations:**
- Interactive map overlay with occupancy heatmap
- 3D furniture layout with utilization stats
- Gantt chart for reservation timeline
- Network graph for customer relationships

---

## Technical Decisions

### Analytics Architecture

**Choice: Embedded analytics vs. Separate BI tool**
- **Decision:** Embedded analytics within Flask app
- **Rationale:**
  - Full control over UI/UX
  - No additional licensing costs
  - Tight integration with existing auth/permissions
  - Simpler deployment
- **Trade-offs:** More development work vs. using pre-built BI tool

**Query Strategy:**
- **Decision:** SQL queries in models layer, cached results
- **Rationale:**
  - Leverage SQLite's excellent read performance
  - WAL mode supports concurrent reads
  - Simple caching strategy (TTL-based)
- **Trade-offs:** May need optimization for large datasets (>100k reservations)

**Charting Library:**
- **Decision:** Chart.js
- **Rationale:**
  - Open source, MIT license
  - Responsive out of the box
  - Good documentation
  - Matches design system colors
- **Alternatives considered:** D3.js (too complex), Plotly (heavier)

---

## Completed Items

### Core System (Completed)
- ✅ Database schema with 22 tables
- ✅ User authentication and role-based permissions
- ✅ Reservation management (single and multi-day)
- ✅ Customer management (interno/externo)
- ✅ Interactive map with drag-and-drop
- ✅ Furniture and zone configuration
- ✅ State management with configurable states
- ✅ Pricing catalog
- ✅ Hotel guest import (Excel)
- ✅ Audit logging

---

## Notes & Discoveries

**Date:** 2025-12-25
**Topic:** Initial insights planning
**Notes:**
- No existing analytics or reports module
- Rich data available across 22 tables
- Good foundation for comprehensive analytics
- Need to clarify business priorities before implementation

---

## Next Steps

1. **Review this plan** and prioritize insight categories
2. **Answer business questions** in "Questions to Consider" section
3. **Begin Phase 1** implementation (if approved)
4. **Set up development branch** for insights module
5. **Create wireframes/mockups** for dashboard layout

---

**How to use this document:**
- Update after each work session
- Mark items with ✅ when completed
- Add new discoveries in "Notes & Discoveries"
- Keep "Next Steps" current
- Reference this before starting any new feature
