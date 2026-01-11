# Move Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a map mode that allows staff to reorganize reservation furniture assignments via pick-up-and-place workflow with preference-based guidance.

**Architecture:** Backend API endpoints handle unassign/assign operations with immediate persistence. Frontend MoveMode controller manages state, pool panel displays unassigned reservations, and PreferenceHighlighter guides placement. All changes auto-save with undo capability.

**Tech Stack:** Flask API endpoints, SQLite with transactions, ES6 JavaScript modules, CSS for panel styling.

**Design Reference:** `docs/plans/2026-01-11-move-mode-design.md`

---

## Task 1: Model - Unassign Furniture Function

**Files:**
- Create: `models/move_mode.py`
- Test: `tests/test_move_mode.py`

**Step 1: Write the failing test**

Create `tests/test_move_mode.py`:
```python
"""
Tests for move mode feature.
"""

import pytest
from datetime import date


class TestUnassignFurniture:
    """Tests for unassigning furniture from reservations."""

    def test_unassign_single_furniture_success(self, app):
        """Should unassign one furniture from a reservation for a specific date."""
        from models.move_mode import unassign_furniture_for_date
        from models.reservation import get_beach_reservation_by_id
        from database import get_db

        with app.app_context():
            # Setup: Create reservation with furniture assignment
            with get_db() as conn:
                cursor = conn.cursor()
                # Get a reservation that has furniture assigned today
                cursor.execute("""
                    SELECT rf.reservation_id, rf.furniture_id, rf.assignment_date
                    FROM beach_reservation_furniture rf
                    JOIN beach_reservations r ON rf.reservation_id = r.id
                    WHERE rf.assignment_date = date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

            if not row:
                pytest.skip("No reservation with furniture for today")

            reservation_id = row['reservation_id']
            furniture_id = row['furniture_id']
            assignment_date = row['assignment_date']

            # Execute
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[furniture_id],
                assignment_date=assignment_date
            )

            # Verify
            assert result['success'] is True
            assert result['unassigned_count'] == 1
            assert furniture_id in result['furniture_ids']

            # Verify furniture is no longer assigned
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
                """, (reservation_id, furniture_id, assignment_date))
                assert cursor.fetchone()['cnt'] == 0
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestUnassignFurniture::test_unassign_single_furniture_success -v`

Expected: FAIL with "cannot import name 'unassign_furniture_for_date'"

**Step 3: Write minimal implementation**

Create `models/move_mode.py`:
```python
"""
Move mode model functions.

Handles furniture assignment changes during move mode operations.
"""

from database import get_db
from datetime import datetime
from typing import List, Dict, Any, Optional


def unassign_furniture_for_date(
    reservation_id: int,
    furniture_ids: List[int],
    assignment_date: str
) -> Dict[str, Any]:
    """
    Unassign furniture from a reservation for a specific date.

    Args:
        reservation_id: The reservation to modify
        furniture_ids: List of furniture IDs to unassign
        assignment_date: Date in YYYY-MM-DD format

    Returns:
        Dict with success status and unassigned furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        unassigned = []
        for furniture_id in furniture_ids:
            cursor.execute("""
                DELETE FROM beach_reservation_furniture
                WHERE reservation_id = ?
                AND furniture_id = ?
                AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.rowcount > 0:
                unassigned.append(furniture_id)

        conn.commit()

        return {
            'success': True,
            'unassigned_count': len(unassigned),
            'furniture_ids': unassigned,
            'reservation_id': reservation_id,
            'date': assignment_date
        }
```

**Step 4: Run test to verify it passes**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestUnassignFurniture::test_unassign_single_furniture_success -v`

Expected: PASS

**Step 5: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add models/move_mode.py tests/test_move_mode.py
git commit -m "feat(models): add unassign_furniture_for_date function"
```

---

## Task 2: Model - Assign Furniture Function

**Files:**
- Modify: `models/move_mode.py`
- Modify: `tests/test_move_mode.py`

**Step 1: Write the failing test**

Add to `tests/test_move_mode.py`:
```python
class TestAssignFurniture:
    """Tests for assigning furniture to reservations."""

    def test_assign_furniture_success(self, app):
        """Should assign available furniture to a reservation for a specific date."""
        from models.move_mode import assign_furniture_for_date, unassign_furniture_for_date
        from database import get_db

        with app.app_context():
            # Setup: Find a reservation and available furniture
            with get_db() as conn:
                cursor = conn.cursor()

                # Get a reservation with furniture
                cursor.execute("""
                    SELECT rf.reservation_id, rf.furniture_id, rf.assignment_date
                    FROM beach_reservation_furniture rf
                    WHERE rf.assignment_date = date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if not row:
                    pytest.skip("No reservation with furniture for today")

                reservation_id = row['reservation_id']
                original_furniture_id = row['furniture_id']
                assignment_date = row['assignment_date']

                # Find available furniture (not assigned today)
                cursor.execute("""
                    SELECT f.id
                    FROM beach_furniture f
                    WHERE f.id NOT IN (
                        SELECT furniture_id
                        FROM beach_reservation_furniture
                        WHERE assignment_date = ?
                    )
                    AND f.active = 1
                    LIMIT 1
                """, (assignment_date,))
                available = cursor.fetchone()

            if not available:
                pytest.skip("No available furniture for today")

            new_furniture_id = available['id']

            # First unassign original
            unassign_furniture_for_date(reservation_id, [original_furniture_id], assignment_date)

            # Execute: Assign new furniture
            result = assign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=[new_furniture_id],
                assignment_date=assignment_date
            )

            # Verify
            assert result['success'] is True
            assert result['assigned_count'] == 1
            assert new_furniture_id in result['furniture_ids']

            # Verify furniture is assigned
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM beach_reservation_furniture
                    WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
                """, (reservation_id, new_furniture_id, assignment_date))
                assert cursor.fetchone()['cnt'] == 1

    def test_assign_furniture_already_taken_fails(self, app):
        """Should fail when furniture is already assigned to another reservation."""
        from models.move_mode import assign_furniture_for_date
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()

                # Get two different reservations on same date
                cursor.execute("""
                    SELECT rf.reservation_id, rf.furniture_id, rf.assignment_date
                    FROM beach_reservation_furniture rf
                    WHERE rf.assignment_date = date('now')
                    LIMIT 2
                """)
                rows = cursor.fetchall()

            if len(rows) < 2:
                pytest.skip("Need at least 2 reservations with furniture today")

            # Try to assign reservation 1's furniture to reservation 2
            result = assign_furniture_for_date(
                reservation_id=rows[1]['reservation_id'],
                furniture_ids=[rows[0]['furniture_id']],
                assignment_date=rows[0]['assignment_date']
            )

            assert result['success'] is False
            assert 'ocupado' in result['error'].lower() or 'unavailable' in result['error'].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestAssignFurniture -v`

Expected: FAIL with "cannot import name 'assign_furniture_for_date'"

**Step 3: Write minimal implementation**

