# Advanced Permission Management - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the read-only role detail view with full permission management: checkbox matrix, custom role CRUD, cloning, and audit history.

**Architecture:** Extend the existing admin blueprint with new routes for role CRUD and AJAX permission save. Create a role_service.py for business logic (validation, cloning, audit). Rewrite role_detail.html with tabbed layout (matrix + history). Add role-permissions.js for client-side matrix interactions.

**Tech Stack:** Flask/Jinja2/Bootstrap 5 (existing), AJAX with fetch API for permission saves and audit log loading.

**Design doc:** `docs/plans/2026-01-31-advanced-permissions-design.md`

---

## Task 1: Role Service — Business Logic

**Files:**
- Create: `blueprints/admin/services/role_service.py`
- Create: `blueprints/admin/services/__init__.py`
- Modify: `models/role.py` — add `bulk_set_permissions`, `delete_role`
- Modify: `utils/messages.py` — add role-related messages

**Step 1: Add bulk_set_permissions and delete_role to models/role.py**

Add at end of `models/role.py`:

```python
def bulk_set_permissions(role_id: int, permission_ids: list) -> dict:
    """
    Replace all permissions for a role with the given set.

    Args:
        role_id: Role ID
        permission_ids: List of permission IDs to assign

    Returns:
        Dict with 'added' and 'removed' lists of permission dicts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        conn.execute('BEGIN IMMEDIATE')

        # Get current permissions
        cursor.execute('''
            SELECT p.id, p.code, p.name
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = ?
        ''', (role_id,))
        current = {row['id']: dict(row) for row in cursor.fetchall()}

        current_ids = set(current.keys())
        new_ids = set(permission_ids)

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        # Remove revoked permissions
        if to_remove:
            placeholders = ','.join('?' * len(to_remove))
            cursor.execute(f'''
                DELETE FROM role_permissions
                WHERE role_id = ? AND permission_id IN ({placeholders})
            ''', [role_id] + list(to_remove))

        # Add new permissions
        for perm_id in to_add:
            cursor.execute('''
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, perm_id))

        # Get details of added permissions for audit
        added_details = []
        if to_add:
            placeholders = ','.join('?' * len(to_add))
            cursor.execute(f'SELECT id, code, name FROM permissions WHERE id IN ({placeholders})',
                          list(to_add))
            added_details = [dict(row) for row in cursor.fetchall()]

        removed_details = [current[pid] for pid in to_remove]

        conn.commit()

        return {'added': added_details, 'removed': removed_details}


def delete_role(role_id: int) -> bool:
    """
    Delete a custom role.

    Args:
        role_id: Role ID to delete

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM roles WHERE id = ? AND is_system = 0', (role_id,))
        conn.commit()
        return cursor.rowcount > 0
```

**Step 2: Add role messages to utils/messages.py**

Add these keys to the MESSAGES dict:

```python
    # Role management
    'role_created': 'Rol creado exitosamente',
    'role_updated': 'Rol actualizado correctamente',
    'role_deleted': 'Rol eliminado',
    'role_permissions_updated': 'Permisos actualizados correctamente',
    'role_name_exists': 'Ya existe un rol con ese nombre',
    'role_has_users': 'No se puede eliminar un rol con usuarios asignados',
    'role_is_system': 'No se puede eliminar un rol de sistema',
    'role_is_admin': 'Los permisos del rol Administrador no se pueden modificar',
    'role_not_found': 'Rol no encontrado',
    'invalid_role_name': 'El nombre interno solo puede contener letras minúsculas, números, guiones y guiones bajos (3-30 caracteres)',
```

**Step 3: Create blueprints/admin/services/__init__.py**

```python
"""Admin services package."""
```

**Step 4: Create blueprints/admin/services/role_service.py**

```python
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
        return {'success': False, 'error': 'El nombre visible debe tener al menos 2 caracteres'}

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
                    'merge', 'interact', 'import', 'export', 'access', 'admin']

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
```

**Step 5: Run tests**

```bash
cd C:\Users\catia\programas\PuroBeach\PuroBeach\.worktrees\advanced-permissions
python -m pytest tests/ -x --tb=short -q
```

Expected: Same 208 pass / 1 pre-existing fail (no regressions).

**Step 6: Commit**

```bash
git add models/role.py utils/messages.py blueprints/admin/services/
git commit -m "feat(admin): add role service with business logic for permission management

Add bulk_set_permissions and delete_role to role model.
Create role_service.py with validation, cloning, audit logging,
and permission matrix builder for the UI."
```

---

## Task 2: Admin Routes — Role CRUD + API Endpoints

**Files:**
- Modify: `blueprints/admin/routes.py` — add role create/edit/delete routes + AJAX endpoints
- Modify: `blueprints/admin/__init__.py` (if needed for imports)

