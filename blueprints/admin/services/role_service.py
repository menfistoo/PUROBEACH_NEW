"""
Business logic for role and permission management.
Handles validation, cloning, and audit logging for roles.
"""

import json
import re
from database import get_db
from models.role import (get_role_by_name, get_role_by_id, get_role_permissions,
                          create_role, update_role, delete_role, has_users,
                          bulk_set_permissions)
from models.permission import get_all_permissions


def validate_role_name(name: str, exclude_id: int = None) -> tuple:
    """
    Validate role name format and uniqueness.

    Args:
        name: Role name (slug)
        exclude_id: Role ID to exclude from uniqueness check (for updates)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not re.match(r'^[a-z0-9_-]{3,30}$', name):
        return False, 'invalid_role_name'

    existing = get_role_by_name(name)
    if existing and (exclude_id is None or existing['id'] != exclude_id):
        return False, 'role_name_exists'

    return True, ''


def create_custom_role(name: str, display_name: str, description: str = None,
                       clone_from_id: int = None) -> dict:
    """
    Create a custom role with optional permission cloning.

    Args:
        name: Unique role name (slug)
        display_name: Display name for UI
        description: Optional description
        clone_from_id: Role ID to clone permissions from

    Returns:
        Dict with 'success', 'role_id', 'error'
    """
    is_valid, error = validate_role_name(name)
    if not is_valid:
        return {'success': False, 'error': error}

    if not display_name or len(display_name.strip()) < 2:
        return {'success': False, 'error': 'invalid_display_name'}

    role_id = create_role(name, display_name.strip(), description)

    # Clone permissions if template selected
    if clone_from_id:
        source_perms = get_role_permissions(clone_from_id)
        perm_ids = [p['id'] for p in source_perms]
        if perm_ids:
            bulk_set_permissions(role_id, perm_ids)

    return {'success': True, 'role_id': role_id}


def can_delete_role(role_id: int) -> tuple:
    """
    Check if a role can be deleted.

    Args:
        role_id: Role ID

    Returns:
        Tuple of (can_delete, error_message_key)
    """
    role = get_role_by_id(role_id)
    if not role:
        return False, 'role_not_found'

    if role['is_system']:
        return False, 'role_is_system'

    if has_users(role_id):
        return False, 'role_has_users'

    return True, ''


def can_edit_permissions(role_id: int) -> tuple:
    """
    Check if a role's permissions can be edited.

    Args:
        role_id: Role ID

    Returns:
        Tuple of (can_edit, error_message_key)
    """
    role = get_role_by_id(role_id)
    if not role:
        return False, 'role_not_found'

    if role['name'] == 'admin':
        return False, 'role_is_admin'

    return True, ''


def get_permissions_matrix(role_id: int) -> dict:
    """
    Build the permission matrix data for the UI.

    Groups permissions by module group and feature, with action columns.

    Args:
        role_id: Role ID

    Returns:
        Dict with 'groups' (list of module groups) and 'assigned_ids' (set)
    """
    all_perms = get_all_permissions()
    role_perms = get_role_permissions(role_id)
    assigned_ids = {p['id'] for p in role_perms}

    # Define module groups for display
    MODULE_GROUPS = {
        'operations': {'label': 'Beach - Operaciones', 'order': 1},
        'config': {'label': 'Beach - Configuración', 'order': 2},
        'reports': {'label': 'Beach - Informes', 'order': 3},
        'admin': {'label': 'Administración', 'order': 4},
        'api': {'label': 'API', 'order': 5},
    }

    # Extract action from permission code (last segment)
    ACTION_LABELS = {
        'view': 'Ver',
        'create': 'Crear',
        'edit': 'Editar',
        'delete': 'Eliminar',
        'manage': 'Gestionar',
        'import': 'Importar',
        'export': 'Exportar',
        'interact': 'Interactuar',
        'change_state': 'Cambiar Estado',
        'merge': 'Fusionar',
        'access': 'Acceso',
        'admin': 'Administrar',
        'payment_reconciliation': 'Conciliación',
    }

    # Build structure: group -> features -> actions
    groups = {}

    for perm in all_perms:
        # Skip parent menu items (they have no URL and are grouping-only)
        if perm['code'].startswith('menu.'):
            continue

        module = perm['module']
        if module not in MODULE_GROUPS:
            continue

        if module not in groups:
            groups[module] = {
                'label': MODULE_GROUPS[module]['label'],
                'order': MODULE_GROUPS[module]['order'],
                'features': {}
            }

        # Parse feature and action from code: "module.feature.action" or "beach.feature.action"
        parts = perm['code'].split('.')
        if len(parts) >= 3:
            feature = parts[-2]  # e.g., "reservations", "users"
            action = parts[-1]   # e.g., "view", "create"
        elif len(parts) == 2:
            feature = parts[-1]
            action = parts[-1]
        else:
            continue

        # Feature display name (capitalize, replace underscores)
        feature_label = feature.replace('_', ' ').title()

        if feature not in groups[module]['features']:
            groups[module]['features'][feature] = {
                'label': feature_label,
                'actions': {}
            }

        action_label = ACTION_LABELS.get(action, action.title())
        groups[module]['features'][feature]['actions'][action] = {
            'id': perm['id'],
            'code': perm['code'],
            'label': action_label,
            'assigned': perm['id'] in assigned_ids
        }

    # Sort groups by order
    sorted_groups = sorted(groups.values(), key=lambda g: g['order'])

    # Collect all unique action types across all groups for column headers
    all_actions = set()
    for group in sorted_groups:
        for feature in group['features'].values():
            all_actions.update(feature['actions'].keys())

    # Define column order
    ACTION_ORDER = ['view', 'create', 'edit', 'delete', 'manage', 'change_state',
                    'merge', 'interact', 'import', 'export', 'access', 'admin',
                    'payment_reconciliation']

    return {
        'groups': sorted_groups,
        'assigned_ids': list(assigned_ids),
        'action_order': [a for a in ACTION_ORDER if a in all_actions],
        'action_labels': ACTION_LABELS,
    }


def log_permission_change(user_id: int, role_id: int, action: str, details: dict) -> None:
    """
    Log a permission-related change to the audit log.

    Args:
        user_id: ID of user making the change
        role_id: Role ID being modified
        action: Action type (role_created, role_updated, role_deleted, permissions_updated)
        details: Dict with change details
    """
    with get_db() as conn:
        conn.execute('''
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, changes)
            VALUES (?, ?, 'role', ?, ?)
        ''', (user_id, action, role_id, json.dumps(details, ensure_ascii=False)))
        conn.commit()


def get_role_audit_log(role_id: int, page: int = 1, per_page: int = 10) -> dict:
    """
    Get paginated audit log for a role.

    Args:
        role_id: Role ID
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Dict with 'entries', 'total', 'page', 'pages'
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Count total
        cursor.execute('''
            SELECT COUNT(*) as count FROM audit_log
            WHERE entity_type = 'role' AND entity_id = ?
        ''', (role_id,))
        total = cursor.fetchone()['count']

        # Get page
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT al.*, u.username, u.full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.entity_type = 'role' AND al.entity_id = ?
            ORDER BY al.created_at DESC
            LIMIT ? OFFSET ?
        ''', (role_id, per_page, offset))

        entries = []
        for row in cursor.fetchall():
            entry = dict(row)
            entry['changes'] = json.loads(entry['changes']) if entry['changes'] else {}
            entries.append(entry)

        pages = (total + per_page - 1) // per_page

        return {
            'entries': entries,
            'total': total,
            'page': page,
            'pages': pages
        }
