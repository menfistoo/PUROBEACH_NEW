"""
Smart furniture suggestion algorithm.
Recommends optimal furniture based on preferences, contiguity, and capacity.

Scoring weights: 40% contiguity + 35% preferences + 25% capacity

Phase 6B - Module 3
"""

from database import get_db
from .reservation_state import get_active_releasing_states


# =============================================================================
# CONSTANTS
# =============================================================================

SUGGESTION_WEIGHTS = {
    'contiguity': 0.40,
    'preferences': 0.35,
    'capacity': 0.25
}

# Preference code to furniture feature mapping
PREFERENCE_TO_FEATURE = {
    'pref_primera_linea': ['first_line', 'premium'],
    'pref_sombra': ['shaded', 'umbrella'],
    'pref_sol': ['full_sun'],
    'pref_tranquilo': ['quiet_zone'],
    'pref_cerca_bar': ['near_bar'],
    'pref_cerca_piscina': ['near_pool'],
    'pref_accesible': ['accessible'],
    'pref_vista_mar': ['sea_view'],
}

# Row grouping tolerance in pixels (furniture within this Y distance are same row)
ROW_TOLERANCE_PX = 30


# =============================================================================
# OCCUPANCY MAP
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
    db = get_db()
    cursor = db.cursor()

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
# CONTIGUITY VALIDATION
# =============================================================================

def validate_cluster_contiguity(furniture_ids: list, occupancy_map: dict) -> dict:
    """
    Validate if selected furniture is contiguous (no occupied gaps between).

    Contiguity rules:
    - Within same row: No occupied furniture between selected ones
    - Across rows: More tolerant (adjacent rows OK)

    Args:
        furniture_ids: List of selected furniture IDs
        occupancy_map: Result from build_furniture_occupancy_map()

    Returns:
        dict: {
            'is_contiguous': bool,
            'gap_count': int,
            'blocking_furniture': [
                {'id': int, 'number': str, 'row': int}
            ],
            'contiguity_score': float,  # 1.0 = perfect, -0.3 per gap
            'rows_used': [int],
            'message': str
        }
    """
    if not furniture_ids:
        return {
            'is_contiguous': True,
            'gap_count': 0,
            'blocking_furniture': [],
            'contiguity_score': 1.0,
            'rows_used': [],
            'message': 'Sin mobiliario seleccionado'
        }

    furniture_dict = occupancy_map.get('furniture', {})
    rows = occupancy_map.get('rows', {})

    # Get rows used by selected furniture
    selected_set = set(furniture_ids)
    rows_used = set()

    for fid in furniture_ids:
        if fid in furniture_dict:
            rows_used.add(furniture_dict[fid].get('row', 0))

    rows_used = sorted(rows_used)

    # Check for gaps within each row
    blocking = []

    for row_idx in rows_used:
        row_furniture = rows.get(row_idx, [])
        if not row_furniture:
            continue

        # Find selected furniture positions in this row
        selected_in_row = [fid for fid in row_furniture if fid in selected_set]

        if len(selected_in_row) < 2:
            continue

        # Get index range of selected furniture
        indices = [row_furniture.index(fid) for fid in selected_in_row]
        min_idx = min(indices)
        max_idx = max(indices)

        # Check furniture between min and max for gaps
        for i in range(min_idx, max_idx + 1):
            fid = row_furniture[i]
            if fid not in selected_set:
                furn = furniture_dict.get(fid, {})
                # Check if this is an occupied gap
                if not furn.get('available', True):
                    blocking.append({
                        'id': fid,
                        'number': furn.get('number', '?'),
                        'row': row_idx
                    })

    gap_count = len(blocking)
    contiguity_score = max(0.0, 1.0 - (gap_count * 0.3))
    is_contiguous = gap_count == 0

    if is_contiguous:
        message = 'Seleccion contigua - sin espacios ocupados entre muebles'
    elif gap_count == 1:
        message = f'1 mueble ocupado entre la seleccion ({blocking[0]["number"]})'
    else:
        numbers = ', '.join(b['number'] for b in blocking[:3])
        message = f'{gap_count} muebles ocupados entre la seleccion ({numbers}...)'

    return {
        'is_contiguous': is_contiguous,
        'gap_count': gap_count,
        'blocking_furniture': blocking,
        'contiguity_score': contiguity_score,
        'rows_used': rows_used,
        'message': message
    }