**Step 1: Add imports and new routes to blueprints/admin/routes.py**

Add to imports at top:

```python
import json
from blueprints.admin.services.role_service import (
    validate_role_name, create_custom_role, can_delete_role,
    can_edit_permissions, get_permissions_matrix, log_permission_change,
    get_role_audit_log
)
from models.role import (get_all_roles, get_role_by_id, get_role_permissions,
                          bulk_set_permissions, update_role, delete_role)
```

Update the existing `role_detail` route (replace lines 212-242) to use the matrix builder:

```python
@admin_bp.route('/roles/<int:role_id>')
@login_required
@permission_required('admin.roles.manage')
def role_detail(role_id):
    """View role details and permission matrix."""
    role = get_role_by_id(role_id)
    if not role:
        flash('Rol no encontrado', 'error')
        return redirect(url_for('admin.roles'))

    can_edit, _ = can_edit_permissions(role_id)
    matrix = get_permissions_matrix(role_id)
    all_roles = get_all_roles()

    return render_template('role_detail.html',
                           role=role,
                           matrix=matrix,
                           can_edit=can_edit,
                           all_roles=all_roles)
```

Add new routes after the role_detail route:

```python
@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@permission_required('admin.roles.manage')
def role_create():
    """Create a new custom role."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        clone_from = request.form.get('clone_from', '')

        clone_from_id = int(clone_from) if clone_from else None

        result = create_custom_role(name, display_name, description, clone_from_id)

        if result['success']:
            # Log creation
            log_details = {'name': name, 'display_name': display_name}
            if clone_from_id:
                source_role = get_role_by_id(clone_from_id)
                log_details['cloned_from'] = source_role['name'] if source_role else str(clone_from_id)
            log_permission_change(current_user.id, result['role_id'], 'role_created', log_details)

            flash(MESSAGES['role_created'], 'success')
            return redirect(url_for('admin.role_detail', role_id=result['role_id']))
        else:
            error_msg = MESSAGES.get(result['error'], result['error'])
            flash(error_msg, 'error')
            return redirect(url_for('admin.roles'))

    # GET: redirect to roles list (creation is via modal)
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<int:role_id>/edit', methods=['POST'])
@login_required
@permission_required('admin.roles.manage')
def role_edit(role_id):
    """Edit role display name and description."""
    role = get_role_by_id(role_id)
    if not role:
        flash(MESSAGES['role_not_found'], 'error')
        return redirect(url_for('admin.roles'))

    display_name = request.form.get('display_name', '').strip()
    description = request.form.get('description', '').strip()

    if not display_name or len(display_name) < 2:
        flash('El nombre visible debe tener al menos 2 caracteres', 'error')
        return redirect(url_for('admin.role_detail', role_id=role_id))

    changes = {}
    if display_name != role['display_name']:
        changes['display_name'] = [role['display_name'], display_name]
    if description != (role['description'] or ''):
        changes['description'] = [role['description'] or '', description]

    if changes:
        update_role(role_id, display_name=display_name, description=description or None)
        log_permission_change(current_user.id, role_id, 'role_updated', {'changes': changes})
        flash(MESSAGES['role_updated'], 'success')
    else:
        flash('No se realizaron cambios', 'warning')

    return redirect(url_for('admin.role_detail', role_id=role_id))


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@permission_required('admin.roles.manage')
def role_delete(role_id):
    """Delete a custom role."""
    can_del, error_key = can_delete_role(role_id)
    if not can_del:
        flash(MESSAGES.get(error_key, error_key), 'error')
        return redirect(url_for('admin.roles'))

    role = get_role_by_id(role_id)
    deleted = delete_role(role_id)

    if deleted:
        log_permission_change(current_user.id, role_id, 'role_deleted',
                            {'name': role['name'], 'display_name': role['display_name']})
        flash(MESSAGES['role_deleted'], 'success')
    else:
        flash('Error al eliminar rol', 'error')

    return redirect(url_for('admin.roles'))


# ==================== Role Permission API (AJAX) ====================

@admin_bp.route('/api/roles/<int:role_id>/permissions', methods=['POST'])
@login_required
@permission_required('admin.roles.manage')
def api_role_permissions_save(role_id):
    """Save role permissions (AJAX)."""
    can_edit, error_key = can_edit_permissions(role_id)
    if not can_edit:
        return jsonify({'success': False, 'error': MESSAGES.get(error_key, error_key)}), 403

    data = request.get_json()
    if not data or 'permission_ids' not in data:
        return jsonify({'success': False, 'error': 'Datos inválidos'}), 400

    permission_ids = [int(pid) for pid in data['permission_ids']]

    result = bulk_set_permissions(role_id, permission_ids)

    # Log if changes were made
    if result['added'] or result['removed']:
        log_permission_change(current_user.id, role_id, 'permissions_updated', {
            'added': result['added'],
            'removed': result['removed']
        })

    return jsonify({
        'success': True,
        'added': len(result['added']),
        'removed': len(result['removed'])
    })


@admin_bp.route('/api/roles/<int:role_id>/audit-log')
@login_required
@permission_required('admin.roles.manage')
def api_role_audit_log(role_id):
    """Get role audit log (AJAX)."""
    page = request.args.get('page', 1, type=int)
    audit = get_role_audit_log(role_id, page=page)

    return jsonify(audit)
```

