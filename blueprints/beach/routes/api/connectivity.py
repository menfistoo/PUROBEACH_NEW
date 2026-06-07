"""
Connectivity logging API.
Receives client-reported network drops (WiFi roaming gaps) so staff connection
issues can be audited. The browser already detects offline/online; on reconnect
it posts how long it was offline.
"""

from flask import current_app, request
from flask_login import login_required, current_user

from utils.api_response import api_success, api_error
from models.connectivity_log import log_connectivity_event


def register_routes(bp):
    """Register connectivity routes on the blueprint."""

    @bp.route('/connectivity-log', methods=['POST'])
    @login_required
    def connectivity_log():
        """
        Record a connectivity event reported by the browser on reconnect.

        Request body (JSON):
            offline_at: str (ISO) - when the client lost connection
            online_at: str (ISO) - when it recovered
            duration_seconds: number - how long it was offline
            page: str - the page the user was on
        """
        data = request.get_json(silent=True) or {}

        try:
            duration = data.get('duration_seconds')
            duration = int(duration) if duration is not None else None
        except (ValueError, TypeError):
            duration = None

        # Ignore implausible values (clock skew / spurious events)
        if duration is not None and (duration < 0 or duration > 86400):
            return api_success(message='Ignorado')

        ip = request.headers.get('CF-Connecting-IP') or request.remote_addr
        user_agent = (request.headers.get('User-Agent') or '')[:300]
        page = (data.get('page') or '')[:300]

        try:
            log_connectivity_event(
                user_id=getattr(current_user, 'id', None),
                username=getattr(current_user, 'username', None),
                offline_at=data.get('offline_at'),
                online_at=data.get('online_at'),
                duration_seconds=duration,
                page=page,
                user_agent=user_agent,
                ip=ip,
            )
            # Also log to the app log for immediate auditing alongside other logs.
            current_app.logger.info(
                f'Connectivity drop: user={getattr(current_user, "username", "?")} '
                f'duration={duration}s page={page} ip={ip}'
            )
            return api_success(message='Registrado')
        except Exception as e:
            current_app.logger.error(f'Error logging connectivity event: {e}', exc_info=True)
            return api_error('Error al registrar', 500)
