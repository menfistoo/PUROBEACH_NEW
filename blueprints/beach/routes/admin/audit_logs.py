"""
Audit log administration routes.
Provides API and page endpoints for viewing and searching audit logs.
Admin-only access with 'admin.audit.view' permission required.
"""

import json
from flask import render_template, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register audit log routes on the blueprint."""

    @bp.route('/audit-logs')
    @login_required
    @permission_required('admin.audit.view')
    def audit_logs():
        """
        Audit log viewer page.
        Renders HTML template with search filters and paginated results.
        """
        from models.audit_log import (
            get_audit_logs,
            count_audit_logs,
            get_distinct_actions,
            get_distinct_entity_types
        )
        from models.user import get_all_users

        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action', '').strip() or None
        entity_type = request.args.get('entity_type', '').strip() or None
        start_date = request.args.get('start_date', '').strip() or None
        end_date = request.args.get('end_date', '').strip() or None

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)  # Cap at 100
        offset = (page - 1) * per_page

        # Get filtered logs
        logs = get_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
            limit=per_page,
            offset=offset
        )

        # Parse changes JSON for display
        for log in logs:
            if log.get('changes'):
                try:
                    log['changes_parsed'] = json.loads(log['changes'])
                except (json.JSONDecodeError, TypeError):
                    log['changes_parsed'] = None

        # Get total count for pagination
        total = count_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date
        )

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        # Get filter options
        users = get_all_users(active_only=False)
        actions = get_distinct_actions()
        entity_types = get_distinct_entity_types()

        return render_template(
            'beach/admin/audit_logs.html',
            logs=logs,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            users=users,
            actions=actions,
            entity_types=entity_types,
            filters={
                'user_id': user_id,
                'action': action,
                'entity_type': entity_type,
                'start_date': start_date,
                'end_date': end_date
            }
        )

    @bp.route('/audit-logs/api')
    @login_required
    @permission_required('admin.audit.view')
    def audit_logs_api():
        """
        Audit logs JSON API endpoint.
        Supports filtering by user_id, action, entity_type, date range.

        Query Parameters:
            user_id (int): Filter by user ID
            action (str): Filter by action type (CREATE, UPDATE, DELETE, etc.)
            entity_type (str): Filter by entity type (reservation, customer, etc.)
            entity_id (int): Filter by specific entity ID
            start_date (str): Filter from date (YYYY-MM-DD)
            end_date (str): Filter until date (YYYY-MM-DD)
            page (int): Page number (default 1)
            per_page (int): Results per page (default 50, max 100)

        Returns:
            JSON response with logs, pagination info, and metadata
        """
        from models.audit_log import get_audit_logs, count_audit_logs

        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action', '').strip() or None
        entity_type = request.args.get('entity_type', '').strip() or None
        entity_id = request.args.get('entity_id', type=int)
        start_date = request.args.get('start_date', '').strip() or None
        end_date = request.args.get('end_date', '').strip() or None

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        per_page = min(per_page, 100)  # Cap at 100
        offset = (page - 1) * per_page

        # Get filtered logs
        logs = get_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            limit=per_page,
            offset=offset
        )

        # Parse changes JSON for each log
        for log in logs:
            if log.get('changes'):
                try:
                    log['changes'] = json.loads(log['changes'])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Get total count for pagination
        total = count_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date
        )

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        return jsonify({
            'success': True,
            'data': logs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })

    @bp.route('/audit-logs/<int:log_id>')
    @login_required
    @permission_required('admin.audit.view')
    def audit_log_detail(log_id):
        """
        Get single audit log entry details.

        Args:
            log_id: Audit log ID

        Returns:
            JSON response with audit log details or 404 error
        """
        from models.audit_log import get_audit_log_by_id

        log = get_audit_log_by_id(log_id)

        if not log:
            return jsonify({
                'success': False,
                'error': 'Registro de auditoría no encontrado'
            }), 404

        # Parse changes JSON
        if log.get('changes'):
            try:
                log['changes'] = json.loads(log['changes'])
            except (json.JSONDecodeError, TypeError):
                pass

        return jsonify({
            'success': True,
            'data': log
        })

    @bp.route('/audit-logs/entity/<entity_type>/<int:entity_id>')
    @login_required
    @permission_required('admin.audit.view')
    def audit_log_entity_history(entity_type, entity_id):
        """
        Get audit history for a specific entity.

        Args:
            entity_type: Entity type (reservation, customer, etc.)
            entity_id: Entity ID

        Returns:
            JSON response with entity's audit history
        """
        from models.audit_log import get_audit_logs_for_entity

        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)

        logs = get_audit_logs_for_entity(entity_type, entity_id, limit)

        # Parse changes JSON for each log
        for log in logs:
            if log.get('changes'):
                try:
                    log['changes'] = json.loads(log['changes'])
                except (json.JSONDecodeError, TypeError):
                    pass

        return jsonify({
            'success': True,
            'data': logs,
            'entity': {
                'type': entity_type,
                'id': entity_id
            }
        })

    @bp.route('/audit-logs/filters')
    @login_required
    @permission_required('admin.audit.view')
    def audit_log_filters():
        """
        Get available filter options for audit logs.

        Returns:
            JSON response with distinct actions, entity types, and users
        """
        from models.audit_log import get_distinct_actions, get_distinct_entity_types
        from models.user import get_all_users

        actions = get_distinct_actions()
        entity_types = get_distinct_entity_types()
        users = get_all_users(active_only=False)

        # Simplify user data for filter dropdown
        users_simplified = [
            {'id': u['id'], 'username': u['username'], 'full_name': u.get('full_name')}
            for u in users
        ]

        return jsonify({
            'success': True,
            'data': {
                'actions': actions,
                'entity_types': entity_types,
                'users': users_simplified
            }
        })

    @bp.route('/audit-logs/stats')
    @login_required
    @permission_required('admin.audit.view')
    def audit_log_stats():
        """
        Get audit log statistics.

        Returns:
            JSON response with retention stats and summary data
        """
        from models.audit_log import get_retention_stats, count_audit_logs

        stats = get_retention_stats()

        # Get counts by action type
        action_counts = {}
        for action in ['CREATE', 'UPDATE', 'DELETE', 'VIEW']:
            action_counts[action] = count_audit_logs(action=action)

        return jsonify({
            'success': True,
            'data': {
                'retention': stats,
                'action_counts': action_counts
            }
        })
