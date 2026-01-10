# Insights Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Insights & Analytics module with operational dashboard for staff and advanced analytics for management.

**Architecture:** Two separate pages with shared API endpoints. Model layer handles all database queries with TTL caching. Chart.js for visualizations following the Beach Club design system.

**Tech Stack:** Flask routes, SQLite queries, Chart.js, Bootstrap 5, existing cache utilities

**Design Document:** `docs/plans/2026-01-10-insights-module-design.md`

---

## Phase 1: Foundation

### Task 1.1: Create Insights Model with Occupancy Query

**Files:**
- Create: `models/insights.py`
- Test: `tests/test_insights.py`

**Step 1: Write the failing test**

Create `tests/test_insights.py`:

```python
"""
Tests for insights model functions.
"""

import pytest
from datetime import date, timedelta


class TestGetOccupancyToday:
    """Tests for get_occupancy_today function."""

    def test_returns_zero_when_no_reservations(self, app):
        """Returns 0% occupancy when no reservations exist."""
        from models.insights import get_occupancy_today

        with app.app_context():
            result = get_occupancy_today()

            assert 'occupied' in result
            assert 'total' in result
            assert 'rate' in result
            assert result['occupied'] == 0
            assert result['rate'] == 0.0

    def test_returns_correct_rate_with_reservations(self, app):
        """Returns correct occupancy rate with active reservations."""
        from models.insights import get_occupancy_today
        from models.furniture import get_all_furniture

        with app.app_context():
            # Get total furniture count for reference
            furniture = get_all_furniture()
            total = len([f for f in furniture if f['is_active']])

            result = get_occupancy_today()

            assert result['total'] == total
            assert 0 <= result['rate'] <= 100
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyToday -v
```

Expected: FAIL with "No module named 'models.insights'"

**Step 3: Write minimal implementation**

Create `models/insights.py`:

```python
"""
Insights model.
Analytics queries for dashboard and advanced analytics.
"""

from database import get_db
from datetime import date
from typing import Optional


# =============================================================================
# TODAY'S METRICS (Dashboard Operativo)
# =============================================================================

def get_occupancy_today() -> dict:
    """
    Get today's occupancy metrics.

    Returns:
        dict with keys:
            - occupied: int (furniture with active reservations)
            - total: int (total active furniture)
            - rate: float (percentage 0-100)
            - by_type: dict (breakdown by furniture type)
    """
    today = date.today().isoformat()

    with get_db() as conn:
        # Total active furniture
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1
        ''')
        total = total_cursor.fetchone()[0]

        if total == 0:
            return {'occupied': 0, 'total': 0, 'rate': 0.0, 'by_type': {}}

        # Occupied furniture (non-releasing states)
        occupied_cursor = conn.execute('''
            SELECT COUNT(DISTINCT rf.furniture_id)
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE rf.assignment_date = ?
              AND s.is_availability_releasing = 0
        ''', (today,))
        occupied = occupied_cursor.fetchone()[0]

        # Breakdown by furniture type
        by_type_cursor = conn.execute('''
            SELECT
                ft.code,
                ft.name,
                COUNT(f.id) as total,
                COUNT(rf.furniture_id) as occupied
            FROM beach_furniture_types ft
            LEFT JOIN beach_furniture f ON f.furniture_type_id = ft.id AND f.is_active = 1
            LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id
                AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.state_id = s.id
                AND s.is_availability_releasing = 0
            WHERE ft.is_active = 1
            GROUP BY ft.id, ft.code, ft.name
        ''', (today,))

        by_type = {}
        for row in by_type_cursor:
            by_type[row[0]] = {
                'name': row[1],
                'total': row[2],
                'occupied': row[3] or 0,
                'free': row[2] - (row[3] or 0)
            }

        rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

        return {
            'occupied': occupied,
            'total': total,
            'rate': rate,
            'by_type': by_type
        }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyToday -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add occupancy today model function

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.2: Add Occupancy by Zone Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetOccupancyByZone:
    """Tests for get_occupancy_by_zone function."""

    def test_returns_all_active_zones(self, app):
        """Returns occupancy data for all active zones."""
        from models.insights import get_occupancy_by_zone
        from models.zone import get_all_zones

        with app.app_context():
            zones = get_all_zones(active_only=True)
            result = get_occupancy_by_zone()

            assert isinstance(result, list)
            # Should have same number of zones
            assert len(result) == len(zones)

    def test_zone_has_required_fields(self, app):
        """Each zone entry has required fields."""
        from models.insights import get_occupancy_by_zone

        with app.app_context():
            result = get_occupancy_by_zone()

            if result:  # Only test if zones exist
                zone = result[0]
                assert 'zone_id' in zone
                assert 'zone_name' in zone
                assert 'occupied' in zone
                assert 'total' in zone
                assert 'rate' in zone
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyByZone -v
```

Expected: FAIL with "cannot import name 'get_occupancy_by_zone'"

**Step 3: Write minimal implementation**

Add to `models/insights.py`:

```python
def get_occupancy_by_zone(target_date: Optional[str] = None) -> list:
    """
    Get occupancy breakdown by zone.

    Args:
        target_date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        list of dicts with keys:
            - zone_id: int
            - zone_name: str
            - occupied: int
            - total: int
            - rate: float (0-100)
    """
    if target_date is None:
        target_date = date.today().isoformat()

    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                z.id as zone_id,
                z.name as zone_name,
                COUNT(DISTINCT f.id) as total,
                COUNT(DISTINCT CASE
                    WHEN rf.id IS NOT NULL AND s.is_availability_releasing = 0
                    THEN f.id
                END) as occupied
            FROM beach_zones z
            LEFT JOIN beach_furniture f ON f.zone_id = z.id AND f.is_active = 1
            LEFT JOIN beach_reservation_furniture rf ON rf.furniture_id = f.id
                AND rf.assignment_date = ?
            LEFT JOIN beach_reservations r ON rf.reservation_id = r.id
            LEFT JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE z.is_active = 1
            GROUP BY z.id, z.name
            ORDER BY z.display_order
        ''', (target_date,))

        results = []
        for row in cursor:
            total = row[2] or 0
            occupied = row[3] or 0
            rate = round((occupied / total) * 100, 1) if total > 0 else 0.0
            results.append({
                'zone_id': row[0],
                'zone_name': row[1],
                'total': total,
                'occupied': occupied,
                'rate': rate
            })

        return results
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyByZone -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add occupancy by zone query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.3: Add Pending Check-ins Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetPendingCheckins:
    """Tests for get_pending_checkins_count function."""

    def test_returns_integer(self, app):
        """Returns an integer count."""
        from models.insights import get_pending_checkins_count

        with app.app_context():
            result = get_pending_checkins_count()
            assert isinstance(result, int)
            assert result >= 0
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetPendingCheckins -v
```

Expected: FAIL with "cannot import name 'get_pending_checkins_count'"