**Step 2: Run tests**

```bash
python -m pytest tests/ -x --tb=short -q
```

Expected: 208 pass / 1 pre-existing fail.

**Step 3: Commit**

```bash
git add blueprints/admin/routes.py
git commit -m "feat(admin): add role CRUD routes and AJAX permission endpoints

Add create, edit, delete routes for roles. Add AJAX endpoints for
bulk permission save and paginated audit log retrieval."
```

---

## Task 3: Roles List Template — Add Create Button + Actions

**Files:**
- Modify: `templates/admin/roles.html` — add create modal, update action column

**Step 1: Rewrite templates/admin/roles.html**

Replace entire file with:

```html
{% extends "base.html" %}

{% set page_title = "Gestión de Roles" %}

{% block title %}Gestión de Roles - PuroBeach{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-start mb-4">
    <div>
        <h2><i class="fas fa-user-shield"></i> Gestión de Roles</h2>
        <p class="text-muted">Administración de roles y permisos del sistema</p>
    </div>
    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createRoleModal">
        <i class="fas fa-plus"></i> Crear Rol
    </button>
</div>

<div class="card">
    <div class="table-responsive">
        <table class="table table-striped table-hover mb-0">
            <thead>
                <tr>
                    <th>Rol</th>
                    <th>Descripción</th>
                    <th>Permisos</th>
                    <th>Usuarios</th>
                    <th>Tipo</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                {% for role in roles %}
                <tr>
                    <td>
                        <strong>{{ role.display_name }}</strong>
                        <br><small class="text-muted">{{ role.name }}</small>
                    </td>
                    <td>{{ role.description or '-' }}</td>
                    <td>
                        <span class="badge bg-primary">{{ role.permission_count }} permisos</span>
                    </td>
                    <td>
                        <span class="badge bg-info">{{ role.user_count }} usuarios</span>
                    </td>
                    <td>
                        {% if role.is_system %}
                        <span class="badge bg-warning text-dark">Sistema</span>
                        {% else %}
                        <span class="badge bg-secondary">Personalizado</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if role.name == 'admin' %}
                            <a href="{{ url_for('admin.role_detail', role_id=role.id) }}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-eye"></i> Ver
                            </a>
                        {% else %}
                            <a href="{{ url_for('admin.role_detail', role_id=role.id) }}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-edit"></i> Editar
                            </a>
                            {% if not role.is_system %}
                                {% if role.user_count == 0 %}
                                <button type="button" class="btn btn-sm btn-outline-danger"
                                        data-bs-toggle="modal" data-bs-target="#deleteRoleModal"
                                        data-role-id="{{ role.id }}" data-role-name="{{ role.display_name }}">
                                    <i class="fas fa-trash"></i>
                                </button>
                                {% else %}
                                <button type="button" class="btn btn-sm btn-outline-danger" disabled
                                        title="Este rol tiene usuarios asignados">
                                    <i class="fas fa-trash"></i>
                                </button>
                                {% endif %}
                            {% endif %}
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="text-center text-muted">No se encontraron roles</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<!-- Create Role Modal -->
<div class="modal fade" id="createRoleModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST" action="{{ url_for('admin.role_create') }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-plus-circle"></i> Crear Nuevo Rol</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="display_name" class="form-label">Nombre visible <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="display_name" name="display_name"
                               required minlength="2" maxlength="50" placeholder="Ej: Recepción">
                    </div>
                    <div class="mb-3">
                        <label for="name" class="form-label">Nombre interno <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="name" name="name"
                               required pattern="[a-z0-9_-]{3,30}" placeholder="Ej: recepcion">
                        <div class="form-text">Solo letras minúsculas, números, guiones y guiones bajos (3-30 caracteres)</div>
                    </div>
                    <div class="mb-3">
                        <label for="description" class="form-label">Descripción</label>
                        <input type="text" class="form-control" id="description" name="description"
                               maxlength="200" placeholder="Descripción del rol">
                    </div>
                    <div class="mb-3">
                        <label for="clone_from" class="form-label">Basado en</label>
                        <select class="form-select" id="clone_from" name="clone_from">
                            <option value="">-- Ninguno (sin permisos) --</option>
                            {% for role in roles %}
                                {% if role.name != 'admin' %}
                                <option value="{{ role.id }}">{{ role.display_name }} ({{ role.permission_count }} permisos)</option>
                                {% endif %}
                            {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Crear Rol</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- Delete Role Confirmation Modal -->
<div class="modal fade" id="deleteRoleModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST" id="deleteRoleForm">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-exclamation-triangle text-danger"></i> Eliminar Rol</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>¿Está seguro de eliminar el rol <strong id="deleteRoleName"></strong>?</p>
                    <p class="text-muted">Esta acción no se puede deshacer.</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-danger">Eliminar</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// Auto-generate slug from display name
document.getElementById('display_name').addEventListener('input', function() {
    const nameInput = document.getElementById('name');
    if (!nameInput.dataset.manual) {
        nameInput.value = this.value
            .toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_|_$/g, '')
            .substring(0, 30);
    }
});

// Mark name as manually edited
document.getElementById('name').addEventListener('input', function() {
    this.dataset.manual = 'true';
});

// Delete modal - set role data
document.getElementById('deleteRoleModal').addEventListener('show.bs.modal', function(event) {
    const button = event.relatedTarget;
    const roleId = button.getAttribute('data-role-id');
    const roleName = button.getAttribute('data-role-name');
    document.getElementById('deleteRoleName').textContent = roleName;
    document.getElementById('deleteRoleForm').action = '/admin/roles/' + roleId + '/delete';
});
</script>
{% endblock %}
```