Add to `models/move_mode.py`:
```python
def assign_furniture_for_date(
    reservation_id: int,
    furniture_ids: List[int],
    assignment_date: str
) -> Dict[str, Any]:
    """
    Assign furniture to a reservation for a specific date.

    Args:
        reservation_id: The reservation to modify
        furniture_ids: List of furniture IDs to assign
        assignment_date: Date in YYYY-MM-DD format

    Returns:
        Dict with success status and assigned furniture info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check availability first
        placeholders = ','.join('?' * len(furniture_ids))
        cursor.execute(f"""
            SELECT rf.furniture_id, r.id as res_id, c.first_name, c.last_name
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE rf.furniture_id IN ({placeholders})
            AND rf.assignment_date = ?
            AND rf.reservation_id != ?
        """, (*furniture_ids, assignment_date, reservation_id))

        conflicts = cursor.fetchall()
        if conflicts:
            conflict = conflicts[0]
            return {
                'success': False,
                'error': f"Mobiliario ocupado por {conflict['first_name']} {conflict['last_name']}",
                'conflicts': [dict(c) for c in conflicts]
            }

        # Assign furniture
        assigned = []
        for furniture_id in furniture_ids:
            # Check if already assigned to this reservation
            cursor.execute("""
                SELECT id FROM beach_reservation_furniture
                WHERE reservation_id = ? AND furniture_id = ? AND assignment_date = ?
            """, (reservation_id, furniture_id, assignment_date))

            if cursor.fetchone():
                # Already assigned, skip
                assigned.append(furniture_id)
                continue

            cursor.execute("""
                INSERT INTO beach_reservation_furniture
                (reservation_id, furniture_id, assignment_date)
                VALUES (?, ?, ?)
            """, (reservation_id, furniture_id, assignment_date))
            assigned.append(furniture_id)

        conn.commit()

        return {
            'success': True,
            'assigned_count': len(assigned),
            'furniture_ids': assigned,
            'reservation_id': reservation_id,
            'date': assignment_date
        }
```

**Step 4: Run test to verify it passes**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestAssignFurniture -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add models/move_mode.py tests/test_move_mode.py
git commit -m "feat(models): add assign_furniture_for_date function"
```

---

## Task 3: Model - Get Reservation Pool Data

**Files:**
- Modify: `models/move_mode.py`
- Modify: `tests/test_move_mode.py`

**Step 1: Write the failing test**

Add to `tests/test_move_mode.py`:
```python
class TestGetPoolData:
    """Tests for getting reservation data for the pool panel."""

    def test_get_reservation_pool_data(self, app):
        """Should return complete reservation data for pool display."""
        from models.move_mode import get_reservation_pool_data
        from database import get_db

        with app.app_context():
            # Get a reservation ID
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.id, r.start_date
                    FROM beach_reservations r
                    JOIN beach_reservation_furniture rf ON r.id = rf.reservation_id
                    WHERE r.start_date <= date('now') AND r.end_date >= date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

            if not row:
                pytest.skip("No active reservation found")

            result = get_reservation_pool_data(row['id'], row['start_date'])

            # Verify structure
            assert 'reservation_id' in result
            assert 'customer_name' in result
            assert 'room_number' in result
            assert 'num_people' in result
            assert 'preferences' in result
            assert 'original_furniture' in result
            assert 'is_multiday' in result
            assert 'total_days' in result
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestGetPoolData -v`

Expected: FAIL with "cannot import name 'get_reservation_pool_data'"

**Step 3: Write minimal implementation**

Add to `models/move_mode.py`:
```python
def get_reservation_pool_data(
    reservation_id: int,
    target_date: str
) -> Dict[str, Any]:
    """
    Get comprehensive reservation data for the pool panel display.

    Args:
        reservation_id: The reservation ID
        target_date: The date being viewed (YYYY-MM-DD)

    Returns:
        Dict with reservation details, customer info, preferences,
        original furniture, and multi-day info
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get reservation and customer info
        cursor.execute("""
            SELECT
                r.id,
                r.ticket_number,
                r.num_people,
                r.start_date,
                r.end_date,
                r.preferences,
                r.notes,
                r.parent_reservation_id,
                c.id as customer_id,
                c.first_name,
                c.last_name,
                c.room_number,
                c.customer_type,
                c.email,
                c.phone
            FROM beach_reservations r
            JOIN beach_customers c ON r.customer_id = c.id
            WHERE r.id = ?
        """, (reservation_id,))

        res = cursor.fetchone()
        if not res:
            return {'error': 'Reserva no encontrada'}

        # Get furniture assignments for target date
        cursor.execute("""
            SELECT
                f.id,
                f.number,
                ft.name as furniture_type,
                f.capacity,
                z.name as zone_name
            FROM beach_reservation_furniture rf
            JOIN beach_furniture f ON rf.furniture_id = f.id
            JOIN beach_furniture_types ft ON f.furniture_type_id = ft.id
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE rf.reservation_id = ? AND rf.assignment_date = ?
        """, (reservation_id, target_date))

        furniture = [dict(row) for row in cursor.fetchall()]

        # Calculate multi-day info
        start = datetime.strptime(res['start_date'], '%Y-%m-%d').date()
        end = datetime.strptime(res['end_date'], '%Y-%m-%d').date()
        total_days = (end - start).days + 1
        is_multiday = total_days > 1

        # Get all day assignments for multi-day
        day_assignments = {}
        if is_multiday:
            cursor.execute("""
                SELECT
                    rf.assignment_date,
                    GROUP_CONCAT(f.number) as furniture_numbers
                FROM beach_reservation_furniture rf
                JOIN beach_furniture f ON rf.furniture_id = f.id
                WHERE rf.reservation_id = ?
                GROUP BY rf.assignment_date
                ORDER BY rf.assignment_date
            """, (reservation_id,))

            for row in cursor.fetchall():
                day_assignments[row['assignment_date']] = row['furniture_numbers']

        # Parse preferences
        preferences = []
        if res['preferences']:
            pref_codes = [p.strip() for p in res['preferences'].split(',') if p.strip()]
            if pref_codes:
                placeholders = ','.join('?' * len(pref_codes))
                cursor.execute(f"""
                    SELECT code, name, icon
                    FROM beach_preferences
                    WHERE code IN ({placeholders})
                """, pref_codes)
                preferences = [dict(row) for row in cursor.fetchall()]

        return {
            'reservation_id': res['id'],
            'ticket_number': res['ticket_number'],
            'customer_id': res['customer_id'],
            'customer_name': f"{res['first_name']} {res['last_name']}",
            'customer_type': res['customer_type'],
            'room_number': res['room_number'],
            'email': res['email'],
            'phone': res['phone'],
            'num_people': res['num_people'],
            'preferences': preferences,
            'notes': res['notes'],
            'original_furniture': furniture,
            'is_multiday': is_multiday,
            'total_days': total_days,
            'start_date': res['start_date'],
            'end_date': res['end_date'],
            'day_assignments': day_assignments,
            'target_date': target_date
        }
```

**Step 4: Run test to verify it passes**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestGetPoolData -v`

Expected: PASS

**Step 5: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add models/move_mode.py tests/test_move_mode.py
git commit -m "feat(models): add get_reservation_pool_data function"
```

---

## Task 4: Model - Get Furniture Preference Matches

**Files:**
- Modify: `models/move_mode.py`
- Modify: `tests/test_move_mode.py`

**Step 1: Write the failing test**

Add to `tests/test_move_mode.py`:
```python
class TestPreferenceMatching:
    """Tests for furniture preference matching."""

    def test_get_furniture_preference_matches(self, app):
        """Should return furniture with preference match scores."""
        from models.move_mode import get_furniture_preference_matches
        from database import get_db

        with app.app_context():
            result = get_furniture_preference_matches(
                preference_codes=['pref_sombra', 'pref_primera_linea'],
                target_date='2026-01-15'
            )

            assert 'furniture' in result
            assert isinstance(result['furniture'], list)

            # Each furniture should have match info
            for f in result['furniture']:
                assert 'id' in f
                assert 'number' in f
                assert 'available' in f
                assert 'match_score' in f
                assert 'matched_preferences' in f
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestPreferenceMatching -v`

Expected: FAIL with "cannot import name 'get_furniture_preference_matches'"

**Step 3: Write minimal implementation**

Add to `models/move_mode.py`:
```python
def get_furniture_preference_matches(
    preference_codes: List[str],
    target_date: str,
    zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get all furniture with preference match scores for a given date.

    Args:
        preference_codes: List of preference codes to match
        target_date: Date to check availability (YYYY-MM-DD)
        zone_id: Optional zone to filter by

    Returns:
        Dict with furniture list including availability and match scores
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get preference feature mappings
        pref_features = {}
        if preference_codes:
            placeholders = ','.join('?' * len(preference_codes))
            cursor.execute(f"""
                SELECT code, maps_to_feature
                FROM beach_preferences
                WHERE code IN ({placeholders})
            """, preference_codes)
            pref_features = {row['code']: row['maps_to_feature'] for row in cursor.fetchall()}

        # Get all active furniture
        zone_filter = "AND f.zone_id = ?" if zone_id else ""
        zone_params = (zone_id,) if zone_id else ()

        cursor.execute(f"""
            SELECT
                f.id,
                f.number,
                f.capacity,
                f.features,
                f.zone_id,
                ft.name as furniture_type,
                z.name as zone_name
            FROM beach_furniture f
            JOIN beach_furniture_types ft ON f.furniture_type_id = ft.id
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE f.active = 1
            AND ft.is_decorative = 0
            {zone_filter}
            ORDER BY z.sort_order, f.number
        """, zone_params)

        all_furniture = [dict(row) for row in cursor.fetchall()]

        # Get occupied furniture for the date
        cursor.execute("""
            SELECT DISTINCT rf.furniture_id
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_reservation_states rs ON r.state_id = rs.id
            WHERE rf.assignment_date = ?
            AND rs.is_availability_releasing = 0
        """, (target_date,))

        occupied_ids = {row['furniture_id'] for row in cursor.fetchall()}

        # Calculate match scores
        result_furniture = []
        for f in all_furniture:
            furniture_features = set()
            if f['features']:
                furniture_features = {feat.strip() for feat in f['features'].split(',') if feat.strip()}

            matched = []
            for pref_code, feature in pref_features.items():
                if feature and feature in furniture_features:
                    matched.append(pref_code)

            total_prefs = len(preference_codes) if preference_codes else 1
            match_score = len(matched) / total_prefs if total_prefs > 0 else 0

            result_furniture.append({
                'id': f['id'],
                'number': f['number'],
                'capacity': f['capacity'],
                'furniture_type': f['furniture_type'],
                'zone_id': f['zone_id'],
                'zone_name': f['zone_name'],
                'available': f['id'] not in occupied_ids,
                'match_score': match_score,
                'matched_preferences': matched
            })

        return {
            'furniture': result_furniture,
            'date': target_date,
            'preferences_requested': preference_codes
        }
```

**Step 4: Run test to verify it passes**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode.py::TestPreferenceMatching -v`

Expected: PASS

**Step 5: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add models/move_mode.py tests/test_move_mode.py
git commit -m "feat(models): add get_furniture_preference_matches function"
```

---

## Task 5: API - Create Move Mode Routes File

**Files:**
- Create: `blueprints/beach/routes/api/move_mode.py`
- Modify: `blueprints/beach/__init__.py` (register routes)
- Create: `tests/test_move_mode_api.py`

**Step 1: Write the failing test**

Create `tests/test_move_mode_api.py`:
```python
"""
Tests for move mode API endpoints.
"""

import pytest
import json


class TestMoveModeUnassignAPI:
    """Tests for the unassign furniture endpoint."""

    def test_unassign_furniture_success(self, client, app):
        """Should unassign furniture via POST."""
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT rf.reservation_id, rf.furniture_id, rf.assignment_date
                    FROM beach_reservation_furniture rf
                    WHERE rf.assignment_date = date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

        if not row:
            pytest.skip("No reservation with furniture for today")

        response = client.post(
            '/beach/api/move-mode/unassign',
            json={
                'reservation_id': row['reservation_id'],
                'furniture_ids': [row['furniture_id']],
                'date': row['assignment_date']
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_unassign_furniture_missing_params(self, client):
        """Should return 400 when missing required parameters."""
        response = client.post(
            '/beach/api/move-mode/unassign',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode_api.py::TestMoveModeUnassignAPI -v`

Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

Create `blueprints/beach/routes/api/move_mode.py`:
```python
"""
Move mode API routes.

