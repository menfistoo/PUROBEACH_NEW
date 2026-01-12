"""
Furniture Manager - Unified configuration page.
Consolidates Map Editor, Furniture List, Furniture Types, and Zones into a tabbed interface.
"""

from flask import render_template, request, redirect, url_for
from flask_login import login_required
from utils.decorators import permission_required
from models.zone import get_all_zones, get_zone_by_id
from models.furniture import get_all_furniture
from models.furniture_type import get_all_furniture_types


def register_routes(bp):
    """Register furniture manager routes."""

    @bp.route('/furniture-manager')
    @login_required
    @permission_required('beach.config.furniture.view')
    def furniture_manager():
        """Unified furniture management page with tabs."""
        # Determine which tab is active (default: map-editor)
        active_tab = request.args.get('tab', 'map-editor')

        # Zone filter for furniture list
        zone_filter = request.args.get('zone', '')
        type_filter = request.args.get('type', '')
        active_filter = request.args.get('active', '1')

        # Get common data
        zones = get_all_zones(active_only=True)
        zones_all = get_all_zones(active_only=False)
        furniture_types = get_all_furniture_types(active_only=True)
        furniture_types_all = get_all_furniture_types(active_only=False)

        # Get furniture list data
        zone_id = int(zone_filter) if zone_filter else None
        active_only = active_filter == '1'
        all_furniture = get_all_furniture(zone_id=zone_id, active_only=active_only)
        if type_filter:
            all_furniture = [f for f in all_furniture if f['furniture_type'] == type_filter]

        # Get distinct furniture types for filter dropdown
        from models.furniture import get_furniture_types
        types_for_filter = get_furniture_types()

        # For furniture types tab - check if editing
        selected_type = None
        mode = None
        type_id = request.args.get('type_id')
        if type_id:
            from models.furniture_type import get_furniture_type_by_id
            selected_type = get_furniture_type_by_id(int(type_id))
            mode = 'edit' if selected_type else None
        elif request.args.get('create') == '1':
            mode = 'create'

        # For zones tab - check if editing or creating
        selected_zone = None
        zones_mode = None
        zones_for_parent = zones_all  # All zones can be parents
        zone_edit_id = request.args.get('zone_id')
        if zone_edit_id:
            selected_zone = get_zone_by_id(int(zone_edit_id))
            zones_mode = 'edit' if selected_zone else None
            # Exclude current zone from parent list
            if selected_zone:
                zones_for_parent = [z for z in zones_all if z['id'] != selected_zone['id']]
        elif request.args.get('create_zone') == '1':
            zones_mode = 'create'

        return render_template('beach/config/furniture_manager.html',
                               active_tab=active_tab,
                               zones=zones,
                               zones_all=zones_all,
                               furniture_types=furniture_types,
                               furniture_types_all=furniture_types_all,
                               furniture=all_furniture,
                               types=types_for_filter,
                               zone_filter=zone_filter,
                               type_filter=type_filter,
                               active_filter=active_filter,
                               selected_type=selected_type,
                               mode=mode,
                               # Zones tab data
                               selected_zone=selected_zone,
                               zones_mode=zones_mode,
                               zones_for_parent=zones_for_parent)