**Step 2: Run tests**

```bash
python -m pytest tests/test_templates.py -x --tb=short -q
```

**Step 3: Commit**

```bash
git add templates/admin/roles.html
git commit -m "feat(admin): update roles list with create modal and action buttons

Add create role modal with slug auto-generation and clone-from dropdown.
Add edit/delete action buttons with proper permission rules.
Remove Phase 2 placeholder banner."
```

---

## Task 4: Role Detail Template — Permission Matrix + Tabs

**Files:**
- Modify: `templates/admin/role_detail.html` — full rewrite with matrix and audit tab

**Step 1: Rewrite templates/admin/role_detail.html**

Replace entire file:

```html
{% extends "base.html" %}

{% block title %}{{ role.display_name }} - Permisos - PuroBeach{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-start mb-4">
    <div>
        <h2>
            <i class="fas fa-user-shield"></i> {{ role.display_name }}
            {% if role.is_system %}
            <span class="badge bg-warning text-dark">Sistema</span>
            {% else %}
            <span class="badge bg-secondary">Personalizado</span>
            {% endif %}
        </h2>
        <p class="text-muted">{{ role.description or 'Sin descripción' }}</p>
    </div>
    <div>
        <a href="{{ url_for('admin.roles') }}" class="btn btn-outline-secondary">
            <i class="fas fa-arrow-left"></i> Volver
        </a>
        {% if not role.is_system %}
        <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#editRoleModal">
            <i class="fas fa-edit"></i> Editar Rol
        </button>
        {% endif %}
    </div>
</div>

<!-- Tabs -->
<ul class="nav nav-tabs mb-3" role="tablist">
    <li class="nav-item" role="presentation">
        <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-permissions" type="button" role="tab">
            <i class="fas fa-key"></i> Permisos
        </button>
    </li>
    <li class="nav-item" role="presentation">
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-history" type="button" role="tab" id="history-tab">
            <i class="fas fa-clock-rotate-left"></i> Historial
        </button>
    </li>
</ul>

<div class="tab-content">
    <!-- Permissions Tab -->
    <div class="tab-pane fade show active" id="tab-permissions" role="tabpanel">
        {% if role.name == 'admin' %}
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            El rol <strong>Administrador</strong> tiene todos los permisos automáticamente.
        </div>
        {% endif %}

        <form id="permissionsForm">
            {% for group in matrix.groups %}
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center"
                     data-bs-toggle="collapse" data-bs-target="#group-{{ loop.index }}"
                     role="button" style="cursor: pointer;">
                    <h6 class="mb-0">
                        <i class="fas fa-folder-open"></i> {{ group.label }}
                    </h6>
                    {% if can_edit %}
                    <button type="button" class="btn btn-sm btn-outline-secondary btn-select-all"
                            data-group="{{ loop.index }}" onclick="event.stopPropagation();">
                        Seleccionar todos
                    </button>
                    {% endif %}
                </div>
                <div class="collapse show" id="group-{{ loop.index }}">
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th style="min-width: 160px;">Feature</th>
                                        {% for action_key in matrix.action_order %}
                                        <th class="text-center" style="min-width: 90px;">
                                            {% if can_edit %}
                                            <a href="#" class="text-decoration-none btn-select-column"
                                               data-group="{{ loop.parent.loop.index }}" data-action="{{ action_key }}"
                                               title="Seleccionar/deseleccionar columna">
                                                {{ matrix.action_labels[action_key] }}
                                            </a>
                                            {% else %}
                                            {{ matrix.action_labels[action_key] }}
                                            {% endif %}
                                        </th>
                                        {% endfor %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for feature_key, feature in group.features.items() %}
                                    <tr>
                                        <td><strong>{{ feature.label }}</strong></td>
                                        {% for action_key in matrix.action_order %}
                                        <td class="text-center">
                                            {% if action_key in feature.actions %}
                                            {% set perm = feature.actions[action_key] %}
                                            <input type="checkbox" class="form-check-input perm-checkbox"
                                                   name="permission_ids" value="{{ perm.id }}"
                                                   data-group="{{ loop.parent.loop.parent.loop.index }}"
                                                   data-action="{{ action_key }}"
                                                   {% if perm.assigned %}checked{% endif %}
                                                   {% if not can_edit %}disabled{% endif %}
                                                   title="{{ perm.code }}">
                                            {% endif %}
                                        </td>
                                        {% endfor %}
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}

            {% if can_edit %}
            <div class="d-flex justify-content-end mt-3">
                <button type="button" id="savePermissions" class="btn btn-primary btn-lg">
                    <i class="fas fa-save"></i> Guardar Permisos
                </button>
            </div>
            {% endif %}
        </form>
    </div>

    <!-- History Tab -->
    <div class="tab-pane fade" id="tab-history" role="tabpanel">
        <div id="auditLogContainer">
            <div class="text-center text-muted p-4">
                <i class="fas fa-spinner fa-spin"></i> Cargando historial...
            </div>
        </div>
        <div id="auditLogPagination" class="d-flex justify-content-center mt-3"></div>
    </div>
</div>

<!-- Edit Role Modal (non-admin only) -->
{% if not role.is_system or role.name != 'admin' %}
<div class="modal fade" id="editRoleModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST" action="{{ url_for('admin.role_edit', role_id=role.id) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-edit"></i> Editar Rol</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Nombre interno</label>
                        <input type="text" class="form-control" value="{{ role.name }}" disabled>
                    </div>
                    <div class="mb-3">
                        <label for="edit_display_name" class="form-label">Nombre visible <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="edit_display_name" name="display_name"
                               required minlength="2" maxlength="50" value="{{ role.display_name }}">
                    </div>
                    <div class="mb-3">
                        <label for="edit_description" class="form-label">Descripción</label>
                        <input type="text" class="form-control" id="edit_description" name="description"
                               maxlength="200" value="{{ role.description or '' }}">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Guardar</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endif %}
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/admin/role-permissions.js') }}"></script>
<script>
    initRolePermissions({{ role.id }}, {{ can_edit|tojson }});
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/admin/role_detail.html
git commit -m "feat(admin): rewrite role detail with permission matrix and audit tabs

Replace read-only permission list with interactive checkbox matrix
grouped by module. Add collapsible sections, column/row selection,
edit role modal, and audit history tab placeholder."
```