# =============================================================================
# PREFERENCE MATCHING
# =============================================================================

def get_furniture_features(furniture_id: int) -> list:
    """
    Get features/tags associated with furniture.

    Checks furniture tags and zone features.

    Args:
        furniture_id: Furniture ID

    Returns:
        list: Feature codes
    """
    db = get_db()
    cursor = db.cursor()

    features = []

    # Get furniture zone and type features
    cursor.execute('''
        SELECT f.furniture_type, z.name as zone_name,
               f.position_y, f.zone_id
        FROM beach_furniture f
        LEFT JOIN beach_zones z ON f.zone_id = z.id
        WHERE f.id = ?
    ''', (furniture_id,))

    row = cursor.fetchone()
    if row:
        # Infer features from zone name
        zone_name = (row['zone_name'] or '').lower()

        if 'primera' in zone_name or 'first' in zone_name:
            features.append('first_line')
        if 'premium' in zone_name or 'vip' in zone_name:
            features.append('premium')
        if 'sombra' in zone_name or 'shade' in zone_name:
            features.append('shaded')
        if 'sol' in zone_name or 'sun' in zone_name:
            features.append('full_sun')
        if 'tranquil' in zone_name or 'quiet' in zone_name:
            features.append('quiet_zone')
        if 'bar' in zone_name:
            features.append('near_bar')
        if 'piscina' in zone_name or 'pool' in zone_name:
            features.append('near_pool')

        # Check if first row (low Y position = near sea)
        if row['position_y'] and row['position_y'] < 100:
            features.append('sea_view')
            features.append('first_line')

    return features


def score_preference_match(furniture_id: int, preferences: list) -> dict:
    """
    Calculate preference match score for furniture.

    Args:
        furniture_id: Furniture ID
        preferences: List of preference codes

    Returns:
        dict: {
            'score': float (0.0 - 1.0),
            'matched': [str],
            'unmatched': [str]
        }
    """
    if not preferences:
        return {'score': 1.0, 'matched': [], 'unmatched': []}

    features = get_furniture_features(furniture_id)
    matched = []
    unmatched = []

    for pref in preferences:
        required_features = PREFERENCE_TO_FEATURE.get(pref, [])
        if any(f in features for f in required_features):
            matched.append(pref)
        else:
            unmatched.append(pref)

    score = len(matched) / len(preferences) if preferences else 1.0

    return {
        'score': score,
        'matched': matched,
        'unmatched': unmatched
    }


# =============================================================================
# CAPACITY SCORING
# =============================================================================

def score_capacity_match(furniture_capacity: int, num_people: int) -> float:
    """
    Calculate capacity match score.

    Perfect match = 1.0
    Overcapacity penalty: -0.1 per extra seat
    Undercapacity: 0.0 (invalid)

    Args:
        furniture_capacity: Total capacity of furniture
        num_people: Number of people

    Returns:
        float: Score (0.0 - 1.0)
    """
    if furniture_capacity < num_people:
        return 0.0  # Can't fit

    if furniture_capacity == num_people:
        return 1.0  # Perfect match

    # Overcapacity penalty
    extra = furniture_capacity - num_people
    return max(0.5, 1.0 - (extra * 0.1))


# =============================================================================
# MAIN SUGGESTION ALGORITHM
# =============================================================================

