"""
Scoring algorithms for furniture suggestion system.

Calculates contiguity, preference matching, and capacity scores
for optimal furniture selection.

Scoring weights: 40% contiguity + 35% preferences + 25% capacity

Phase 6B - Module 3B (Refactored from reservation_suggestions.py)
"""

from database import get_db


# =============================================================================
# CONSTANTS
# =============================================================================

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
