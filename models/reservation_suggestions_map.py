"""
Occupancy mapping and spatial analysis for furniture suggestions.

Builds spatial maps of furniture grouped by rows, tracking availability
and providing customer history-based preferences.

Phase 6B - Module 3A (Refactored from reservation_suggestions.py)
"""

from database import get_db
from .reservation_state import get_active_releasing_states


# =============================================================================
# CONSTANTS
# =============================================================================

# Row grouping tolerance in pixels (furniture within this Y distance are same row)
ROW_TOLERANCE_PX = 30


# =============================================================================
# OCCUPANCY MAP BUILDER
# =============================================================================

def build_furniture_occupancy_map(date: str, zone_id: int = None) -> dict:
    """
    Build spatial occupancy map grouping furniture by rows.

    Uses position_y with ±ROW_TOLERANCE_PX tolerance for row grouping.

    Args:
        date: Date to check (YYYY-MM-DD)
        zone_id: Filter by zone (optional)

    Returns:
        dict: {
            'date': str,
            'zone_id': int or None,
            'occupied_ids': [int],
            'available_ids': [int],
            'furniture': {
                furniture_id: {
                    'id': int,
                    'number': str,
                    'type': str,
                    'capacity': int,
                    'x': float,
                    'y': float,
                    'row': int,
                    'available': bool,
                    'reservation_id': int or None
                }
            },
            'rows': {
                row_index: [furniture_ids sorted by x position]
            },
            'row_count': int
        }
    """
    with get_db() as conn:
        cursor = conn.cursor()

        releasing_states = get_active_releasing_states()

        # Get all furniture
        furniture_query = '''
            SELECT f.id, f.number, f.furniture_type, f.capacity,
                   f.position_x, f.position_y, f.zone_id,
                   z.name as zone_name
            FROM beach_furniture f
            LEFT JOIN beach_zones z ON f.zone_id = z.id
            WHERE f.active = 1
        '''
        params = []

        if zone_id:
            furniture_query += ' AND f.zone_id = ?'
            params.append(zone_id)

        furniture_query += ' ORDER BY f.position_y, f.position_x'

        cursor.execute(furniture_query, params)
        all_furniture = cursor.fetchall()

        if not all_furniture:
            return {
                'date': date,
                'zone_id': zone_id,
                'occupied_ids': [],
                'available_ids': [],
                'furniture': {},
                'rows': {},
                'row_count': 0
            }

        # Get occupied furniture for the date
        occupied_query = '''
            SELECT rf.furniture_id, r.id as reservation_id
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            WHERE rf.assignment_date = ?
        '''
        occ_params = [date]

        if releasing_states:
            placeholders = ','.join('?' * len(releasing_states))
            occupied_query += f' AND r.current_state NOT IN ({placeholders})'
            occ_params.extend(releasing_states)

        cursor.execute(occupied_query, occ_params)
        occupied_map = {row['furniture_id']: row['reservation_id'] for row in cursor.fetchall()}

        # Group furniture by rows (based on Y position)
        furniture_dict = {}
        y_positions = []

        for f in all_furniture:
            furn_id = f['id']
            y = f['position_y'] or 0

            furniture_dict[furn_id] = {
                'id': furn_id,
                'number': f['number'],
                'type': f['furniture_type'],
                'capacity': f['capacity'],
                'x': f['position_x'] or 0,
                'y': y,
                'zone_id': f['zone_id'],
                'available': furn_id not in occupied_map,
                'reservation_id': occupied_map.get(furn_id)
            }
            y_positions.append((furn_id, y))

        # Assign rows based on Y clustering
        rows = {}
        row_assignments = {}

        if y_positions:
            # Sort by Y position
            y_positions.sort(key=lambda x: x[1])

            current_row = 0
            current_y = y_positions[0][1]
            rows[current_row] = []

            for furn_id, y in y_positions:
                if abs(y - current_y) > ROW_TOLERANCE_PX:
                    # New row
                    current_row += 1
                    current_y = y
                    rows[current_row] = []

                rows[current_row].append(furn_id)
                row_assignments[furn_id] = current_row
                furniture_dict[furn_id]['row'] = current_row

            # Sort each row by X position
            for row_idx in rows:
                rows[row_idx].sort(key=lambda fid: furniture_dict[fid]['x'])

        occupied_ids = list(occupied_map.keys())
        available_ids = [fid for fid in furniture_dict if fid not in occupied_map]

        return {
            'date': date,
            'zone_id': zone_id,
            'occupied_ids': occupied_ids,
            'available_ids': available_ids,
            'furniture': furniture_dict,
            'rows': rows,
            'row_count': len(rows)
        }


# =============================================================================
# CUSTOMER HISTORY ANALYSIS
# =============================================================================

def get_customer_preferred_furniture(customer_id: int, limit: int = 5) -> list:
    """
    Get furniture the customer has used most frequently.

    Args:
        customer_id: Customer ID
        limit: Maximum items to return

    Returns:
        list: [{'furniture_id': int, 'number': str, 'usage_count': int}]
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get releasing states dynamically from database
        releasing_states = get_active_releasing_states()
        if not releasing_states:
            releasing_states = ['Cancelada', 'No-Show', 'Liberada']  # Fallback

        placeholders = ','.join('?' * len(releasing_states))
        query = f'''
            SELECT f.id, f.number, COUNT(*) as usage_count
            FROM beach_reservation_furniture rf
            JOIN beach_reservations r ON rf.reservation_id = r.id
            JOIN beach_furniture f ON rf.furniture_id = f.id
            WHERE r.customer_id = ?
              AND r.current_state NOT IN ({placeholders})
            GROUP BY f.id
            ORDER BY usage_count DESC
            LIMIT ?
        '''
        cursor.execute(query, [customer_id] + releasing_states + [limit])

        return [dict(row) for row in cursor.fetchall()]
