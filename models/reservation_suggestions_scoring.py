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

# Note: PREFERENCE_TO_FEATURE mapping removed.
# Now uses unified características system with direct ID matching.


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
# PREFERENCE MATCHING (CARACTERÍSTICAS SYSTEM)
# =============================================================================

def score_preference_match(furniture_id: int, preferences: list) -> dict:
    """
    Score how well furniture matches requested characteristics.

    Uses the unified características system - direct ID comparison.

    Args:
        furniture_id: Furniture ID to score
        preferences: List of characteristic IDs requested (NOT codes)

    Returns:
        dict: {
            'score': float (0.0 to 1.0),
            'matched': list of matched characteristic names,
            'total_requested': int
        }
    """
    from models.characteristic_assignments import score_characteristic_match

    # Handle empty preferences
    if not preferences:
        return {
            'score': 1.0,
            'matched': [],
            'total_requested': 0
        }

    # Use the new characteristic matching system
    result = score_characteristic_match(furniture_id, preferences)

    # Get matched characteristic names for display
    matched_names = []
    if result['matched']:
        from models.characteristic import get_characteristic_by_id
        for char_id in result['matched']:
            char = get_characteristic_by_id(char_id)
            if char:
                matched_names.append(char['name'])

    return {
        'score': result['score'],
        'matched': matched_names,
        'total_requested': len(preferences)
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
