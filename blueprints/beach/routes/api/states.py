"""
States API endpoints for fetching reservation states with colors.
Used by standalone reservation panel and other components that need
dynamic state colors without full map data.
"""

from flask import jsonify
from flask_login import login_required
from models.state import get_all_states


def register_routes(bp):
    """Register states API routes on the blueprint."""

    @bp.route('/states', methods=['GET'])
    @login_required
    def get_states():
        """
        Get all active reservation states with their colors and properties.

        Response JSON:
        {
            "success": true,
            "states": [
                {
                    "id": 1,
                    "code": "confirmada",
                    "name": "Confirmada",
                    "color": "#4A7C59",
                    "icon": "fa-check",
                    "is_availability_releasing": 0,
                    "display_order": 1,
                    "display_priority": 10
                },
                ...
            ]
        }
        """
        try:
            states = get_all_states(active_only=True)

            # Return only fields needed by the panel
            filtered_states = []
            for state in states:
                filtered_states.append({
                    'id': state['id'],
                    'code': state['code'],
                    'name': state['name'],
                    'color': state['color'],
                    'icon': state.get('icon'),
                    'is_availability_releasing': state['is_availability_releasing'],
                    'display_order': state['display_order'],
                    'display_priority': state['display_priority']
                })

            return jsonify({
                'success': True,
                'states': filtered_states
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