def suggest_furniture_for_reservation(
    dates: list,
    num_people: int,
    preferences_csv: str = '',
    customer_id: int = None,
    zone_id: int = None,
    limit: int = 5
) -> dict:
    """
    Suggest optimal furniture combinations based on preferences and contiguity.

    Scoring: 40% contiguity + 35% preferences + 25% capacity

    Args:
        dates: List of dates (checks availability across all)
        num_people: Number of people to seat
        preferences_csv: Comma-separated preference codes
        customer_id: Customer ID (for history-based suggestions)
        zone_id: Filter by zone
        limit: Maximum suggestions to return

    Returns:
        dict: {
            'success': bool,
            'strategy': 'preference_based' | 'capacity_based' | 'no_availability',
            'suggestions': [
                {
                    'furniture_ids': [int],
                    'furniture_numbers': [str],
                    'total_capacity': int,
                    'total_score': float,
                    'contiguity_score': float,
                    'preference_score': float,
                    'capacity_score': float,
                    'preference_matches': [str],
                    'available_all_dates': bool,
                    'zone_name': str
                }
            ],
            'total_available': int,
            'message': str
        }
    """
    if not dates:
        return {
            'success': False,
            'strategy': 'no_availability',
            'suggestions': [],
            'total_available': 0,
            'message': 'Se requiere al menos una fecha'
        }

    preferences = [p.strip() for p in preferences_csv.split(',') if p.strip()]

    # Build occupancy map for first date (primary)
    primary_date = dates[0]
    occupancy_map = build_furniture_occupancy_map(primary_date, zone_id)

    available_ids = occupancy_map.get('available_ids', [])
    furniture_dict = occupancy_map.get('furniture', {})

    if not available_ids:
        return {
            'success': False,
            'strategy': 'no_availability',
            'suggestions': [],
            'total_available': 0,
            'message': 'No hay mobiliario disponible para esta fecha'
        }

    # Check availability across all dates
    if len(dates) > 1:
        for date in dates[1:]:
            other_map = build_furniture_occupancy_map(date, zone_id)
            other_available = set(other_map.get('available_ids', []))
            available_ids = [fid for fid in available_ids if fid in other_available]

    if not available_ids:
        return {
            'success': False,
            'strategy': 'no_availability',
            'suggestions': [],
            'total_available': 0,
            'message': 'No hay mobiliario disponible para todas las fechas'
        }

    # Score individual furniture
    scored_furniture = []
    for fid in available_ids:
        furn = furniture_dict.get(fid, {})

        # Preference score
        pref_result = score_preference_match(fid, preferences)

        scored_furniture.append({
            'id': fid,
            'number': furn.get('number', '?'),
            'capacity': furn.get('capacity', 2),
            'row': furn.get('row', 0),
            'x': furn.get('x', 0),
            'zone_id': furn.get('zone_id'),
            'preference_score': pref_result['score'],
            'matched_prefs': pref_result['matched']
        })

    # Sort by preference score, then by row/x for grouping
    scored_furniture.sort(key=lambda f: (-f['preference_score'], f['row'], f['x']))

    # Generate furniture combinations
    suggestions = []

    # Strategy 1: Single furniture that fits everyone
    for furn in scored_furniture:
        if furn['capacity'] >= num_people:
            cap_score = score_capacity_match(furn['capacity'], num_people)
            total_score = (
                SUGGESTION_WEIGHTS['contiguity'] * 1.0 +  # Single = perfect contiguity
                SUGGESTION_WEIGHTS['preferences'] * furn['preference_score'] +
                SUGGESTION_WEIGHTS['capacity'] * cap_score
            )

            suggestions.append({
                'furniture_ids': [furn['id']],
                'furniture_numbers': [furn['number']],
                'total_capacity': furn['capacity'],
                'total_score': round(total_score, 3),
                'contiguity_score': 1.0,
                'preference_score': round(furn['preference_score'], 3),
                'capacity_score': round(cap_score, 3),
                'preference_matches': furn['matched_prefs'],
                'available_all_dates': True,
                'zone_id': furn['zone_id']
            })

    # Strategy 2: Pairs/groups of adjacent furniture
    rows = occupancy_map.get('rows', {})

    for row_idx, row_furniture in rows.items():
        available_in_row = [fid for fid in row_furniture if fid in available_ids]

        if len(available_in_row) < 2:
            continue

        # Try consecutive pairs
        for i in range(len(available_in_row) - 1):
            pair = available_in_row[i:i+2]

            # Check if truly adjacent (no occupied between)
            contiguity = validate_cluster_contiguity(pair, occupancy_map)

            if contiguity['is_contiguous']:
                total_cap = sum(furniture_dict[fid]['capacity'] for fid in pair)

                if total_cap >= num_people:
                    # Average preference score
                    avg_pref = sum(
                        next((f['preference_score'] for f in scored_furniture if f['id'] == fid), 0)
                        for fid in pair
                    ) / len(pair)

                    cap_score = score_capacity_match(total_cap, num_people)

                    total_score = (
                        SUGGESTION_WEIGHTS['contiguity'] * contiguity['contiguity_score'] +
                        SUGGESTION_WEIGHTS['preferences'] * avg_pref +
                        SUGGESTION_WEIGHTS['capacity'] * cap_score
                    )

                    matched_prefs = []
                    for fid in pair:
                        for f in scored_furniture:
                            if f['id'] == fid:
                                matched_prefs.extend(f['matched_prefs'])
                                break

                    suggestions.append({
                        'furniture_ids': pair,
                        'furniture_numbers': [furniture_dict[fid]['number'] for fid in pair],
                        'total_capacity': total_cap,
                        'total_score': round(total_score, 3),
                        'contiguity_score': round(contiguity['contiguity_score'], 3),
                        'preference_score': round(avg_pref, 3),
                        'capacity_score': round(cap_score, 3),
                        'preference_matches': list(set(matched_prefs)),
                        'available_all_dates': True,
                        'zone_id': furniture_dict[pair[0]]['zone_id']
                    })

        # Try triplets if needed
        if num_people > 4 and len(available_in_row) >= 3:
            for i in range(len(available_in_row) - 2):
                triplet = available_in_row[i:i+3]
                contiguity = validate_cluster_contiguity(triplet, occupancy_map)

                if contiguity['is_contiguous']:
                    total_cap = sum(furniture_dict[fid]['capacity'] for fid in triplet)

                    if total_cap >= num_people:
                        avg_pref = sum(
                            next((f['preference_score'] for f in scored_furniture if f['id'] == fid), 0)
                            for fid in triplet
                        ) / len(triplet)

                        cap_score = score_capacity_match(total_cap, num_people)

                        total_score = (
                            SUGGESTION_WEIGHTS['contiguity'] * contiguity['contiguity_score'] +
                            SUGGESTION_WEIGHTS['preferences'] * avg_pref +
                            SUGGESTION_WEIGHTS['capacity'] * cap_score
                        )

                        suggestions.append({
                            'furniture_ids': triplet,
                            'furniture_numbers': [furniture_dict[fid]['number'] for fid in triplet],
                            'total_capacity': total_cap,
                            'total_score': round(total_score, 3),
                            'contiguity_score': round(contiguity['contiguity_score'], 3),
                            'preference_score': round(avg_pref, 3),
                            'capacity_score': round(cap_score, 3),
                            'preference_matches': [],
                            'available_all_dates': True,
                            'zone_id': furniture_dict[triplet[0]]['zone_id']
                        })

    # Sort by total score and limit
    suggestions.sort(key=lambda s: -s['total_score'])
    suggestions = suggestions[:limit]

    # Determine strategy
    if not suggestions:
        strategy = 'no_availability'
        message = 'No se encontraron combinaciones de mobiliario adecuadas'
    elif preferences and any(s['preference_matches'] for s in suggestions):
        strategy = 'preference_based'
        message = f'Sugerencias basadas en preferencias ({len(suggestions)} opciones)'
    else:
        strategy = 'capacity_based'
        message = f'Sugerencias basadas en capacidad ({len(suggestions)} opciones)'

    return {
        'success': len(suggestions) > 0,
        'strategy': strategy,
        'suggestions': suggestions,
        'total_available': len(available_ids),
        'message': message
    }


# =============================================================================
# CUSTOMER HISTORY SUGGESTIONS
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
    db = get_db()
    cursor = db.cursor()

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
