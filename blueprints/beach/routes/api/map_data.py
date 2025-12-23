"""
Map data API routes.
Endpoints for retrieving map data and availability information.
"""

from flask import request, jsonify
from flask_login import login_required
from datetime import date

from utils.decorators import permission_required
from models.zone import get_all_zones
from models.furniture import get_all_furniture
from models.furniture_type import get_all_furniture_types
from models.state import get_all_states
from models.reservation import get_furniture_availability_map


def register_routes(bp):
    """Register map data routes on the blueprint."""

    @bp.route('/map/data')
    @login_required
    @permission_required('beach.map.view')
    def map_data():
        """
        Get all data needed to render the interactive map.

        Query params:
            date: Date string YYYY-MM-DD (default: today)

        Returns:
            JSON with zones, furniture, furniture_types, states, availability
        """
        date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))

        # Get all static data
        zones = get_all_zones(active_only=True)
        furniture = get_all_furniture(active_only=True)
        furniture_types = get_all_furniture_types(active_only=True)
        states = get_all_states(active_only=True)

        # Build lookup dicts
        furniture_types_map = {ft['type_code']: ft for ft in furniture_types}
        state_colors = {s['name']: s['color'] for s in states}

        # Get availability for the date
        availability = get_furniture_availability_map(date_str, date_str)

        # Build furniture availability lookup for the specific date
        furniture_availability = {}
        if availability and 'availability' in availability:
            for fid, dates_data in availability['availability'].items():
                if date_str in dates_data:
                    furniture_availability[int(fid)] = dates_data[date_str]

        # Calculate zone bounds for rendering (vertical stacking)
        zone_bounds = {}
        zone_padding = 20
        zone_height = 200
        map_width = 1200

        for idx, zone in enumerate(zones):
            zone_bounds[zone['id']] = {
                'x': zone_padding,
                'y': zone_padding + idx * (zone_height + zone_padding),
                'width': map_width - 2 * zone_padding,
                'height': zone_height
            }

        # Calculate total map height based on zones
        total_height = zone_padding + len(zones) * (zone_height + zone_padding)

        return jsonify({
            'success': True,
            'date': date_str,
            'zones': zones,
            'zone_bounds': zone_bounds,
            'furniture': furniture,
            'furniture_types': furniture_types_map,
            'states': states,
            'state_colors': state_colors,
            'availability': furniture_availability,
            'summary': availability.get('summary', {}).get(date_str, {}),
            'map_dimensions': {
                'width': map_width,
                'height': max(800, total_height)
            }
        })

    @bp.route('/map/availability')
    @login_required
    @permission_required('beach.map.view')
    def map_availability():
        """
        Get availability for date range (for calendar/timeline view).

        Query params:
            date_from: Start date YYYY-MM-DD
            date_to: End date YYYY-MM-DD (default: same as date_from)
            zone_id: Filter by zone (optional)

        Returns:
            JSON availability matrix
        """
        date_from = request.args.get('date_from', date.today().strftime('%Y-%m-%d'))
        date_to = request.args.get('date_to', date_from)
        zone_id = request.args.get('zone_id', type=int)

        try:
            availability = get_furniture_availability_map(
                date_from, date_to,
                zone_id=zone_id
            )

            return jsonify({
                'success': True,
                'date_from': date_from,
                'date_to': date_to,
                **availability
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