**Step 3: Write minimal implementation**

Add to `models/insights.py`:

```python
def get_pending_checkins_count(target_date: Optional[str] = None) -> int:
    """
    Get count of reservations pending check-in for a date.

    Args:
        target_date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        int: Number of reservations in 'confirmada' or 'pendiente' state
    """
    if target_date is None:
        target_date = date.today().isoformat()

    with get_db() as conn:
        cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date <= ?
              AND r.end_date >= ?
              AND s.code IN ('pendiente', 'confirmada')
        ''', (target_date, target_date))
        return cursor.fetchone()[0]
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetPendingCheckins -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add pending check-ins count query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.4: Add Yesterday's Occupancy for Comparison

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetOccupancyComparison:
    """Tests for get_occupancy_comparison function."""

    def test_returns_comparison_data(self, app):
        """Returns today vs yesterday comparison."""
        from models.insights import get_occupancy_comparison

        with app.app_context():
            result = get_occupancy_comparison()

            assert 'today_rate' in result
            assert 'yesterday_rate' in result
            assert 'difference' in result
            assert 'trend' in result
            assert result['trend'] in ('up', 'down', 'same')
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyComparison -v
```

Expected: FAIL with "cannot import name 'get_occupancy_comparison'"

**Step 3: Write minimal implementation**

Add to `models/insights.py` (add import at top: `from datetime import date, timedelta`):

```python
def get_occupancy_comparison() -> dict:
    """
    Get today's occupancy compared to yesterday.

    Returns:
        dict with keys:
            - today_rate: float
            - yesterday_rate: float
            - difference: float (positive = improvement)
            - trend: str ('up', 'down', 'same')
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    today_data = _get_occupancy_for_date(today.isoformat())
    yesterday_data = _get_occupancy_for_date(yesterday.isoformat())

    today_rate = today_data['rate']
    yesterday_rate = yesterday_data['rate']
    difference = round(today_rate - yesterday_rate, 1)

    if difference > 0:
        trend = 'up'
    elif difference < 0:
        trend = 'down'
    else:
        trend = 'same'

    return {
        'today_rate': today_rate,
        'yesterday_rate': yesterday_rate,
        'difference': difference,
        'trend': trend
    }


def _get_occupancy_for_date(target_date: str) -> dict:
    """
    Internal helper to get occupancy for a specific date.

    Args:
        target_date: Date string (YYYY-MM-DD)

    Returns:
        dict with occupied, total, rate
    """
    with get_db() as conn:
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1
        ''')
        total = total_cursor.fetchone()[0]

        if total == 0:
            return {'occupied': 0, 'total': 0, 'rate': 0.0}

        occupied_cursor = conn.execute('''
            SELECT COUNT(DISTINCT rf.furniture_id)
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE rf.assignment_date = ?
              AND s.is_availability_releasing = 0
        ''', (target_date,))
        occupied = occupied_cursor.fetchone()[0]

        rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

        return {'occupied': occupied, 'total': total, 'rate': rate}
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyComparison -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add occupancy comparison vs yesterday

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.5: Create Insights API Endpoint for Today's Data

**Files:**
- Create: `blueprints/beach/routes/api/insights.py`
- Modify: `blueprints/beach/routes/api/__init__.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestInsightsAPI:
    """Tests for insights API endpoints."""

    def test_today_endpoint_returns_data(self, authenticated_client, app):
        """GET /beach/api/insights/today returns today's metrics."""
        with app.app_context():
            response = authenticated_client.get('/beach/api/insights/today')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'occupancy' in data
            assert 'pending_checkins' in data
            assert 'zones' in data

    def test_today_endpoint_requires_auth(self, client, app):
        """GET /beach/api/insights/today requires authentication."""
        with app.app_context():
            response = client.get('/beach/api/insights/today')
            # Should redirect to login or return 401
            assert response.status_code in (302, 401)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestInsightsAPI -v
```

Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Write minimal implementation**

Create `blueprints/beach/routes/api/insights.py`:

```python
"""
Insights API endpoints.
Provides analytics data for dashboard and advanced views.
"""

from flask import jsonify, request
from flask_login import login_required
from utils.decorators import permission_required
from models.insights import (
    get_occupancy_today,
    get_occupancy_by_zone,
    get_pending_checkins_count,
    get_occupancy_comparison
)