Handles furniture reassignment operations during move mode.
"""

from flask import request, jsonify, Response, Blueprint
from flask_login import login_required
from utils.decorators import permission_required
from models.move_mode import (
    unassign_furniture_for_date,
    assign_furniture_for_date,
    get_reservation_pool_data,
    get_furniture_preference_matches
)


def register_routes(bp: Blueprint) -> None:
    """Register move mode routes on the blueprint."""

    @bp.route('/api/move-mode/unassign', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def move_mode_unassign() -> tuple[Response, int] | Response:
        """
        Unassign furniture from a reservation for a specific date.

        Request body:
            reservation_id: int
            furniture_ids: list[int]
            date: str (YYYY-MM-DD)

        Returns:
            JSON with success status and unassigned furniture info
        """
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        reservation_id = data.get('reservation_id')
        furniture_ids = data.get('furniture_ids', [])
        target_date = data.get('date')

        if not reservation_id or not furniture_ids or not target_date:
            return jsonify({
                'success': False,
                'error': 'reservation_id, furniture_ids y date son requeridos'
            }), 400

        try:
            result = unassign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=furniture_ids,
                assignment_date=target_date
            )
            return jsonify(result), 200 if result['success'] else 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/api/move-mode/assign', methods=['POST'])
    @login_required
    @permission_required('beach.reservations.edit')
    def move_mode_assign() -> tuple[Response, int] | Response:
        """
        Assign furniture to a reservation for a specific date.

        Request body:
            reservation_id: int
            furniture_ids: list[int]
            date: str (YYYY-MM-DD)

        Returns:
            JSON with success status and assigned furniture info
        """
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Datos requeridos'}), 400

        reservation_id = data.get('reservation_id')
        furniture_ids = data.get('furniture_ids', [])
        target_date = data.get('date')

        if not reservation_id or not furniture_ids or not target_date:
            return jsonify({
                'success': False,
                'error': 'reservation_id, furniture_ids y date son requeridos'
            }), 400

        try:
            result = assign_furniture_for_date(
                reservation_id=reservation_id,
                furniture_ids=furniture_ids,
                assignment_date=target_date
            )
            return jsonify(result), 200 if result['success'] else 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/api/move-mode/reservation/<int:reservation_id>', methods=['GET'])
    @login_required
    @permission_required('beach.reservations.view')
    def move_mode_get_reservation(reservation_id: int) -> tuple[Response, int] | Response:
        """
        Get reservation data for pool panel display.

        Query params:
            date: str (YYYY-MM-DD) - target date

        Returns:
            JSON with complete reservation info for pool display
        """
        target_date = request.args.get('date')
        if not target_date:
            return jsonify({'success': False, 'error': 'date es requerido'}), 400

        try:
            result = get_reservation_pool_data(reservation_id, target_date)
            if 'error' in result:
                return jsonify({'success': False, 'error': result['error']}), 404
            return jsonify({'success': True, 'data': result}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/api/move-mode/preferences-match', methods=['GET'])
    @login_required
    @permission_required('beach.reservations.view')
    def move_mode_preferences_match() -> tuple[Response, int] | Response:
        """
        Get furniture with preference match scores.

        Query params:
            preferences: str (comma-separated preference codes)
            date: str (YYYY-MM-DD)
            zone_id: int (optional)

        Returns:
            JSON with furniture list including match scores
        """
        preferences_str = request.args.get('preferences', '')
        target_date = request.args.get('date')
        zone_id = request.args.get('zone_id', type=int)

        if not target_date:
            return jsonify({'success': False, 'error': 'date es requerido'}), 400

        preference_codes = [p.strip() for p in preferences_str.split(',') if p.strip()]

        try:
            result = get_furniture_preference_matches(
                preference_codes=preference_codes,
                target_date=target_date,
                zone_id=zone_id
            )
            return jsonify({'success': True, 'data': result}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
```

**Step 4: Register routes in blueprint**

Check current structure and add import. Add to `blueprints/beach/__init__.py` in the route registration section:
```python
from .routes.api import move_mode
move_mode.register_routes(bp)
```

**Step 5: Run test to verify it passes**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode_api.py::TestMoveModeUnassignAPI -v`

Expected: PASS

**Step 6: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add blueprints/beach/routes/api/move_mode.py blueprints/beach/__init__.py tests/test_move_mode_api.py
git commit -m "feat(api): add move mode API endpoints"
```

---

## Task 6: API - Add Remaining Endpoint Tests

**Files:**
- Modify: `tests/test_move_mode_api.py`

**Step 1: Add tests for assign and preferences endpoints**

Add to `tests/test_move_mode_api.py`:
```python
class TestMoveModeAssignAPI:
    """Tests for the assign furniture endpoint."""

    def test_assign_furniture_success(self, client, app):
        """Should assign available furniture via POST."""
        from database import get_db
        from models.move_mode import unassign_furniture_for_date

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()

                # Get a reservation with furniture
                cursor.execute("""
                    SELECT rf.reservation_id, rf.furniture_id, rf.assignment_date
                    FROM beach_reservation_furniture rf
                    WHERE rf.assignment_date = date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if not row:
                    pytest.skip("No reservation with furniture for today")

                # Find available furniture
                cursor.execute("""
                    SELECT f.id FROM beach_furniture f
                    WHERE f.id NOT IN (
                        SELECT furniture_id
                        FROM beach_reservation_furniture
                        WHERE assignment_date = ?
                    )
                    AND f.active = 1
                    LIMIT 1
                """, (row['assignment_date'],))
                available = cursor.fetchone()

            if not available:
                pytest.skip("No available furniture")

            # Unassign first
            unassign_furniture_for_date(
                row['reservation_id'],
                [row['furniture_id']],
                row['assignment_date']
            )

        response = client.post(
            '/beach/api/move-mode/assign',
            json={
                'reservation_id': row['reservation_id'],
                'furniture_ids': [available['id']],
                'date': row['assignment_date']
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestMoveModePreferencesAPI:
    """Tests for the preferences match endpoint."""

    def test_get_preferences_match(self, client):
        """Should return furniture with preference matches."""
        response = client.get(
            '/beach/api/move-mode/preferences-match?date=2026-01-15&preferences=pref_sombra'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'furniture' in data['data']


class TestMoveModeReservationAPI:
    """Tests for getting reservation pool data."""

    def test_get_reservation_pool_data(self, client, app):
        """Should return reservation data for pool display."""
        from database import get_db

        with app.app_context():
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.id, r.start_date
                    FROM beach_reservations r
                    WHERE r.start_date <= date('now') AND r.end_date >= date('now')
                    LIMIT 1
                """)
                row = cursor.fetchone()

        if not row:
            pytest.skip("No active reservation")

        response = client.get(
            f'/beach/api/move-mode/reservation/{row["id"]}?date={row["start_date"]}'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'customer_name' in data['data']
```

**Step 2: Run all API tests**

Run: `cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode && python -m pytest tests/test_move_mode_api.py -v`

Expected: PASS (all tests)

**Step 3: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add tests/test_move_mode_api.py
git commit -m "test(api): add remaining move mode API tests"
```

---

## Task 7: Frontend - Create MoveMode Controller Class

**Files:**
- Create: `static/js/map/move-mode.js`

**Step 1: Create the MoveMode class**

Create `static/js/map/move-mode.js`:
```javascript
/**
 * Move Mode Module
 *
 * Manages the move mode for reorganizing reservation furniture assignments.
 * Handles pool state, furniture selection, and API communication.
 */

import { showToast, getCSRFToken } from './utils.js';

export class MoveMode {
    constructor(options = {}) {
        this.isActive = false;
        this.currentDate = options.currentDate || new Date().toISOString().split('T')[0];
        this.pool = new Map(); // reservation_id -> pool data
        this.selectedReservationId = null;
        this.undoStack = [];
        this.maxUndoSize = 20;

        // Callbacks
        this.callbacks = {
            onActivate: options.onActivate || (() => {}),
            onDeactivate: options.onDeactivate || (() => {}),
            onPoolUpdate: options.onPoolUpdate || (() => {}),
            onSelectionChange: options.onSelectionChange || (() => {}),
            onFurnitureHighlight: options.onFurnitureHighlight || (() => {}),
            onError: options.onError || ((err) => console.error(err))
        };

        // Bind methods
        this.activate = this.activate.bind(this);
        this.deactivate = this.deactivate.bind(this);
        this.handleFurnitureClick = this.handleFurnitureClick.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
    }

    /**
     * Activate move mode
     */
    activate() {
        if (this.isActive) return;

        this.isActive = true;
        this.pool.clear();
        this.selectedReservationId = null;
        this.undoStack = [];

        // Setup keyboard listener
        document.addEventListener('keydown', this.handleKeyDown);

        this.callbacks.onActivate();
    }

    /**
     * Deactivate move mode
     * @returns {boolean} True if deactivated, false if blocked (pool not empty)
     */
    deactivate() {
        if (!this.isActive) return true;

        // Block if pool not empty
        if (this.pool.size > 0) {
            showToast('Asigna todas las reservas antes de salir', 'warning');
            return false;
        }

        this.isActive = false;
        this.selectedReservationId = null;
        this.undoStack = [];

        // Remove keyboard listener
        document.removeEventListener('keydown', this.handleKeyDown);

        this.callbacks.onDeactivate();
        return true;
    }

    /**
     * Check if can exit move mode
     */
    canExit() {
        return this.pool.size === 0;
    }

    /**
     * Handle furniture click in move mode
     * @param {number} furnitureId - The clicked furniture ID
     * @param {Object} furnitureData - Data about the furniture
     * @param {boolean} ctrlKey - Whether Ctrl was held
     */
    async handleFurnitureClick(furnitureId, furnitureData, ctrlKey = false) {
        if (!this.isActive) return;

        // If furniture is occupied, unassign it
        if (furnitureData.reservationId) {
            await this.unassignFurniture(
                furnitureData.reservationId,
                furnitureId,
                ctrlKey
            );
        }
        // If furniture is available and we have a selection, assign it
        else if (this.selectedReservationId && furnitureData.available) {
            await this.assignFurniture(
                this.selectedReservationId,
                furnitureId
            );
        }
    }

    /**
     * Unassign furniture from a reservation
     * @param {number} reservationId
     * @param {number} furnitureId
     * @param {boolean} singleOnly - If true, only unassign this furniture
     */
    async unassignFurniture(reservationId, furnitureId, singleOnly = false) {
        try {
            // Get reservation data first if not in pool
            let poolData = this.pool.get(reservationId);
            if (!poolData) {
                poolData = await this.fetchReservationData(reservationId);
            }

            // Determine which furniture to unassign
            let furnitureIds;
            if (singleOnly) {
                furnitureIds = [furnitureId];
            } else {
                // Unassign all furniture for this reservation
                furnitureIds = poolData.original_furniture.map(f => f.id);
            }

            // Show multi-day warning if applicable
            if (poolData.is_multiday) {
                showToast(
                    `Reserva de ${poolData.total_days} dias - cambios solo afectan hoy`,
                    'warning',
                    3000
                );
            }

            // API call to unassign
            const response = await fetch('/beach/api/move-mode/unassign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    reservation_id: reservationId,
                    furniture_ids: furnitureIds,
                    date: this.currentDate
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al liberar mobiliario');
            }

            // Update pool
            if (!this.pool.has(reservationId)) {
                this.pool.set(reservationId, {
                    ...poolData,
                    assignedFurnitureIds: [],
                    unassignedFurnitureIds: furnitureIds
                });
            } else {
                const existing = this.pool.get(reservationId);
                existing.unassignedFurnitureIds.push(...furnitureIds);
                existing.assignedFurnitureIds = existing.assignedFurnitureIds
                    .filter(id => !furnitureIds.includes(id));
            }

            // Add to undo stack
            this.pushUndo({
                type: 'unassign',
                reservationId,
                furnitureIds,
                date: this.currentDate
            });

            // Show toast with undo option
            const furnitureNumbers = poolData.original_furniture
                .filter(f => furnitureIds.includes(f.id))
                .map(f => f.number)
                .join(', ');
            showToast(`${furnitureNumbers} liberado - `, 'success', 3000, {
                action: 'Deshacer',
                onAction: () => this.undo()
            });

            this.callbacks.onPoolUpdate(this.getPoolArray());

        } catch (error) {
            this.callbacks.onError(error);
            showToast(error.message, 'error');
        }
    }

    /**
     * Assign furniture to selected reservation
     * @param {number} reservationId
     * @param {number} furnitureId
     */
    async assignFurniture(reservationId, furnitureId) {
        try {
            const poolData = this.pool.get(reservationId);
            if (!poolData) {
                throw new Error('Reserva no encontrada en el pool');
            }

            // API call to assign
            const response = await fetch('/beach/api/move-mode/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    reservation_id: reservationId,
                    furniture_ids: [furnitureId],
                    date: this.currentDate
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al asignar mobiliario');
            }

            // Update pool data
            poolData.assignedFurnitureIds.push(furnitureId);
            poolData.unassignedFurnitureIds = poolData.unassignedFurnitureIds
                .filter(id => id !== furnitureId);

            // Add to undo stack
            this.pushUndo({
                type: 'assign',
                reservationId,
                furnitureIds: [furnitureId],
                date: this.currentDate
            });

            // Check if fully assigned
            const totalNeeded = poolData.num_people;
            const totalAssigned = poolData.assignedFurnitureIds.length;

            if (totalAssigned >= totalNeeded) {
                // Remove from pool
                this.pool.delete(reservationId);
                this.selectedReservationId = null;

                showToast(
                    `${poolData.customer_name} asignado completamente`,
                    'success'
                );

                this.callbacks.onSelectionChange(null);
                this.callbacks.onFurnitureHighlight([]);
            } else {
                showToast(
                    `${totalAssigned} de ${totalNeeded} asignados`,
                    'info'
                );
            }

            this.callbacks.onPoolUpdate(this.getPoolArray());

        } catch (error) {
            this.callbacks.onError(error);
            showToast(error.message, 'error');
        }
    }

    /**
     * Select a reservation from the pool
     * @param {number} reservationId
     */
    async selectReservation(reservationId) {
        this.selectedReservationId = reservationId;

        const poolData = this.pool.get(reservationId);
        if (poolData) {
            // Fetch preference matches
            const preferences = poolData.preferences.map(p => p.code).join(',');
            await this.updateFurnitureHighlights(preferences);
        }

        this.callbacks.onSelectionChange(reservationId);
    }

    /**
     * Deselect current selection
     */
    deselectReservation() {
        this.selectedReservationId = null;
        this.callbacks.onSelectionChange(null);
        this.callbacks.onFurnitureHighlight([]);
    }

    /**
     * Restore a reservation to its original furniture
     * @param {number} reservationId
     */
    async restoreOriginal(reservationId) {
        const poolData = this.pool.get(reservationId);
        if (!poolData) return;

        try {
            // Assign back to original furniture
            const originalIds = poolData.original_furniture.map(f => f.id);

            const response = await fetch('/beach/api/move-mode/assign', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    reservation_id: reservationId,
                    furniture_ids: originalIds,
                    date: this.currentDate
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Error al restaurar posicion');
            }

            // Remove from pool
            this.pool.delete(reservationId);
            if (this.selectedReservationId === reservationId) {
                this.selectedReservationId = null;
                this.callbacks.onSelectionChange(null);
                this.callbacks.onFurnitureHighlight([]);
            }

            showToast('Posicion original restaurada', 'success');
            this.callbacks.onPoolUpdate(this.getPoolArray());

        } catch (error) {
            this.callbacks.onError(error);
            showToast(error.message, 'error');
        }
    }

    /**
     * Fetch reservation data from API
     */
    async fetchReservationData(reservationId) {
        const response = await fetch(
            `/beach/api/move-mode/reservation/${reservationId}?date=${this.currentDate}`
        );
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Error al obtener datos de reserva');
        }

        return result.data;
    }

    /**
     * Update furniture highlights based on preferences
     */
    async updateFurnitureHighlights(preferencesCsv) {
        try {
            const response = await fetch(
                `/beach/api/move-mode/preferences-match?date=${this.currentDate}&preferences=${preferencesCsv}`
            );
            const result = await response.json();

            if (result.success) {
                this.callbacks.onFurnitureHighlight(result.data.furniture);
            }
        } catch (error) {
            console.error('Error fetching preference matches:', error);
        }
    }

    /**
     * Push action to undo stack
     */
    pushUndo(action) {
        this.undoStack.push(action);
        if (this.undoStack.length > this.maxUndoSize) {
            this.undoStack.shift();
        }
    }

    /**
     * Undo last action
     */
    async undo() {
        if (this.undoStack.length === 0) return;

        const action = this.undoStack.pop();

        try {
            if (action.type === 'unassign') {
                // Re-assign the furniture
                await fetch('/beach/api/move-mode/assign', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        reservation_id: action.reservationId,
                        furniture_ids: action.furnitureIds,
                        date: action.date
                    })
                });

                // Update pool
                const poolData = this.pool.get(action.reservationId);
                if (poolData) {
                    poolData.assignedFurnitureIds.push(...action.furnitureIds);
                    poolData.unassignedFurnitureIds = poolData.unassignedFurnitureIds
                        .filter(id => !action.furnitureIds.includes(id));

                    // Remove from pool if fully assigned
                    if (poolData.unassignedFurnitureIds.length === 0) {
                        this.pool.delete(action.reservationId);
                    }
                }

            } else if (action.type === 'assign') {
                // Unassign the furniture
                await fetch('/beach/api/move-mode/unassign', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        reservation_id: action.reservationId,
                        furniture_ids: action.furnitureIds,
                        date: action.date
                    })
                });

                // Update pool
                const poolData = this.pool.get(action.reservationId);
                if (poolData) {
                    poolData.unassignedFurnitureIds.push(...action.furnitureIds);
                    poolData.assignedFurnitureIds = poolData.assignedFurnitureIds
                        .filter(id => !action.furnitureIds.includes(id));
                }
            }

            showToast('Accion deshecha', 'info');
            this.callbacks.onPoolUpdate(this.getPoolArray());

        } catch (error) {
            this.callbacks.onError(error);
            showToast('Error al deshacer', 'error');
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyDown(event) {
        if (!this.isActive) return;

        // Ctrl+Z for undo
        if (event.ctrlKey && event.key === 'z') {
            event.preventDefault();
            this.undo();
        }

        // Escape to exit (if pool empty)
        if (event.key === 'Escape') {
            this.deactivate();
        }
    }

    /**
     * Get pool as array for UI
     */
    getPoolArray() {
        return Array.from(this.pool.entries()).map(([id, data]) => ({
            id,
            ...data
        }));
    }

    /**
     * Set current date
     */
    setDate(date) {
        this.currentDate = date;
    }

    /**
     * Add reservation directly to pool (for entry from reservation modal)
     */
    async addToPool(reservationId) {
        if (this.pool.has(reservationId)) return;

        const poolData = await this.fetchReservationData(reservationId);
        const furnitureIds = poolData.original_furniture.map(f => f.id);

        // Unassign all furniture
        await fetch('/beach/api/move-mode/unassign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                reservation_id: reservationId,
                furniture_ids: furnitureIds,
                date: this.currentDate
            })
        });

        this.pool.set(reservationId, {
            ...poolData,
            assignedFurnitureIds: [],
            unassignedFurnitureIds: furnitureIds
        });

        // Auto-select
        this.selectReservation(reservationId);
        this.callbacks.onPoolUpdate(this.getPoolArray());
    }
}
```

**Step 2: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add static/js/map/move-mode.js
git commit -m "feat(frontend): add MoveMode controller class"
```

---

## Task 8: Frontend - Create Reservation Pool Panel Component

**Files:**
- Create: `static/js/map/move-mode-panel.js`

**Step 1: Create the panel component**

Create `static/js/map/move-mode-panel.js`:
```javascript
/**
 * Move Mode Panel Component
 *
 * Renders the reservation pool panel showing unassigned reservations.
 */

export class MoveModePanel {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.reservations = [];
        this.selectedId = null;
        this.expandedIds = new Set();

        this.callbacks = {
            onSelect: options.onSelect || (() => {}),
            onRestore: options.onRestore || (() => {}),
            onClose: options.onClose || (() => {})
        };

        this.render();
    }

    /**
     * Update reservations in the panel
     */
    update(reservations) {
        this.reservations = reservations;
        this.renderCards();
    }

    /**
     * Set selected reservation
     */
    setSelected(reservationId) {
        this.selectedId = reservationId;
        this.renderCards();
    }

    /**
     * Show the panel
     */
    show() {
        this.container.classList.remove('hidden');
        this.container.classList.add('visible');
    }

    /**
     * Hide the panel
     */
    hide() {
        this.container.classList.remove('visible');
        this.container.classList.add('hidden');
    }

    /**
     * Initial render
     */
    render() {
        this.container.innerHTML = `
            <div class="move-mode-panel-header">
                <h4>Reservas sin asignar</h4>
                <span class="move-mode-badge" id="pool-count">0</span>
                <button type="button" class="btn-icon move-mode-close" id="close-move-mode" title="Salir del modo mover">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="move-mode-panel-body" id="pool-cards">
                <div class="move-mode-empty">
                    <i class="fas fa-hand-pointer"></i>
                    <p>Haz clic en el mobiliario ocupado para liberarlo</p>
                </div>
            </div>
            <div class="move-mode-panel-footer">
                <div class="move-mode-shortcuts">
                    <small><kbd>Ctrl</kbd>+clic: liberar individual</small>
                    <small><kbd>Ctrl</kbd>+<kbd>Z</kbd>: deshacer</small>
                    <small><kbd>Esc</kbd>: salir</small>
                </div>
            </div>
        `;

        // Event listeners
        document.getElementById('close-move-mode').addEventListener('click', () => {
            this.callbacks.onClose();
        });
    }

    /**
     * Render reservation cards
     */
    renderCards() {
        const container = document.getElementById('pool-cards');
        const countBadge = document.getElementById('pool-count');

        countBadge.textContent = this.reservations.length;

        if (this.reservations.length === 0) {
            container.innerHTML = `
                <div class="move-mode-empty">
                    <i class="fas fa-hand-pointer"></i>
                    <p>Haz clic en el mobiliario ocupado para liberarlo</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.reservations.map(res => this.renderCard(res)).join('');

        // Add event listeners to cards
        this.reservations.forEach(res => {
            const card = document.getElementById(`pool-card-${res.id}`);
            const header = card.querySelector('.pool-card-header');
            const restoreBtn = card.querySelector('.btn-restore');

            header.addEventListener('click', (e) => {
                if (e.target.closest('.btn-restore')) return;

                if (this.expandedIds.has(res.id)) {
                    this.expandedIds.delete(res.id);
                } else {
                    this.expandedIds.add(res.id);
                }

                // Select on click
                this.callbacks.onSelect(res.id);
                this.renderCards();
            });

            if (restoreBtn) {
                restoreBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.callbacks.onRestore(res.id);
                });
            }
        });
    }

    /**
     * Render a single card
     */
    renderCard(reservation) {
        const isSelected = this.selectedId === reservation.id;
        const isExpanded = this.expandedIds.has(reservation.id);

        const roomDisplay = reservation.room_number
            ? `Hab. ${reservation.room_number}`
            : reservation.customer_type === 'externo' ? 'Externo' : '';

        const prefDots = this.renderPrefDots(reservation.preferences);
        const originalFurniture = reservation.original_furniture
            .map(f => f.number)
            .join(', ');

        const assignedCount = reservation.assignedFurnitureIds?.length || 0;
        const totalNeeded = reservation.num_people;
        const progressDisplay = assignedCount > 0
            ? `<span class="assign-progress">${assignedCount} de ${totalNeeded}</span>`
            : '';

        let expandedContent = '';
        if (isExpanded) {
            expandedContent = `
                <div class="pool-card-details">
                    ${reservation.preferences.length > 0 ? `
                        <div class="pool-card-prefs">
                            <strong>Preferencias:</strong>
                            ${reservation.preferences.map(p => `
                                <span class="pref-tag">${p.icon || ''} ${p.name}</span>
                            `).join('')}
                        </div>
                    ` : ''}
                    ${reservation.notes ? `
                        <div class="pool-card-notes">
                            <strong>Notas:</strong> ${reservation.notes}
                        </div>
                    ` : ''}
                    ${reservation.is_multiday ? `
                        <div class="pool-card-days">
                            <strong>Dias de reserva:</strong>
                            ${Object.entries(reservation.day_assignments || {}).map(([date, furniture]) => `
                                <div class="day-row ${date === reservation.target_date ? 'today' : ''}">
                                    ${this.formatDate(date)}: ${furniture}
                                    ${date === reservation.target_date ? '(hoy)' : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-secondary btn-restore">
                        <i class="fas fa-undo"></i> Restaurar posicion original
                    </button>
                </div>
            `;
        }

        return `
            <div class="pool-card ${isSelected ? 'selected' : ''} ${isExpanded ? 'expanded' : ''}"
                 id="pool-card-${reservation.id}">
                <div class="pool-card-header">
                    <div class="pool-card-title">
                        <i class="fas fa-bed"></i>
                        <span class="room-number">${roomDisplay}</span>
                        <span class="customer-name">- ${reservation.customer_name}</span>
                        ${reservation.is_multiday ? `
                            <span class="multiday-badge" title="${reservation.total_days} dias">
                                <i class="far fa-calendar-alt"></i>${reservation.total_days}
                            </span>
                        ` : ''}
                    </div>
                    <i class="fas fa-chevron-${isExpanded ? 'up' : 'down'} expand-icon"></i>
                </div>
                <div class="pool-card-summary">
                    <span class="people-count">
                        <i class="fas fa-users"></i> ${reservation.num_people} personas
                    </span>
                    ${prefDots}
                    ${progressDisplay}
                </div>
                <div class="pool-card-origin">
                    <i class="fas fa-map-marker-alt"></i> Era: ${originalFurniture}
                </div>
                ${expandedContent}
            </div>
        `;
    }

    /**
     * Render preference indicator dots
     */
    renderPrefDots(preferences) {
        const count = preferences.length;
        if (count === 0) return '';

        const filled = Math.min(count, 3);
        const dots = [];
        for (let i = 0; i < 3; i++) {
            dots.push(`<span class="pref-dot ${i < filled ? 'filled' : ''}"></span>`);
        }

        return `<span class="pref-dots" title="${count} preferencias">${dots.join('')}</span>`;
    }

    /**
     * Format date for display
     */
    formatDate(dateStr) {
        const date = new Date(dateStr + 'T00:00:00');
        return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
    }
}
```

**Step 2: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add static/js/map/move-mode-panel.js
git commit -m "feat(frontend): add MoveModePanel component"
```

---

## Task 9: Frontend - Create Move Mode CSS

**Files:**
- Create: `static/css/move-mode.css`

**Step 1: Create the CSS file**

Note: Use `/frontend-design` skill when implementing to ensure compliance with design system.

Create `static/css/move-mode.css`:
```css
/* =============================================================================
   MOVE MODE STYLES
   ============================================================================= */

/* =============================================================================
   MOVE MODE INDICATOR
   ============================================================================= */

.move-mode-active {
    position: relative;
}

.move-mode-active::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border: 3px solid #1A3A5C;
    pointer-events: none;
    z-index: 100;
}

.move-mode-header-bar {
    position: fixed;
    top: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: #1A3A5C;
    color: white;
    padding: 8px 24px;
    border-radius: 0 0 8px 8px;
    font-weight: 500;
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.move-mode-header-bar i {
    color: #D4AF37;
}

/* =============================================================================
   POOL PANEL
   ============================================================================= */

.move-mode-panel {
    position: fixed;
    top: 120px;
    right: 20px;
    width: 340px;
    max-height: calc(100vh - 160px);
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    z-index: 999;
    display: flex;
    flex-direction: column;
    transition: transform 0.3s ease, opacity 0.3s ease;
}

.move-mode-panel.hidden {
    transform: translateX(400px);
    opacity: 0;
    pointer-events: none;
}

.move-mode-panel.visible {
    transform: translateX(0);
    opacity: 1;
}

.move-mode-panel-header {
    display: flex;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #F5E6D3;
    background: #F5E6D3;
    border-radius: 12px 12px 0 0;
}

.move-mode-panel-header h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #1A3A5C;
    flex: 1;
}

.move-mode-badge {
    background: #D4AF37;
    color: white;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    margin-right: 12px;
}

.move-mode-close {
    background: none;
    border: none;
    color: #1A3A5C;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.move-mode-close:hover {
    background: rgba(26, 58, 92, 0.1);
}

.move-mode-panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
}

.move-mode-empty {
    text-align: center;
    padding: 40px 20px;
    color: #6B7280;
}

.move-mode-empty i {
    font-size: 48px;
    color: #D4AF37;
    margin-bottom: 16px;
}

.move-mode-empty p {
    margin: 0;
    font-size: 14px;
}

.move-mode-panel-footer {
    padding: 12px 16px;
    border-top: 1px solid #F5E6D3;
    background: #FAFAFA;
    border-radius: 0 0 12px 12px;
}

.move-mode-shortcuts {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.move-mode-shortcuts small {
    font-size: 11px;
    color: #6B7280;
}

.move-mode-shortcuts kbd {
    background: #E5E7EB;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 10px;
}

/* =============================================================================
   POOL CARDS
   ============================================================================= */

.pool-card {
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 8px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.pool-card:hover {
    border-color: #D4AF37;
    box-shadow: 0 2px 8px rgba(212, 175, 55, 0.15);
}

.pool-card.selected {
    border-color: #D4AF37;
    background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2);
}

.pool-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    border-bottom: 1px solid #F3F4F6;
}

.pool-card-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
}

.pool-card-title i {
    color: #1A3A5C;
}

.pool-card-title .room-number {
    font-weight: 600;
    color: #1A3A5C;
}

.pool-card-title .customer-name {
    color: #374151;
}

.multiday-badge {
    background: #E5A33D;
    color: white;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 3px;
    margin-left: 6px;
}

.expand-icon {
    color: #9CA3AF;
    font-size: 12px;
}

.pool-card-summary {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    font-size: 13px;
    color: #6B7280;
}

.people-count {
    display: flex;
    align-items: center;
    gap: 4px;
}

.pref-dots {
    display: flex;
    gap: 3px;
}

.pref-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1px solid #D4AF37;
    background: transparent;
}

.pref-dot.filled {
    background: #D4AF37;
}

.assign-progress {
    margin-left: auto;
    background: #4A7C59;
    color: white;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
}

.pool-card-origin {
    padding: 8px 12px;
    font-size: 12px;
    color: #9CA3AF;
    border-top: 1px dashed #E5E7EB;
}

.pool-card-origin i {
    margin-right: 4px;
}

/* =============================================================================
   EXPANDED CARD DETAILS
   ============================================================================= */

.pool-card-details {
    padding: 12px;
    background: #F9FAFB;
    border-top: 1px solid #E5E7EB;
    font-size: 13px;
}

.pool-card-prefs {
    margin-bottom: 12px;
}

.pool-card-prefs strong {
    display: block;
    margin-bottom: 6px;
    color: #374151;
}

.pref-tag {
    display: inline-block;
    background: #FEF3C7;
    color: #92400E;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-right: 6px;
    margin-bottom: 4px;
}

.pool-card-notes {
    margin-bottom: 12px;
    color: #6B7280;
}

.pool-card-notes strong {
    color: #374151;
}

.pool-card-days {
    margin-bottom: 12px;
}

.pool-card-days strong {
    display: block;
    margin-bottom: 6px;
    color: #374151;
}

.day-row {
    padding: 4px 8px;
    font-size: 12px;
    color: #6B7280;
    border-left: 2px solid #E5E7EB;
    margin-left: 4px;
}

.day-row.today {
    border-left-color: #D4AF37;
    background: #FFFBEB;
    font-weight: 500;
}

.btn-restore {
    width: 100%;
    margin-top: 8px;
}

/* =============================================================================
   FURNITURE HIGHLIGHTING
   ============================================================================= */

.furniture-highlight-full {
    filter: drop-shadow(0 0 8px #D4AF37) drop-shadow(0 0 16px rgba(212, 175, 55, 0.4));
}

.furniture-highlight-partial {
    filter: drop-shadow(0 0 4px rgba(212, 175, 55, 0.6));
}

.furniture-highlight-none {
    opacity: 0.4;
}

/* =============================================================================
   PREFERENCE LEGEND
   ============================================================================= */

.preference-legend {
    position: fixed;
    bottom: 100px;
    right: 380px;
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 998;
    max-width: 200px;
}

.preference-legend h5 {
    margin: 0 0 8px 0;
    font-size: 13px;
    color: #374151;
}

.preference-legend ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.preference-legend li {
    font-size: 12px;
    color: #6B7280;
    padding: 3px 0;
}

/* =============================================================================
   TOOLBAR BUTTON
   ============================================================================= */

.btn-move-mode {
    background: linear-gradient(135deg, #1A3A5C 0%, #2D5A87 100%);
    color: white;
    border: none;
}

.btn-move-mode:hover {
    background: linear-gradient(135deg, #2D5A87 0%, #1A3A5C 100%);
    color: white;
}

.btn-move-mode.active {
    background: linear-gradient(135deg, #D4AF37 0%, #B8972F 100%);
    box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.3);
}

/* =============================================================================
   TOAST WITH ACTION
   ============================================================================= */

.toast-action {
    margin-left: 12px;
    color: #D4AF37;
    text-decoration: underline;
    cursor: pointer;
    font-weight: 500;
}

.toast-action:hover {
    color: #B8972F;
}
```

**Step 2: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add static/css/move-mode.css
git commit -m "feat(frontend): add move mode CSS styles"
```

---

## Task 10: Frontend - Integrate Move Mode with Map

**Files:**
- Modify: `static/js/map/BeachMap.js`
- Modify: `templates/beach/map.html`

**Step 1: Add imports and initialization to BeachMap.js**

Find the imports section in `static/js/map/BeachMap.js` and add:
```javascript
import { MoveMode } from './move-mode.js';
import { MoveModePanel } from './move-mode-panel.js';
```

Find the constructor and add move mode initialization:
```javascript
// In constructor, add:
this.moveMode = null;
this.moveModePanel = null;
```

Add method to initialize move mode:
```javascript
/**
 * Initialize move mode functionality
 */
initMoveMode() {
    this.moveMode = new MoveMode({
        currentDate: this.currentDate,
        onActivate: () => {
            document.body.classList.add('move-mode-active');
            this.showMoveModeHeader();
            this.moveModePanel.show();
            this.updateToolbarButton(true);
        },
        onDeactivate: () => {
            document.body.classList.remove('move-mode-active');
            this.hideMoveModeHeader();
            this.moveModePanel.hide();
            this.updateToolbarButton(false);
            this.clearFurnitureHighlights();
        },
        onPoolUpdate: (pool) => {
            this.moveModePanel.update(pool);
            this.refreshMap();
        },
        onSelectionChange: (reservationId) => {
            this.moveModePanel.setSelected(reservationId);
        },
        onFurnitureHighlight: (furniture) => {
            this.applyFurnitureHighlights(furniture);
        }
    });

    this.moveModePanel = new MoveModePanel('move-mode-panel-container', {
        onSelect: (id) => this.moveMode.selectReservation(id),
        onRestore: (id) => this.moveMode.restoreOriginal(id),
        onClose: () => this.toggleMoveMode()
    });
}

/**
 * Toggle move mode on/off
 */
toggleMoveMode() {
    if (this.moveMode.isActive) {
        this.moveMode.deactivate();
    } else {
        this.moveMode.activate();
    }
}

/**
 * Show move mode header bar
 */
showMoveModeHeader() {
    let header = document.getElementById('move-mode-header');
    if (!header) {
        header = document.createElement('div');
        header.id = 'move-mode-header';
        header.className = 'move-mode-header-bar';
        header.innerHTML = '<i class="fas fa-arrows-alt"></i> Modo Mover Activo';
        document.body.appendChild(header);
    }
    header.style.display = 'flex';
}

/**
 * Hide move mode header bar
 */
hideMoveModeHeader() {
    const header = document.getElementById('move-mode-header');
    if (header) {
        header.style.display = 'none';
    }
}

/**
 * Update toolbar button state
 */
updateToolbarButton(active) {
    const btn = document.getElementById('btn-move-mode');
    if (btn) {
        btn.classList.toggle('active', active);
        btn.innerHTML = active
            ? '<i class="fas fa-times"></i> Salir Modo Mover'
            : '<i class="fas fa-arrows-alt"></i> Modo Mover';
    }
}

/**
 * Apply preference-based highlights to furniture
 */
applyFurnitureHighlights(furniture) {
    // Clear existing highlights
    this.clearFurnitureHighlights();

    furniture.forEach(f => {
        const element = document.querySelector(`[data-furniture-id="${f.id}"]`);
        if (!element) return;

        if (!f.available) {
            // Occupied - no special highlight
            return;
        }

        if (f.match_score >= 0.8) {
            element.classList.add('furniture-highlight-full');
        } else if (f.match_score >= 0.3) {
            element.classList.add('furniture-highlight-partial');
        } else {
            element.classList.add('furniture-highlight-none');
        }
    });
}

/**
 * Clear all furniture highlights
 */
clearFurnitureHighlights() {
    document.querySelectorAll('.furniture-highlight-full, .furniture-highlight-partial, .furniture-highlight-none')
        .forEach(el => {
            el.classList.remove('furniture-highlight-full', 'furniture-highlight-partial', 'furniture-highlight-none');
        });
}

/**
 * Handle furniture click - check if move mode should intercept
 */
handleFurnitureClickForMoveMode(furnitureId, furnitureData, event) {
    if (this.moveMode && this.moveMode.isActive) {
        this.moveMode.handleFurnitureClick(furnitureId, furnitureData, event.ctrlKey);
        return true; // Handled
    }
    return false; // Not handled, proceed with normal click
}

/**
 * Enter move mode from reservation modal
 */
enterMoveModeWithReservation(reservationId) {
    if (!this.moveMode.isActive) {
        this.moveMode.activate();
    }
    this.moveMode.addToPool(reservationId);
}
```

**Step 2: Update map template**

Add to `templates/beach/map.html` in the extra_css block:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/move-mode.css') }}">
```

Add the panel container and toolbar button in the template body:
```html
<!-- Move Mode Panel Container -->
<div id="move-mode-panel-container" class="move-mode-panel hidden"></div>

<!-- In the toolbar section, add the button -->
<button type="button" class="btn btn-move-mode" id="btn-move-mode">
    <i class="fas fa-arrows-alt"></i> Modo Mover
</button>
```

Add initialization in the script section:
```javascript
// After BeachMap initialization
beachMap.initMoveMode();

// Toolbar button click handler
document.getElementById('btn-move-mode').addEventListener('click', () => {
    beachMap.toggleMoveMode();
});
```

**Step 3: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add static/js/map/BeachMap.js templates/beach/map.html
git commit -m "feat(frontend): integrate move mode with map"
```

---

## Task 11: Add Reservation Modal Entry Point

**Files:**
- Modify: `templates/beach/_reservation_panel.html` or equivalent modal template

**Step 1: Add "Reorganizar en mapa" button**

Find the furniture assignment section in the reservation edit modal and add:
```html
<!-- In the furniture assignment section -->
<div class="furniture-actions mt-2">
    <button type="button" class="btn btn-outline-secondary btn-sm"
            id="btn-reorganize-map"
            onclick="enterMoveModeFromModal({{ reservation.id }})">
        <i class="fas fa-arrows-alt"></i> Reorganizar en mapa
    </button>
</div>
```

Add the JavaScript function:
```javascript
function enterMoveModeFromModal(reservationId) {
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('reservationModal'));
    if (modal) {
        modal.hide();
    }

    // Enter move mode with this reservation
    if (window.beachMap) {
        beachMap.enterMoveModeWithReservation(reservationId);
    }
}
```

**Step 2: Commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add templates/beach/_reservation_panel.html
git commit -m "feat(frontend): add move mode entry from reservation modal"
```

---

## Task 12: Run Full Test Suite

**Step 1: Run all tests to ensure nothing is broken**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
python -m pytest -v
```

Expected: All tests pass including new move mode tests

**Step 2: Manual testing checklist**

- [ ] Click "Modo Mover" button - panel appears, header shows
- [ ] Click occupied furniture - reservation goes to pool
- [ ] Ctrl+click occupied furniture - only that furniture unassigns
- [ ] Click reservation in pool - it becomes selected, furniture highlights
- [ ] Click available furniture - assigns to selected reservation
- [ ] Multi-day reservation shows warning toast
- [ ] Ctrl+Z undoes last action
- [ ] Escape exits (if pool empty)
- [ ] Cannot exit with reservations in pool
- [ ] "Restaurar posicion original" works
- [ ] "Reorganizar en mapa" from modal works

**Step 3: Final commit**

```bash
cd C:/Users/catia/programas/PuroBeach/PuroBeach/.worktrees/move-mode
git add -A
git commit -m "feat: complete move mode feature implementation"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Model | `unassign_furniture_for_date` function |
| 2 | Model | `assign_furniture_for_date` function |
| 3 | Model | `get_reservation_pool_data` function |
| 4 | Model | `get_furniture_preference_matches` function |
| 5 | API | Move mode routes file with all endpoints |
| 6 | API | Additional endpoint tests |
| 7 | Frontend | MoveMode controller class |
| 8 | Frontend | MoveModePanel component |
| 9 | Frontend | Move mode CSS styles |
| 10 | Frontend | Integration with BeachMap |
| 11 | Frontend | Reservation modal entry point |
| 12 | Testing | Full test suite verification |

**Total estimated tasks:** 12 major tasks with TDD steps

**Key files created:**
- `models/move_mode.py`
- `blueprints/beach/routes/api/move_mode.py`
- `static/js/map/move-mode.js`
- `static/js/map/move-mode-panel.js`
- `static/css/move-mode.css`
- `tests/test_move_mode.py`
- `tests/test_move_mode_api.py`