---

## Task 5: JavaScript — Permission Matrix + Audit Log

**Files:**
- Create: `static/js/admin/role-permissions.js`

**Step 1: Create the JavaScript file**

```javascript
/**
 * Role permission matrix interactions.
 * Handles checkbox selection, bulk save via AJAX, and audit log loading.
 */

let roleId = null;
let canEdit = false;

function initRolePermissions(id, editable) {
    roleId = id;
    canEdit = editable;

    if (canEdit) {
        initSelectAll();
        initColumnSelect();
        initSaveButton();
    }

    initAuditLog();
}

// ============================================================
// Select All / Column Selection
// ============================================================

function initSelectAll() {
    document.querySelectorAll('.btn-select-all').forEach(btn => {
        btn.addEventListener('click', function () {
            const group = this.dataset.group;
            const checkboxes = document.querySelectorAll(
                `.perm-checkbox[data-group="${group}"]:not(:disabled)`
            );

            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);

            this.textContent = allChecked ? 'Seleccionar todos' : 'Deseleccionar todos';
        });
    });
}

function initColumnSelect() {
    document.querySelectorAll('.btn-select-column').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const group = this.dataset.group;
            const action = this.dataset.action;
            const checkboxes = document.querySelectorAll(
                `.perm-checkbox[data-group="${group}"][data-action="${action}"]:not(:disabled)`
            );

            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);
        });
    });
}

// ============================================================
// Save Permissions (AJAX)
// ============================================================

function initSaveButton() {
    const btn = document.getElementById('savePermissions');
    if (!btn) return;

    btn.addEventListener('click', async function () {
        const checkboxes = document.querySelectorAll('.perm-checkbox:checked');
        const permissionIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
            const response = await fetch(`/admin/api/roles/${roleId}/permissions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ permission_ids: permissionIds })
            });

            const data = await response.json();

            if (data.success) {
                const msg = `Permisos actualizados: ${data.added} añadidos, ${data.removed} eliminados`;
                showToast(msg, 'success');
            } else {
                showToast(data.error || 'Error al guardar permisos', 'error');
            }
        } catch (err) {
            showToast('Error de conexión al guardar permisos', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Guardar Permisos';
        }
    });
}