def register_routes(bp):
    """Register insights API routes on the blueprint."""

    @bp.route('/insights/today', methods=['GET'])
    @login_required
    def get_insights_today():
        """
        Get today's operational metrics for dashboard.

        Response JSON:
        {
            "success": true,
            "occupancy": {
                "occupied": 45,
                "total": 60,
                "rate": 75.0,
                "by_type": {...}
            },
            "comparison": {
                "today_rate": 75.0,
                "yesterday_rate": 70.0,
                "difference": 5.0,
                "trend": "up"
            },
            "pending_checkins": 7,
            "zones": [...]
        }
        """
        try:
            occupancy = get_occupancy_today()
            comparison = get_occupancy_comparison()
            pending = get_pending_checkins_count()
            zones = get_occupancy_by_zone()

            return jsonify({
                'success': True,
                'occupancy': occupancy,
                'comparison': comparison,
                'pending_checkins': pending,
                'zones': zones
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
```

**Step 4: Register the routes**

Modify `blueprints/beach/routes/api/__init__.py` - add after line 17:

```python
from blueprints.beach.routes.api import insights
```

And add after line 25:

```python
insights.register_routes(api_bp)
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestInsightsAPI -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add blueprints/beach/routes/api/insights.py blueprints/beach/routes/api/__init__.py tests/test_insights.py
git commit -m "feat(insights): add today's metrics API endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.6: Add Insights Permissions to Database

**Files:**
- Create: `database/migrations/add_insights_permissions.py`

**Step 1: Create migration file**

Create `database/migrations/add_insights_permissions.py`:

```python
"""
Migration: Add insights permissions.
"""

from database import get_db


def migrate():
    """Add insights module permissions."""
    with get_db() as conn:
        # Check if permissions already exist
        cursor = conn.execute(
            "SELECT COUNT(*) FROM permissions WHERE code LIKE 'beach.insights.%'"
        )
        if cursor.fetchone()[0] > 0:
            print("Insights permissions already exist, skipping...")
            return

        # Insert insights permissions
        permissions = [
            ('beach.insights.view', 'Ver Dashboard Operativo', 'beach', 1, 'fa-chart-line', '/beach/insights', 85),
            ('beach.insights.analytics', 'Ver Analíticas Avanzadas', 'beach', 1, 'fa-chart-bar', '/beach/insights/analytics', 86),
        ]

        for code, name, module, is_menu, icon, menu_url, order in permissions:
            conn.execute('''
                INSERT INTO permissions (code, name, module, is_menu_item, menu_icon, menu_url, menu_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (code, name, module, is_menu, icon, menu_url, order))

        # Grant to admin role (id=1)
        conn.execute('''
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
            SELECT 1, id FROM permissions WHERE code LIKE 'beach.insights.%'
        ''')

        # Grant to manager role (id=2) if exists
        conn.execute('''
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
            SELECT 2, id FROM permissions WHERE code LIKE 'beach.insights.%'
        ''')

        conn.commit()
        print("Insights permissions added successfully.")


if __name__ == '__main__':
    migrate()
```

**Step 2: Run the migration**

```bash
python -c "from database.migrations.add_insights_permissions import migrate; migrate()"
```

Expected: "Insights permissions added successfully."

**Step 3: Commit**

```bash
git add database/migrations/add_insights_permissions.py
git commit -m "feat(insights): add insights permissions migration

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.7: Create Dashboard Template

**Files:**
- Create: `templates/beach/insights/dashboard.html`

**Step 1: Create the template**

Create directory and file `templates/beach/insights/dashboard.html`:

```html
{% extends "base.html" %}

{% block title %}Dashboard del Día - Beach Club{% endblock %}

{% block extra_css %}
<style>
    .kpi-card {
        border-radius: 12px;
        border: 1px solid #E8E8E8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
    .trend-same { color: #9CA3AF; }

    .kpi-subtitle {
        font-size: 12px;
        color: #9CA3AF;
    }

    .zone-bar-container {
        background: #E8E8E8;
        border-radius: 4px;
        height: 24px;
        overflow: hidden;
    }
    .zone-bar {
        background: linear-gradient(135deg, #D4AF37 0%, #B8960C 100%);
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }
    .zone-row {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }
    .zone-name {
        width: 140px;
        font-size: 14px;
        color: #1F2937;
    }
    .zone-bar-wrapper {
        flex: 1;
        margin: 0 12px;
    }
    .zone-rate {
        width: 50px;
        text-align: right;
        font-weight: 600;
        color: #1A3A5C;
    }

    .refresh-btn {
        color: #D4AF37;
        border-color: #D4AF37;
    }
    .refresh-btn:hover {
        background: #D4AF37;
        color: white;
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
    .loading-overlay.hidden {
        display: none;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h1 class="h3 mb-1" style="color: #1A3A5C;">
                <i class="fas fa-chart-line me-2" style="color: #D4AF37;"></i>
                Dashboard del Día
            </h1>
            <p class="text-muted mb-0" id="current-date"></p>
        </div>
        <div class="d-flex gap-2">
            <button class="btn btn-outline-primary refresh-btn" id="refresh-btn" aria-label="Actualizar datos">
                <i class="fas fa-sync-alt me-1"></i> Actualizar
            </button>
            {% if current_user_can('beach.insights.analytics') %}
            <a href="{{ url_for('beach.insights_analytics') }}" class="btn btn-primary">
                Ver Analíticas Avanzadas <i class="fas fa-arrow-right ms-1"></i>
            </a>
            {% endif %}
        </div>
    </div>

    <!-- KPI Cards -->
    <div class="row g-4 mb-4">
        <!-- Occupancy -->
        <div class="col-md-4">
            <div class="card kpi-card h-100 position-relative">
                <div class="loading-overlay hidden" id="loading-occupancy">
                    <div class="spinner-border text-warning" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>
                <div class="card-body text-center py-4">
                    <div class="kpi-value" id="kpi-occupancy-rate">--</div>
                    <div class="kpi-label">Ocupación del Día</div>
                    <div class="kpi-trend" id="kpi-occupancy-trend">
                        <span class="trend-icon"></span>
                        <span class="trend-text"></span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Free Furniture -->
        <div class="col-md-4">
            <div class="card kpi-card h-100 position-relative">
                <div class="loading-overlay hidden" id="loading-free">
                    <div class="spinner-border text-warning" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>
                <div class="card-body text-center py-4">
                    <div class="kpi-value" id="kpi-free-count">--</div>
                    <div class="kpi-label">Mobiliario Libre</div>
                    <div class="kpi-subtitle" id="kpi-free-breakdown"></div>
                </div>
            </div>
        </div>

        <!-- Pending Check-ins -->
        <div class="col-md-4">
            <div class="card kpi-card h-100 position-relative">
                <div class="loading-overlay hidden" id="loading-pending">
                    <div class="spinner-border text-warning" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                </div>
                <div class="card-body text-center py-4">
                    <div class="kpi-value" id="kpi-pending-count">--</div>
                    <div class="kpi-label">Reservas Pendientes</div>
                    <div class="kpi-subtitle">de Check-in</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Occupancy by Zone -->
    <div class="card">
        <div class="card-header" style="background: #F5E6D3; border-bottom: 2px solid #D4AF37;">
            <h5 class="card-title mb-0" style="color: #1A3A5C;">
                <i class="fas fa-map-marker-alt me-2" style="color: #D4AF37;"></i>
                Ocupación por Zona
            </h5>
        </div>
        <div class="card-body position-relative">
            <div class="loading-overlay hidden" id="loading-zones">
                <div class="spinner-border text-warning" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
            </div>
            <div id="zones-container">
                <!-- Zones will be rendered here -->
            </div>
            <div id="zones-empty" class="text-center text-muted py-4 d-none">
                No hay zonas configuradas
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').textContent =
        now.toLocaleDateString('es-ES', options).replace(/^\w/, c => c.toUpperCase());

    // Load data
    loadDashboardData();

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', function() {
        loadDashboardData();
    });
});

function loadDashboardData() {
    // Show loading
    document.querySelectorAll('.loading-overlay').forEach(el => el.classList.remove('hidden'));

    fetch('/beach/api/insights/today')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderOccupancy(data.occupancy, data.comparison);
                renderPendingCheckins(data.pending_checkins);
                renderZones(data.zones);
            } else {
                console.error('Error loading insights:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching insights:', error);
        })
        .finally(() => {
            // Hide loading
            document.querySelectorAll('.loading-overlay').forEach(el => el.classList.add('hidden'));
        });
}

function renderOccupancy(occupancy, comparison) {
    // Rate
    document.getElementById('kpi-occupancy-rate').textContent = occupancy.rate + '%';

    // Trend
    const trendContainer = document.getElementById('kpi-occupancy-trend');
    let trendClass = 'trend-same';
    let trendIcon = 'fa-minus';
    let trendText = 'igual que ayer';

    if (comparison.trend === 'up') {
        trendClass = 'trend-up';
        trendIcon = 'fa-arrow-up';
        trendText = '+' + comparison.difference + '% vs ayer';
    } else if (comparison.trend === 'down') {
        trendClass = 'trend-down';
        trendIcon = 'fa-arrow-down';
        trendText = comparison.difference + '% vs ayer';
    }

    trendContainer.className = 'kpi-trend ' + trendClass;
    trendContainer.innerHTML = '<i class="fas ' + trendIcon + ' me-1"></i>' + trendText;

    // Free count
    const freeCount = occupancy.total - occupancy.occupied;
    document.getElementById('kpi-free-count').textContent = freeCount;

    // Breakdown by type
    const breakdown = [];
    for (const [code, typeData] of Object.entries(occupancy.by_type || {})) {
        if (typeData.free > 0) {
            breakdown.push(typeData.name + ' ' + typeData.free);
        }
    }
    document.getElementById('kpi-free-breakdown').textContent =
        breakdown.length > 0 ? breakdown.join(' | ') : '';
}

function renderPendingCheckins(count) {
    document.getElementById('kpi-pending-count').textContent = count;
}

function renderZones(zones) {
    const container = document.getElementById('zones-container');
    const emptyState = document.getElementById('zones-empty');

    if (!zones || zones.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');

    let html = '';
    zones.forEach(zone => {
        html += `
            <div class="zone-row">
                <div class="zone-name">${zone.zone_name}</div>
                <div class="zone-bar-wrapper">
                    <div class="zone-bar-container">
                        <div class="zone-bar" style="width: ${zone.rate}%"></div>
                    </div>
                </div>
                <div class="zone-rate">${zone.rate}%</div>
            </div>
        `;
    });

    container.innerHTML = html;
}
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/beach/insights/dashboard.html
git commit -m "feat(insights): add operational dashboard template

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 1.8: Create Dashboard Route

**Files:**
- Modify: `blueprints/beach/__init__.py`

**Step 1: Add route**

Add to `blueprints/beach/__init__.py` after the reservation routes section (around line 183):

```python
# =============================================================================
# INSIGHTS ROUTES
# =============================================================================

@beach_bp.route('/insights')
@login_required
@permission_required('beach.insights.view')
def insights_dashboard():
    """Display operational insights dashboard."""
    return render_template('beach/insights/dashboard.html')


@beach_bp.route('/insights/analytics')
@login_required
@permission_required('beach.insights.analytics')
def insights_analytics():
    """Display advanced analytics."""
    return render_template('beach/insights/analytics.html')
```

**Step 2: Add helper function for permission check in templates**

Add this context processor or use existing one. Check if `current_user_can` already exists, if not add to the blueprint:

```python
@beach_bp.app_context_processor
def inject_permission_helper():
    """Inject permission helper into templates."""
    from utils.permissions import user_has_permission
    from flask_login import current_user

    def current_user_can(permission_code):
        if not current_user.is_authenticated:
            return False
        return user_has_permission(current_user.id, permission_code)

    return {'current_user_can': current_user_can}
```

**Step 3: Test manually**

```bash
# Start server and navigate to /beach/insights
python app.py
```

Open browser to `http://localhost:5000/beach/insights`

**Step 4: Commit**

```bash
git add blueprints/beach/__init__.py
git commit -m "feat(insights): add dashboard and analytics routes

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Advanced Analytics - Occupancy

### Task 2.1: Add Date Range Occupancy Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetOccupancyRange:
    """Tests for get_occupancy_range function."""

    def test_returns_list_for_date_range(self, app):
        """Returns occupancy data for each day in range."""
        from models.insights import get_occupancy_range
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            result = get_occupancy_range(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)
            assert len(result) == 7  # 7 days

    def test_each_day_has_required_fields(self, app):
        """Each day entry has date, occupied, total, rate."""
        from models.insights import get_occupancy_range
        from datetime import date

        with app.app_context():
            today = date.today().isoformat()
            result = get_occupancy_range(today, today)

            assert len(result) == 1
            day = result[0]
            assert 'date' in day
            assert 'occupied' in day
            assert 'total' in day
            assert 'rate' in day
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyRange -v
```

Expected: FAIL

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
def get_occupancy_range(start_date: str, end_date: str) -> list:
    """
    Get daily occupancy for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        list of dicts with date, occupied, total, rate for each day
    """
    with get_db() as conn:
        # Get total active furniture (constant for all days)
        total_cursor = conn.execute('''
            SELECT COUNT(*) FROM beach_furniture WHERE is_active = 1
        ''')
        total = total_cursor.fetchone()[0]

        # Generate all dates in range
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get occupied counts for the range
        occupied_cursor = conn.execute('''
            SELECT
                rf.assignment_date,
                COUNT(DISTINCT rf.furniture_id) as occupied
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE rf.assignment_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
            GROUP BY rf.assignment_date
        ''', (start_date, end_date))

        occupied_by_date = {row[0]: row[1] for row in occupied_cursor}

        # Build result for each day
        results = []
        current = start
        while current <= end:
            date_str = current.isoformat()
            occupied = occupied_by_date.get(date_str, 0)
            rate = round((occupied / total) * 100, 1) if total > 0 else 0.0

            results.append({
                'date': date_str,
                'occupied': occupied,
                'total': total,
                'rate': rate
            })
            current += timedelta(days=1)

        return results
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyRange -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add date range occupancy query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2.2: Add Occupancy Stats Summary Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetOccupancyStats:
    """Tests for get_occupancy_stats function."""

    def test_returns_summary_stats(self, app):
        """Returns average occupancy, total reservations, no-show rate."""
        from models.insights import get_occupancy_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_occupancy_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'avg_occupancy' in result
            assert 'total_reservations' in result
            assert 'noshow_rate' in result
            assert isinstance(result['avg_occupancy'], float)
            assert isinstance(result['total_reservations'], int)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyStats -v
```

Expected: FAIL

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
def get_occupancy_stats(start_date: str, end_date: str) -> dict:
    """
    Get summary occupancy statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - avg_occupancy: float (average daily occupancy %)
            - total_reservations: int (non-cancelled reservations)
            - noshow_rate: float (no-show percentage)
    """
    # Get daily occupancy data
    daily_data = get_occupancy_range(start_date, end_date)
    avg_occupancy = 0.0
    if daily_data:
        avg_occupancy = round(
            sum(d['rate'] for d in daily_data) / len(daily_data), 1
        )

    with get_db() as conn:
        # Total reservations (non-releasing states)
        res_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
        ''', (start_date, end_date))
        total_reservations = res_cursor.fetchone()[0]

        # No-show count
        noshow_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'no_show'
        ''', (start_date, end_date))
        noshow_count = noshow_cursor.fetchone()[0]

        # Total for rate calculation (including no-shows)
        total_for_rate = conn.execute('''
            SELECT COUNT(DISTINCT r.id)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date)).fetchone()[0]

        noshow_rate = 0.0
        if total_for_rate > 0:
            noshow_rate = round((noshow_count / total_for_rate) * 100, 1)

    return {
        'avg_occupancy': avg_occupancy,
        'total_reservations': total_reservations,
        'noshow_rate': noshow_rate
    }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetOccupancyStats -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add occupancy stats summary query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2.3: Add Occupancy API Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
def test_occupancy_endpoint_returns_range_data(self, authenticated_client, app):
    """GET /beach/api/insights/occupancy returns occupancy data for range."""
    from datetime import date, timedelta

    with app.app_context():
        end_date = date.today()
        start_date = end_date - timedelta(days=6)

        response = authenticated_client.get(
            f'/beach/api/insights/occupancy?start_date={start_date}&end_date={end_date}'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'stats' in data
        assert 'daily' in data
        assert 'by_zone' in data
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestInsightsAPI::test_occupancy_endpoint_returns_range_data -v
```

Expected: FAIL (404)

**Step 3: Add endpoint**

Add to `blueprints/beach/routes/api/insights.py`:

```python
from models.insights import (
    get_occupancy_today,
    get_occupancy_by_zone,
    get_pending_checkins_count,
    get_occupancy_comparison,
    get_occupancy_range,
    get_occupancy_stats
)
from datetime import date, timedelta


# Add this route in the register_routes function:

    @bp.route('/insights/occupancy', methods=['GET'])
    @login_required
    def get_insights_occupancy():
        """
        Get occupancy analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {
                "avg_occupancy": 68.5,
                "total_reservations": 245,
                "noshow_rate": 5.2
            },
            "daily": [...],
            "by_zone": [...]
        }
        """
        try:
            # Get date range from query params
            end_date = request.args.get('end_date', date.today().isoformat())
            start_date = request.args.get(
                'start_date',
                (date.today() - timedelta(days=29)).isoformat()
            )

            stats = get_occupancy_stats(start_date, end_date)
            daily = get_occupancy_range(start_date, end_date)
            # For by_zone, calculate average over the range
            by_zone = _get_average_zone_occupancy(start_date, end_date)

            return jsonify({
                'success': True,
                'stats': stats,
                'daily': daily,
                'by_zone': by_zone
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


def _get_average_zone_occupancy(start_date: str, end_date: str) -> list:
    """Calculate average occupancy by zone over a date range."""
    from models.insights import get_occupancy_by_zone
    from datetime import datetime, timedelta

    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    num_days = (end - start).days + 1

    # Accumulate data
    zone_totals = {}
    current = start
    while current <= end:
        daily_zones = get_occupancy_by_zone(current.isoformat())
        for zone in daily_zones:
            zone_id = zone['zone_id']
            if zone_id not in zone_totals:
                zone_totals[zone_id] = {
                    'zone_name': zone['zone_name'],
                    'total_rate': 0,
                    'total_furniture': zone['total']
                }
            zone_totals[zone_id]['total_rate'] += zone['rate']
        current += timedelta(days=1)

    # Calculate averages
    results = []
    for zone_id, data in zone_totals.items():
        avg_rate = round(data['total_rate'] / num_days, 1)
        results.append({
            'zone_id': zone_id,
            'zone_name': data['zone_name'],
            'rate': avg_rate,
            'total': data['total_furniture']
        })

    return results
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestInsightsAPI::test_occupancy_endpoint_returns_range_data -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add blueprints/beach/routes/api/insights.py tests/test_insights.py
git commit -m "feat(insights): add occupancy analytics API endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Advanced Analytics - Revenue

### Task 3.1: Add Revenue Stats Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetRevenueStats:
    """Tests for get_revenue_stats function."""

    def test_returns_revenue_summary(self, app):
        """Returns total revenue, paid reservations, average."""
        from models.insights import get_revenue_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_revenue_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'total_revenue' in result
            assert 'paid_reservations' in result
            assert 'avg_per_reservation' in result
            assert isinstance(result['total_revenue'], (int, float))
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetRevenueStats -v
```

Expected: FAIL

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
# =============================================================================
# REVENUE METRICS (Advanced Analytics)
# =============================================================================

def get_revenue_stats(start_date: str, end_date: str) -> dict:
    """
    Get revenue statistics for a date range.
    Only includes paquete and consumo_minimo reservation types.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - total_revenue: float
            - paid_reservations: int
            - avg_per_reservation: float
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                COALESCE(SUM(calculated_price), 0) as total_revenue,
                COUNT(*) as paid_reservations
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND r.reservation_type IN ('paquete', 'consumo_minimo')
              AND s.is_availability_releasing = 0
        ''', (start_date, end_date))

        row = cursor.fetchone()
        total_revenue = float(row[0] or 0)
        paid_reservations = row[1] or 0

        avg_per_reservation = 0.0
        if paid_reservations > 0:
            avg_per_reservation = round(total_revenue / paid_reservations, 2)

        return {
            'total_revenue': total_revenue,
            'paid_reservations': paid_reservations,
            'avg_per_reservation': avg_per_reservation
        }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetRevenueStats -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add revenue stats query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3.2: Add Revenue by Type Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetRevenueByType:
    """Tests for get_revenue_by_type function."""

    def test_returns_breakdown_by_reservation_type(self, app):
        """Returns revenue breakdown by reservation type."""
        from models.insights import get_revenue_by_type
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_revenue_by_type(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'by_reservation_type' in result
            assert 'by_customer_type' in result
            assert isinstance(result['by_reservation_type'], list)
            assert isinstance(result['by_customer_type'], list)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetRevenueByType -v
```

Expected: FAIL

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
def get_revenue_by_type(start_date: str, end_date: str) -> dict:
    """
    Get revenue breakdown by reservation type and customer type.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - by_reservation_type: list of {type, count, revenue, percentage}
            - by_customer_type: list of {type, count, revenue, percentage}
    """
    with get_db() as conn:
        # By reservation type
        res_type_cursor = conn.execute('''
            SELECT
                r.reservation_type,
                COUNT(*) as count,
                COALESCE(SUM(r.calculated_price), 0) as revenue
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
            GROUP BY r.reservation_type
        ''', (start_date, end_date))

        by_res_type = []
        total_count = 0
        for row in res_type_cursor:
            by_res_type.append({
                'type': row[0] or 'incluido',
                'count': row[1],
                'revenue': float(row[2])
            })
            total_count += row[1]

        # Calculate percentages
        for item in by_res_type:
            item['percentage'] = round((item['count'] / total_count) * 100, 1) if total_count > 0 else 0

        # By customer type
        cust_type_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(DISTINCT r.id) as count,
                COALESCE(SUM(r.calculated_price), 0) as revenue
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_cust_type = []
        cust_total = 0
        for row in cust_type_cursor:
            by_cust_type.append({
                'type': row[0],
                'count': row[1],
                'revenue': float(row[2])
            })
            cust_total += row[1]

        for item in by_cust_type:
            item['percentage'] = round((item['count'] / cust_total) * 100, 1) if cust_total > 0 else 0

        return {
            'by_reservation_type': by_res_type,
            'by_customer_type': by_cust_type
        }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetRevenueByType -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add revenue by type breakdown query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3.3: Add Top Packages Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetTopPackages:
    """Tests for get_top_packages function."""

    def test_returns_packages_list(self, app):
        """Returns list of top packages by revenue."""
        from models.insights import get_top_packages
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_top_packages(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert isinstance(result, list)
            # Each item should have required fields
            if result:
                pkg = result[0]
                assert 'package_id' in pkg
                assert 'package_name' in pkg
                assert 'sold_count' in pkg
                assert 'revenue' in pkg
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetTopPackages -v
```

Expected: FAIL

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
def get_top_packages(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get top packages by revenue.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Max number of packages to return

    Returns:
        list of dicts with package_id, package_name, sold_count, revenue, percentage
    """
    with get_db() as conn:
        # Get total revenue for percentage calculation
        total_cursor = conn.execute('''
            SELECT COALESCE(SUM(calculated_price), 0)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND r.reservation_type = 'paquete'
              AND s.is_availability_releasing = 0
        ''', (start_date, end_date))
        total_revenue = float(total_cursor.fetchone()[0] or 0)

        cursor = conn.execute('''
            SELECT
                p.id,
                p.package_name,
                COUNT(r.id) as sold_count,
                COALESCE(SUM(r.calculated_price), 0) as revenue
            FROM beach_packages p
            JOIN beach_reservations r ON r.package_id = p.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND r.reservation_type = 'paquete'
              AND s.is_availability_releasing = 0
            GROUP BY p.id, p.package_name
            ORDER BY revenue DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            revenue = float(row[3])
            percentage = round((revenue / total_revenue) * 100, 1) if total_revenue > 0 else 0
            results.append({
                'package_id': row[0],
                'package_name': row[1],
                'sold_count': row[2],
                'revenue': revenue,
                'percentage': percentage
            })

        return results
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetTopPackages -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add top packages query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 3.4: Add Revenue API Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/insights.py`

**Step 1: Add endpoint**

Add to `blueprints/beach/routes/api/insights.py` in register_routes:

```python
from models.insights import (
    # ... existing imports ...
    get_revenue_stats,
    get_revenue_by_type,
    get_top_packages
)

    @bp.route('/insights/revenue', methods=['GET'])
    @login_required
    def get_insights_revenue():
        """
        Get revenue analytics for a date range.

        Query params:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)

        Response JSON:
        {
            "success": true,
            "stats": {...},
            "by_type": {...},
            "top_packages": [...]
        }
        """
        try:
            end_date = request.args.get('end_date', date.today().isoformat())
            start_date = request.args.get(
                'start_date',
                (date.today() - timedelta(days=29)).isoformat()
            )

            stats = get_revenue_stats(start_date, end_date)
            by_type = get_revenue_by_type(start_date, end_date)
            top_packages = get_top_packages(start_date, end_date)

            return jsonify({
                'success': True,
                'stats': stats,
                'by_type': by_type,
                'top_packages': top_packages
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
```

**Step 2: Test manually**

```bash
curl "http://localhost:5000/beach/api/insights/revenue?start_date=2026-01-01&end_date=2026-01-10"
```

**Step 3: Commit**

```bash
git add blueprints/beach/routes/api/insights.py
git commit -m "feat(insights): add revenue analytics API endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Advanced Analytics - Customers

### Task 4.1: Add Customer Stats Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

Add to `tests/test_insights.py`:

```python
class TestGetCustomerStats:
    """Tests for get_customer_stats function."""

    def test_returns_customer_summary(self, app):
        """Returns unique customers, avg group size, returning rate."""
        from models.insights import get_customer_stats
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_stats(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'unique_customers' in result
            assert 'avg_group_size' in result
            assert 'returning_rate' in result
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_insights.py::TestGetCustomerStats -v
```

**Step 3: Write implementation**

Add to `models/insights.py`:

```python
# =============================================================================
# CUSTOMER METRICS (Advanced Analytics)
# =============================================================================

def get_customer_stats(start_date: str, end_date: str) -> dict:
    """
    Get customer statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        dict with:
            - unique_customers: int
            - avg_group_size: float
            - returning_rate: float (% with >1 reservation ever)
    """
    with get_db() as conn:
        # Unique customers in period
        unique_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.customer_id)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        unique_customers = unique_cursor.fetchone()[0]

        # Average group size
        avg_cursor = conn.execute('''
            SELECT AVG(r.num_people)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        avg_group_size = round(float(avg_cursor.fetchone()[0] or 0), 1)

        # Returning customers (have >1 reservation total, not just in period)
        if unique_customers > 0:
            returning_cursor = conn.execute('''
                SELECT COUNT(DISTINCT r.customer_id)
                FROM beach_reservations r
                WHERE r.start_date BETWEEN ? AND ?
                  AND r.customer_id IN (
                      SELECT customer_id
                      FROM beach_reservations
                      GROUP BY customer_id
                      HAVING COUNT(*) > 1
                  )
            ''', (start_date, end_date))
            returning_count = returning_cursor.fetchone()[0]
            returning_rate = round((returning_count / unique_customers) * 100, 1)
        else:
            returning_rate = 0.0

        return {
            'unique_customers': unique_customers,
            'avg_group_size': avg_group_size,
            'returning_rate': returning_rate
        }
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_insights.py::TestGetCustomerStats -v
```

**Step 5: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add customer stats query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.2: Add Customer Segmentation Query

**Files:**
- Modify: `models/insights.py`
- Modify: `tests/test_insights.py`

**Step 1: Write the failing test**

```python
class TestGetCustomerSegmentation:
    """Tests for get_customer_segmentation function."""

    def test_returns_segmentation_data(self, app):
        """Returns new vs returning and interno vs externo breakdown."""
        from models.insights import get_customer_segmentation
        from datetime import date, timedelta

        with app.app_context():
            end_date = date.today()
            start_date = end_date - timedelta(days=29)

            result = get_customer_segmentation(
                start_date.isoformat(),
                end_date.isoformat()
            )

            assert 'by_status' in result  # new vs returning
            assert 'by_type' in result    # interno vs externo
```

**Step 2: Run test and implement**

Add to `models/insights.py`:

```python
def get_customer_segmentation(start_date: str, end_date: str) -> dict:
    """
    Get customer segmentation data.

    Returns:
        dict with:
            - by_status: list [{status: 'new'/'returning', count, percentage}]
            - by_type: list [{type: 'interno'/'externo', count, percentage}]
    """
    with get_db() as conn:
        # By status (new vs returning)
        # New = first reservation is within the date range
        new_cursor = conn.execute('''
            SELECT COUNT(DISTINCT r.customer_id)
            FROM beach_reservations r
            WHERE r.start_date BETWEEN ? AND ?
              AND r.customer_id IN (
                  SELECT customer_id
                  FROM beach_reservations
                  GROUP BY customer_id
                  HAVING MIN(start_date) BETWEEN ? AND ?
              )
        ''', (start_date, end_date, start_date, end_date))
        new_count = new_cursor.fetchone()[0]

        total_cursor = conn.execute('''
            SELECT COUNT(DISTINCT customer_id)
            FROM beach_reservations
            WHERE start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        total = total_cursor.fetchone()[0]

        returning_count = total - new_count

        by_status = []
        if total > 0:
            by_status = [
                {'status': 'new', 'count': new_count,
                 'percentage': round((new_count / total) * 100, 1)},
                {'status': 'returning', 'count': returning_count,
                 'percentage': round((returning_count / total) * 100, 1)}
            ]

        # By customer type
        type_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(DISTINCT r.customer_id) as count
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_type = []
        type_total = 0
        type_data = []
        for row in type_cursor:
            type_data.append({'type': row[0], 'count': row[1]})
            type_total += row[1]

        for item in type_data:
            item['percentage'] = round((item['count'] / type_total) * 100, 1) if type_total > 0 else 0
            by_type.append(item)

        return {
            'by_status': by_status,
            'by_type': by_type
        }
```

**Step 3: Commit**

```bash
git add models/insights.py tests/test_insights.py
git commit -m "feat(insights): add customer segmentation query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.3: Add Top Customers Query

**Files:**
- Modify: `models/insights.py`

Add to `models/insights.py`:

```python
def get_top_customers(start_date: str, end_date: str, limit: int = 10) -> list:
    """
    Get top customers by total spend.

    Returns:
        list of dicts with customer info, reservation count, total spend
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                c.id,
                c.first_name,
                c.last_name,
                c.customer_type,
                c.room_number,
                COUNT(r.id) as reservation_count,
                COALESCE(SUM(r.calculated_price), 0) as total_spend
            FROM beach_customers c
            JOIN beach_reservations r ON r.customer_id = c.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
            GROUP BY c.id
            ORDER BY total_spend DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        results = []
        for row in cursor:
            name = f"{row[1]} {row[2]}"
            if row[3] == 'interno' and row[4]:
                name += f" (H.{row[4]})"
            results.append({
                'customer_id': row[0],
                'customer_name': name,
                'customer_type': row[3],
                'reservation_count': row[5],
                'total_spend': float(row[6])
            })

        return results
```

**Commit:**

```bash
git add models/insights.py
git commit -m "feat(insights): add top customers query

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.4: Add Popular Preferences and Tags Query

**Files:**
- Modify: `models/insights.py`

Add to `models/insights.py`:

```python
def get_popular_preferences(start_date: str, end_date: str, limit: int = 5) -> list:
    """
    Get most requested preferences in reservations.

    Returns:
        list of dicts with preference name and count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                p.name,
                COUNT(rp.id) as request_count
            FROM beach_preferences p
            JOIN beach_reservation_preferences rp ON rp.preference_id = p.id
            JOIN beach_reservations r ON rp.reservation_id = r.id
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY p.id, p.name
            ORDER BY request_count DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        return [{'name': row[0], 'count': row[1]} for row in cursor]


def get_popular_tags(start_date: str, end_date: str, limit: int = 5) -> list:
    """
    Get most used customer tags.

    Returns:
        list of dicts with tag name and count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                t.name,
                COUNT(DISTINCT r.customer_id) as customer_count
            FROM beach_tags t
            JOIN beach_customer_tags ct ON ct.tag_id = t.id
            JOIN beach_reservations r ON r.customer_id = ct.customer_id
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY t.id, t.name
            ORDER BY customer_count DESC
            LIMIT ?
        ''', (start_date, end_date, limit))

        return [{'name': row[0], 'count': row[1]} for row in cursor]
```

**Commit:**

```bash
git add models/insights.py
git commit -m "feat(insights): add popular preferences and tags queries

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4.5: Add Customers API Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/insights.py`

Add to register_routes:

```python
from models.insights import (
    # ... existing imports ...
    get_customer_stats,
    get_customer_segmentation,
    get_top_customers,
    get_popular_preferences,
    get_popular_tags
)

    @bp.route('/insights/customers', methods=['GET'])
    @login_required
    def get_insights_customers():
        """
        Get customer analytics for a date range.
        """
        try:
            end_date = request.args.get('end_date', date.today().isoformat())
            start_date = request.args.get(
                'start_date',
                (date.today() - timedelta(days=29)).isoformat()
            )

            stats = get_customer_stats(start_date, end_date)
            segmentation = get_customer_segmentation(start_date, end_date)
            top_customers = get_top_customers(start_date, end_date)
            preferences = get_popular_preferences(start_date, end_date)
            tags = get_popular_tags(start_date, end_date)

            return jsonify({
                'success': True,
                'stats': stats,
                'segmentation': segmentation,
                'top_customers': top_customers,
                'preferences': preferences,
                'tags': tags
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
```

**Commit:**

```bash
git add blueprints/beach/routes/api/insights.py
git commit -m "feat(insights): add customers analytics API endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: Advanced Analytics - Patterns

### Task 5.1: Add Booking Patterns Queries

**Files:**
- Modify: `models/insights.py`

Add to `models/insights.py`:

```python
# =============================================================================
# BOOKING PATTERNS (Advanced Analytics)
# =============================================================================

def get_pattern_stats(start_date: str, end_date: str) -> dict:
    """
    Get booking pattern statistics.

    Returns:
        dict with avg_lead_time, cancellation_rate, noshow_rate
    """
    with get_db() as conn:
        # Average lead time
        lead_cursor = conn.execute('''
            SELECT AVG(JULIANDAY(start_date) - JULIANDAY(DATE(created_at)))
            FROM beach_reservations
            WHERE start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        avg_lead_time = round(float(lead_cursor.fetchone()[0] or 0), 1)

        # Total reservations for rate calculation
        total_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations
            WHERE start_date BETWEEN ? AND ?
        ''', (start_date, end_date))
        total = total_cursor.fetchone()[0]

        # Cancellation count
        cancel_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'cancelada'
        ''', (start_date, end_date))
        cancel_count = cancel_cursor.fetchone()[0]

        # No-show count
        noshow_cursor = conn.execute('''
            SELECT COUNT(*)
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.code = 'no_show'
        ''', (start_date, end_date))
        noshow_count = noshow_cursor.fetchone()[0]

        cancellation_rate = round((cancel_count / total) * 100, 1) if total > 0 else 0
        noshow_rate = round((noshow_count / total) * 100, 1) if total > 0 else 0

        return {
            'avg_lead_time': avg_lead_time,
            'cancellation_rate': cancellation_rate,
            'noshow_rate': noshow_rate
        }


def get_reservations_by_day_of_week(start_date: str, end_date: str) -> list:
    """
    Get reservation count by day of week.

    Returns:
        list of dicts with day_of_week (0=Sun, 1=Mon, etc), name, count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                CAST(strftime('%w', start_date) AS INTEGER) as day_of_week,
                COUNT(*) as count
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
              AND s.is_availability_releasing = 0
            GROUP BY day_of_week
            ORDER BY day_of_week
        ''', (start_date, end_date))

        day_names = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
        results = {i: 0 for i in range(7)}

        for row in cursor:
            results[row[0]] = row[1]

        return [
            {'day_of_week': i, 'name': day_names[i], 'count': results[i]}
            for i in range(7)
        ]


def get_lead_time_distribution(start_date: str, end_date: str) -> list:
    """
    Get distribution of booking lead times.

    Returns:
        list of dicts with bucket name and count
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT
                CASE
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) = 0 THEN 'same_day'
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 2 THEN '1_2_days'
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 7 THEN '3_7_days'
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 14 THEN '8_14_days'
                    ELSE '15_plus_days'
                END as bucket,
                COUNT(*) as count
            FROM beach_reservations
            WHERE start_date BETWEEN ? AND ?
            GROUP BY bucket
        ''', (start_date, end_date))

        bucket_order = ['same_day', '1_2_days', '3_7_days', '8_14_days', '15_plus_days']
        bucket_names = {
            'same_day': 'Mismo día',
            '1_2_days': '1-2 días',
            '3_7_days': '3-7 días',
            '8_14_days': '8-14 días',
            '15_plus_days': '15+ días'
        }

        data = {b: 0 for b in bucket_order}
        total = 0
        for row in cursor:
            if row[0] in data:
                data[row[0]] = row[1]
                total += row[1]

        return [
            {
                'bucket': b,
                'name': bucket_names[b],
                'count': data[b],
                'percentage': round((data[b] / total) * 100, 1) if total > 0 else 0
            }
            for b in bucket_order
        ]


def get_cancellation_breakdown(start_date: str, end_date: str) -> dict:
    """
    Get cancellation breakdown by customer type and lead time.

    Returns:
        dict with by_customer_type and by_lead_time lists
    """
    with get_db() as conn:
        # By customer type
        cust_cursor = conn.execute('''
            SELECT
                c.customer_type,
                COUNT(CASE WHEN s.code = 'cancelada' THEN 1 END) as cancelled,
                COUNT(*) as total
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY c.customer_type
        ''', (start_date, end_date))

        by_customer_type = []
        for row in cust_cursor:
            rate = round((row[1] / row[2]) * 100, 1) if row[2] > 0 else 0
            by_customer_type.append({
                'type': row[0],
                'rate': rate
            })

        # By lead time bucket
        lead_cursor = conn.execute('''
            SELECT
                CASE
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) = 0 THEN 'same_day'
                    WHEN JULIANDAY(start_date) - JULIANDAY(DATE(created_at)) <= 7 THEN '1_7_days'
                    ELSE '8_plus_days'
                END as bucket,
                COUNT(CASE WHEN s.code = 'cancelada' THEN 1 END) as cancelled,
                COUNT(*) as total
            FROM beach_reservations r
            JOIN beach_reservation_states s ON r.state_id = s.id
            WHERE r.start_date BETWEEN ? AND ?
            GROUP BY bucket
        ''', (start_date, end_date))

        bucket_names = {
            'same_day': 'Mismo día',
            '1_7_days': '1-7 días',
            '8_plus_days': '8+ días'
        }

        by_lead_time = []
        for row in lead_cursor:
            rate = round((row[1] / row[2]) * 100, 1) if row[2] > 0 else 0
            by_lead_time.append({
                'bucket': row[0],
                'name': bucket_names.get(row[0], row[0]),
                'rate': rate
            })

        return {
            'by_customer_type': by_customer_type,
            'by_lead_time': by_lead_time
        }
```

**Commit:**

```bash
git add models/insights.py
git commit -m "feat(insights): add booking patterns queries

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5.2: Add Patterns API Endpoint

**Files:**
- Modify: `blueprints/beach/routes/api/insights.py`

Add to register_routes:

```python
from models.insights import (
    # ... existing imports ...
    get_pattern_stats,
    get_reservations_by_day_of_week,
    get_lead_time_distribution,
    get_cancellation_breakdown
)

    @bp.route('/insights/patterns', methods=['GET'])
    @login_required
    def get_insights_patterns():
        """
        Get booking pattern analytics for a date range.
        """
        try:
            end_date = request.args.get('end_date', date.today().isoformat())
            start_date = request.args.get(
                'start_date',
                (date.today() - timedelta(days=29)).isoformat()
            )

            stats = get_pattern_stats(start_date, end_date)
            by_day_of_week = get_reservations_by_day_of_week(start_date, end_date)
            lead_time = get_lead_time_distribution(start_date, end_date)
            cancellation = get_cancellation_breakdown(start_date, end_date)

            return jsonify({
                'success': True,
                'stats': stats,
                'by_day_of_week': by_day_of_week,
                'lead_time': lead_time,
                'cancellation': cancellation
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
```

**Commit:**

```bash
git add blueprints/beach/routes/api/insights.py
git commit -m "feat(insights): add booking patterns API endpoint

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 6: Analytics Template

### Task 6.1: Create Analytics Page Template

**Files:**
- Create: `templates/beach/insights/analytics.html`
- Create: `static/js/insights/chart-config.js`
- Create: `static/js/insights/analytics.js`

Due to the length of this task, the template and JS files will be created in implementation. The structure follows the design document with:

1. Date range picker at top
2. Four collapsible sections: Ocupación, Ingresos, Clientes, Patrones
3. Chart.js visualizations following design system colors
4. KPI cards, donut charts, bar charts, line charts, and tables

**Commit after creation:**

```bash
git add templates/beach/insights/analytics.html static/js/insights/
git commit -m "feat(insights): add advanced analytics template and JS

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 7: Polish & Testing

### Task 7.1: Run All Tests

```bash
python -m pytest tests/test_insights.py -v
```

Ensure all tests pass.

### Task 7.2: Manual Testing Checklist

- [ ] Dashboard loads with correct today's data
- [ ] Refresh button updates data
- [ ] Zone bars render correctly
- [ ] Analytics page loads all sections
- [ ] Date range picker works
- [ ] Charts render with correct colors
- [ ] Tables display data properly
- [ ] Collapsible sections work
- [ ] Mobile responsive layout
- [ ] Loading states show/hide correctly

### Task 7.3: Update DEVELOPMENT_PLAN.md

Add entry for insights module completion.

### Task 7.4: Final Commit

```bash
git add .
git commit -m "feat(insights): complete insights module implementation

- Operational dashboard with today's KPIs
- Advanced analytics with date range
- Occupancy, revenue, customer, and pattern analytics
- Chart.js visualizations
- Full test coverage

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1 | 1.1-1.8 | Foundation: Models, API, Dashboard |
| 2 | 2.1-2.3 | Occupancy Analytics |
| 3 | 3.1-3.4 | Revenue Analytics |
| 4 | 4.1-4.5 | Customer Analytics |
| 5 | 5.1-5.2 | Booking Patterns |
| 6 | 6.1 | Analytics Template |
| 7 | 7.1-7.4 | Polish & Testing |

**Total Tasks:** ~25 tasks
**Estimated Implementation:** Follow TDD for each task
