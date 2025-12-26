"""
Smart furniture suggestion algorithm.
Recommends optimal furniture based on preferences, contiguity, and capacity.

Scoring weights: 40% contiguity + 35% preferences + 25% capacity

Phase 6B - Module 3 (Main API with re-exports from specialized modules)
"""

# Re-export functions from specialized modules for backward compatibility
from .reservation_suggestions_map import (
    build_furniture_occupancy_map,
    get_customer_preferred_furniture,
    ROW_TOLERANCE_PX
)

from .reservation_suggestions_scoring import (
    validate_cluster_contiguity,
    get_furniture_features,
    score_preference_match,
    score_capacity_match,
    PREFERENCE_TO_FEATURE
)


# =============================================================================
# CONSTANTS
# =============================================================================

SUGGESTION_WEIGHTS = {
    'contiguity': 0.40,
    'preferences': 0.35,
    'capacity': 0.25
}


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