function showToast(message, type) {
    // Use flash-message style notification
    const container = document.querySelector('.main-content');
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';

    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-dismissible fade show mx-3 mt-2`;
    alert.innerHTML = `
        <i class="fas ${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const content = container.querySelector('.container-fluid') || container;
    content.insertBefore(alert, content.firstChild);

    setTimeout(() => alert.remove(), 5000);
}

// ============================================================
// Audit Log
// ============================================================

function initAuditLog() {
    const historyTab = document.getElementById('history-tab');
    if (!historyTab) return;

    let loaded = false;
    historyTab.addEventListener('shown.bs.tab', function () {
        if (!loaded) {
            loadAuditLog(1);
            loaded = true;
        }
    });
}

async function loadAuditLog(page) {
    const container = document.getElementById('auditLogContainer');
    const pagination = document.getElementById('auditLogPagination');

    container.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';

    try {
        const response = await fetch(`/admin/api/roles/${roleId}/audit-log?page=${page}`);
        const data = await response.json();

        if (!data.entries || data.entries.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-4"><i class="fas fa-info-circle"></i> Sin registros de cambios</div>';
            pagination.innerHTML = '';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm table-hover">';
        html += '<thead><tr><th>Fecha</th><th>Usuario</th><th>Cambio</th><th></th></tr></thead><tbody>';

        data.entries.forEach((entry, idx) => {
            const date = new Date(entry.created_at).toLocaleString('es-ES', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            const user = entry.full_name || entry.username || 'Sistema';
            const summary = formatAuditSummary(entry);

            html += `<tr>`;
            html += `<td><small>${date}</small></td>`;
            html += `<td>${user}</td>`;
            html += `<td>${summary}</td>`;
            html += `<td>`;
            if (entry.action === 'permissions_updated' && entry.changes) {
                html += `<button class="btn btn-sm btn-outline-secondary" onclick="toggleDetail(${idx})"><i class="fas fa-eye"></i> Ver</button>`;
            }
            html += `</td></tr>`;

            // Detail row (hidden by default)
            if (entry.action === 'permissions_updated' && entry.changes) {
                html += `<tr id="detail-${idx}" style="display:none;"><td colspan="4" class="bg-light">`;
                const changes = entry.changes;
                if (changes.added && changes.added.length > 0) {
                    changes.added.forEach(p => {
                        html += `<div class="text-success"><i class="fas fa-check"></i> Añadido: ${p.name} <small class="text-muted">(${p.code})</small></div>`;
                    });
                }
                if (changes.removed && changes.removed.length > 0) {
                    changes.removed.forEach(p => {
                        html += `<div class="text-danger"><i class="fas fa-times"></i> Quitado: ${p.name} <small class="text-muted">(${p.code})</small></div>`;
                    });
                }
                html += `</td></tr>`;
            }
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;

        // Pagination
        if (data.pages > 1) {
            let pagHtml = '<nav><ul class="pagination pagination-sm">';
            for (let i = 1; i <= data.pages; i++) {
                const active = i === data.page ? 'active' : '';
                pagHtml += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="loadAuditLog(${i}); return false;">${i}</a></li>`;
            }
            pagHtml += '</ul></nav>';
            pagination.innerHTML = pagHtml;
        } else {
            pagination.innerHTML = '';
        }

    } catch (err) {
        container.innerHTML = '<div class="alert alert-danger">Error al cargar historial</div>';
    }
}

function toggleDetail(idx) {
    const row = document.getElementById(`detail-${idx}`);
    if (row) {
        row.style.display = row.style.display === 'none' ? '' : 'none';
    }
}

function formatAuditSummary(entry) {
    switch (entry.action) {
        case 'role_created': {
            const clone = entry.changes?.cloned_from;
            return 'Rol creado' + (clone ? ` (basado en ${clone})` : '');
        }
        case 'role_updated': {
            const changes = entry.changes?.changes || {};
            const fields = Object.keys(changes).map(f => {
                const labels = { display_name: 'nombre', description: 'descripción' };
                return labels[f] || f;
            });
            return `Rol editado: ${fields.join(', ')}`;
        }
        case 'role_deleted':
            return 'Rol eliminado';
        case 'permissions_updated': {
            const added = entry.changes?.added?.length || 0;
            const removed = entry.changes?.removed?.length || 0;
            const parts = [];
            if (added) parts.push(`+${added} permiso${added > 1 ? 's' : ''}`);
            if (removed) parts.push(`-${removed} permiso${removed > 1 ? 's' : ''}`);
            return parts.join(', ') || 'Sin cambios';
        }
        default:
            return entry.action;
    }
}
```

**Step 2: Create the js/admin directory if needed**

```bash
mkdir -p static/js/admin
```

**Step 3: Commit**

```bash
git add static/js/admin/role-permissions.js
git commit -m "feat(admin): add role-permissions.js for matrix interactions and audit log

Client-side logic for permission checkbox matrix: select all per group,
select/deselect column, AJAX save with CSRF. Audit log lazy-loading
with pagination and expandable permission change details."
```

---

## Task 6: Tests — Role Management

**Files:**
- Create: `tests/test_role_management.py`

**Step 1: Write tests**

```python
"""Tests for role management: CRUD, permissions, audit."""

import pytest
import json
from database import get_db, init_db


@pytest.fixture
def app():
    """Create test app with fresh database."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        init_db()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Authenticated client as admin."""
    with app.app_context():
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
    return client


class TestRoleService:
    """Test role_service business logic."""

    def test_validate_role_name_valid(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import validate_role_name
            valid, error = validate_role_name('recepcion')
            assert valid is True

    def test_validate_role_name_invalid_chars(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import validate_role_name
            valid, error = validate_role_name('Recepción!')
            assert valid is False

    def test_validate_role_name_too_short(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import validate_role_name
            valid, error = validate_role_name('ab')
            assert valid is False

    def test_validate_role_name_duplicate(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import validate_role_name
            valid, error = validate_role_name('admin')  # exists
            assert valid is False

    def test_create_custom_role(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import create_custom_role
            result = create_custom_role('test_role', 'Test Role', 'A test role')
            assert result['success'] is True
            assert result['role_id'] > 0

    def test_create_role_with_clone(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import create_custom_role
            from models.role import get_role_by_name, get_role_permissions

            staff = get_role_by_name('staff')
            staff_perms = get_role_permissions(staff['id'])

            result = create_custom_role('cloned_role', 'Cloned', clone_from_id=staff['id'])
            assert result['success'] is True

            cloned_perms = get_role_permissions(result['role_id'])
            assert len(cloned_perms) == len(staff_perms)

    def test_can_delete_custom_role(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import create_custom_role, can_delete_role
            result = create_custom_role('deletable', 'Deletable')
            can_del, error = can_delete_role(result['role_id'])
            assert can_del is True

    def test_cannot_delete_system_role(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import can_delete_role
            from models.role import get_role_by_name
            admin = get_role_by_name('admin')
            can_del, error = can_delete_role(admin['id'])
            assert can_del is False

    def test_cannot_edit_admin_permissions(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import can_edit_permissions
            from models.role import get_role_by_name
            admin = get_role_by_name('admin')
            can_edit, error = can_edit_permissions(admin['id'])
            assert can_edit is False

    def test_can_edit_staff_permissions(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import can_edit_permissions
            from models.role import get_role_by_name
            staff = get_role_by_name('staff')
            can_edit, error = can_edit_permissions(staff['id'])
            assert can_edit is True

    def test_permissions_matrix_structure(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import get_permissions_matrix
            from models.role import get_role_by_name
            staff = get_role_by_name('staff')
            matrix = get_permissions_matrix(staff['id'])

            assert 'groups' in matrix
            assert 'assigned_ids' in matrix
            assert 'action_order' in matrix
            assert len(matrix['groups']) > 0

            # Check group structure
            group = matrix['groups'][0]
            assert 'label' in group
            assert 'features' in group

    def test_bulk_set_permissions(self, app):
        with app.app_context():
            from models.role import get_role_by_name, bulk_set_permissions, get_role_permissions
            from models.permission import get_all_permissions

            staff = get_role_by_name('staff')
            all_perms = get_all_permissions()
            first_three = [p['id'] for p in all_perms[:3]]

            result = bulk_set_permissions(staff['id'], first_three)

            new_perms = get_role_permissions(staff['id'])
            assert len(new_perms) == 3
            assert 'added' in result
            assert 'removed' in result

    def test_audit_log(self, app):
        with app.app_context():
            from blueprints.admin.services.role_service import (
                log_permission_change, get_role_audit_log
            )
            from models.role import get_role_by_name

            staff = get_role_by_name('staff')
            log_permission_change(1, staff['id'], 'permissions_updated', {
                'added': [{'id': 1, 'code': 'test.perm', 'name': 'Test'}],
                'removed': []
            })

            audit = get_role_audit_log(staff['id'])
            assert audit['total'] >= 1
            assert len(audit['entries']) >= 1
            assert audit['entries'][0]['action'] == 'permissions_updated'


class TestRoleRoutes:
    """Test role management HTTP routes."""

    def test_roles_list(self, auth_client):
        response = auth_client.get('/admin/roles')
        assert response.status_code == 200
        assert b'Administrador' in response.data

    def test_role_detail(self, auth_client, app):
        with app.app_context():
            from models.role import get_role_by_name
            staff = get_role_by_name('staff')
        response = auth_client.get(f'/admin/roles/{staff["id"]}')
        assert response.status_code == 200
        assert b'Permisos' in response.data

    def test_create_role(self, auth_client):
        response = auth_client.post('/admin/roles/create', data={
            'name': 'new_role',
            'display_name': 'New Role',
            'description': 'A new role',
            'clone_from': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        assert 'Rol creado' in response.data.decode('utf-8')

    def test_create_role_duplicate_name(self, auth_client):
        response = auth_client.post('/admin/roles/create', data={
            'name': 'admin',
            'display_name': 'Another Admin',
            'clone_from': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        assert 'Ya existe' in response.data.decode('utf-8')

    def test_delete_system_role_fails(self, auth_client, app):
        with app.app_context():
            from models.role import get_role_by_name
            staff = get_role_by_name('staff')
        response = auth_client.post(f'/admin/roles/{staff["id"]}/delete',
                                     follow_redirects=True)
        assert 'sistema' in response.data.decode('utf-8').lower()

    def test_api_save_permissions(self, auth_client, app):
        with app.app_context():
            from models.role import get_role_by_name
            from models.permission import get_all_permissions
            staff = get_role_by_name('staff')
            perms = get_all_permissions()

        perm_ids = [p['id'] for p in perms[:5]]
        response = auth_client.post(
            f'/admin/api/roles/{staff["id"]}/permissions',
            data=json.dumps({'permission_ids': perm_ids}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        assert data['success'] is True

    def test_api_save_admin_permissions_forbidden(self, auth_client, app):
        with app.app_context():
            from models.role import get_role_by_name
            admin = get_role_by_name('admin')

        response = auth_client.post(
            f'/admin/api/roles/{admin["id"]}/permissions',
            data=json.dumps({'permission_ids': [1, 2, 3]}),
            content_type='application/json'
        )
        assert response.status_code == 403

    def test_api_audit_log(self, auth_client, app):
        with app.app_context():
            from models.role import get_role_by_name
            staff = get_role_by_name('staff')

        response = auth_client.get(f'/admin/api/roles/{staff["id"]}/audit-log')
        data = json.loads(response.data)
        assert 'entries' in data
        assert 'total' in data
```

**Step 2: Run the new tests**

```bash
python -m pytest tests/test_role_management.py -v --tb=short
```

Expected: All tests PASS.

**Step 3: Run full test suite**

```bash
python -m pytest tests/ -x --tb=short -q
```

Expected: 208 + new tests pass, 1 pre-existing fail.

**Step 4: Commit**

```bash
git add tests/test_role_management.py
git commit -m "test(admin): add tests for role management CRUD, permissions, and audit

Test role service validation, creation with cloning, deletion rules,
permission matrix structure, bulk permission assignment, audit logging.
Test HTTP routes for create, edit, delete, and AJAX endpoints."
```

---

## Task 7: Integration Testing + Fixes

**Step 1: Start dev server and test manually**

```bash
python app.py
```

Navigate to `/admin/roles` and verify:
- [ ] Create Role modal opens with slug auto-generation
- [ ] "Basado en" dropdown shows roles
- [ ] Created role redirects to detail with pre-loaded permissions
- [ ] Permission matrix shows all modules/features/actions
- [ ] Checkboxes are clickable, column and group selection work
- [ ] Save Permissions AJAX works (check toast notification)
- [ ] Admin role shows read-only matrix
- [ ] History tab loads audit entries
- [ ] Delete button works for custom roles without users
- [ ] Delete button disabled for roles with users

**Step 2: Fix any issues found**

**Step 3: Run full test suite**

```bash
python -m pytest tests/ -x --tb=short -q
```

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix(admin): integration fixes for role permission management"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Role service business logic | `role_service.py`, `role.py`, `messages.py` |
| 2 | Admin routes (CRUD + API) | `routes.py` |
| 3 | Roles list template | `roles.html` |
| 4 | Role detail template (matrix + tabs) | `role_detail.html` |
| 5 | JavaScript (matrix + audit) | `role-permissions.js` |
| 6 | Tests | `test_role_management.py` |
| 7 | Integration testing + fixes | Various |
