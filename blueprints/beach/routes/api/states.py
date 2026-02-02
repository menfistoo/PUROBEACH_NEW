"""
States API endpoints for fetching reservation states with colors.
Used by standalone reservation panel and other components that need
dynamic state colors without full map data.
Also exposes valid state transitions for frontend validation.
"""

from flask import current_app, request
from flask_login import login_required
from models.state import get_all_states
from utils.api_response import api_success, api_error
from models.reservation_state import get_valid_transitions, get_allowed_transitions


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

            return api_success(states=filtered_states)

        except Exception as e:
            current_app.logger.error(f'Error fetching states: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)

    @bp.route('/states/transitions', methods=['GET'])
    @login_required
    def get_state_transitions():
        """
        Get valid state transitions matrix.

        Optional query param:
            current_state: Get transitions for a specific state only

        Response JSON:
        {
            "success": true,
            "transitions": {
                "Confirmada": ["Sentada", "Cancelada", "No-Show"],
                ...
            }
        }
        """
        try:
            current_state = request.args.get('current_state')

            if current_state is not None:
                allowed = get_allowed_transitions(current_state)
                return api_success(
                    current_state=current_state,
                    allowed_transitions=sorted(allowed)
                )

            # Return full matrix (convert sets to sorted lists for JSON)
            transitions = get_valid_transitions()
            serializable = {}
            for key, values in transitions.items():
                display_key = key if key else '__initial__'
                serializable[display_key] = sorted(values)

            return api_success(transitions=serializable)

        except Exception as e:
            current_app.logger.error(f'Error fetching transitions: {e}', exc_info=True)
            return api_error('Error interno del servidor', 500)
