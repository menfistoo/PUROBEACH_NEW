"""
Tests for role management: service business logic and HTTP routes.
Covers role CRUD, permission matrix, bulk assignment, and audit logging.
"""

import json
import pytest


# =============================================================================
# HELPER: Login as admin
# =============================================================================

def login_admin(client, app):
    """Log in as the admin user and return the client."""
    with app.app_context():
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
    return client


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def staff_role_id(app):
    """Return the staff role id from seed data."""
    from models.role import get_role_by_name
    with app.app_context():
        role = get_role_by_name('staff')
        return role['id']


@pytest.fixture
def admin_role_id(app):
    """Return the admin role id from seed data."""
    from models.role import get_role_by_name
    with app.app_context():
        role = get_role_by_name('admin')
        return role['id']


# =============================================================================
# TestRoleService — Business Logic
# =============================================================================

class TestRoleService:
    """Tests for blueprints.admin.services.role_service."""

    def test_validate_role_name_valid(self, app):
        """Valid slug names pass validation."""
        from blueprints.admin.services.role_service import validate_role_name
        with app.app_context():
            is_valid, error = validate_role_name('beach-vip')
            assert is_valid is True
            assert error == ''

    def test_validate_role_name_invalid_chars(self, app):
        """Uppercase and special characters fail validation."""
        from blueprints.admin.services.role_service import validate_role_name
        with app.app_context():
            is_valid, error = validate_role_name('Admin!')
            assert is_valid is False
            assert error == 'invalid_role_name'

    def test_validate_role_name_too_short(self, app):
        """Names shorter than 3 characters fail validation."""
        from blueprints.admin.services.role_service import validate_role_name
        with app.app_context():
            is_valid, error = validate_role_name('ab')
            assert is_valid is False
            assert error == 'invalid_role_name'

    def test_validate_role_name_duplicate(self, app):
        """Existing role name 'admin' fails uniqueness check."""
        from blueprints.admin.services.role_service import validate_role_name
        with app.app_context():
            is_valid, error = validate_role_name('admin')
            assert is_valid is False
            assert error == 'role_name_exists'

    def test_create_custom_role(self, app):
        """Successfully creates a custom role."""
        from blueprints.admin.services.role_service import create_custom_role
        from models.role import get_role_by_name
        with app.app_context():
            result = create_custom_role('test-role', 'Test Role', 'A test role')
            assert result['success'] is True
            assert 'role_id' in result

            role = get_role_by_name('test-role')
            assert role is not None
            assert role['display_name'] == 'Test Role'

    def test_create_role_with_clone(self, app, staff_role_id):
        """Cloning from staff copies its permissions to the new role."""
        from blueprints.admin.services.role_service import create_custom_role
        from models.role import get_role_permissions
        with app.app_context():
            # Get staff permissions before cloning
            staff_perms = get_role_permissions(staff_role_id)
            staff_perm_ids = {p['id'] for p in staff_perms}
            assert len(staff_perm_ids) > 0, "Staff role should have permissions"

            result = create_custom_role('cloned-role', 'Cloned Role',
                                        clone_from_id=staff_role_id)
            assert result['success'] is True

            # Verify cloned permissions match staff
            new_perms = get_role_permissions(result['role_id'])
            new_perm_ids = {p['id'] for p in new_perms}
            assert new_perm_ids == staff_perm_ids

    def test_can_delete_custom_role(self, app):
        """Custom role with no users can be deleted."""
        from blueprints.admin.services.role_service import create_custom_role, can_delete_role
        with app.app_context():
            result = create_custom_role('deletable-role', 'Deletable')
            assert result['success'] is True

            can_del, error = can_delete_role(result['role_id'])
            assert can_del is True
            assert error == ''

    def test_cannot_delete_system_role(self, app, staff_role_id):
        """System role cannot be deleted."""
        from blueprints.admin.services.role_service import can_delete_role
        with app.app_context():
            can_del, error = can_delete_role(staff_role_id)
            assert can_del is False
            assert error == 'role_is_system'

    def test_cannot_edit_admin_permissions(self, app, admin_role_id):
        """Admin role permissions cannot be edited."""
        from blueprints.admin.services.role_service import can_edit_permissions
        with app.app_context():
            can_edit, error = can_edit_permissions(admin_role_id)
            assert can_edit is False
            assert error == 'role_is_admin'

    def test_can_edit_staff_permissions(self, app, staff_role_id):
        """Staff role permissions can be edited."""
        from blueprints.admin.services.role_service import can_edit_permissions
        with app.app_context():
            can_edit, error = can_edit_permissions(staff_role_id)
            assert can_edit is True
            assert error == ''

    def test_permissions_matrix_structure(self, app, staff_role_id):
        """Permission matrix has groups, assigned_ids, and action_order."""
        from blueprints.admin.services.role_service import get_permissions_matrix
        with app.app_context():
            matrix = get_permissions_matrix(staff_role_id)
            assert 'groups' in matrix
            assert 'assigned_ids' in matrix
            assert 'action_order' in matrix
            assert isinstance(matrix['groups'], list)
            assert isinstance(matrix['assigned_ids'], list)
            assert isinstance(matrix['action_order'], list)
            assert len(matrix['groups']) > 0
            assert len(matrix['action_order']) > 0

    def test_bulk_set_permissions(self, app):
        """Bulk set replaces role permissions with exactly the given set."""
        from blueprints.admin.services.role_service import create_custom_role
        from models.role import bulk_set_permissions, get_role_permissions
        from models.permission import get_all_permissions
        with app.app_context():
            # Create a fresh role
            result = create_custom_role('bulk-test', 'Bulk Test')
            role_id = result['role_id']

            # Pick two permission IDs from the system
            all_perms = get_all_permissions()
            target_ids = [all_perms[0]['id'], all_perms[1]['id']]

            bulk_set_permissions(role_id, target_ids)

            assigned = get_role_permissions(role_id)
            assigned_ids = {p['id'] for p in assigned}
            assert assigned_ids == set(target_ids)

    def test_audit_log(self, app):
        """Logging and retrieval of audit entries works."""
        from blueprints.admin.services.role_service import (
            log_permission_change, get_role_audit_log, create_custom_role
        )
        with app.app_context():
            # Create a role to have an entity_id
            result = create_custom_role('audit-test', 'Audit Test')
            role_id = result['role_id']

            # Log an entry
            log_permission_change(
                user_id=1,
                role_id=role_id,
                action='role_created',
                details={'name': 'audit-test'}
            )

            # Retrieve audit log
            audit = get_role_audit_log(role_id)
            assert audit['total'] >= 1
            assert len(audit['entries']) >= 1
            assert audit['entries'][0]['action'] == 'role_created'

            changes = audit['entries'][0]['changes']
            assert changes['name'] == 'audit-test'


# =============================================================================
# TestRoleRoutes — HTTP Routes
# =============================================================================

class TestRoleRoutes:
    """Tests for admin role HTTP endpoints."""

    def test_roles_list(self, app, client):
        """GET /admin/roles returns 200."""
        login_admin(client, app)
        response = client.get('/admin/roles')
        assert response.status_code == 200

    def test_role_detail(self, app, client, staff_role_id):
        """GET /admin/roles/<id> returns 200 with 'Permisos'."""
        login_admin(client, app)
        response = client.get(f'/admin/roles/{staff_role_id}')
        assert response.status_code == 200
        assert 'Permisos' in response.data.decode('utf-8')

    def test_create_role(self, app, client):
        """POST /admin/roles/create creates role and redirects with success flash."""
        login_admin(client, app)
        response = client.post('/admin/roles/create', data={
            'name': 'http-test-role',
            'display_name': 'HTTP Test',
            'description': 'Created via HTTP',
            'clone_from': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        assert 'exitosamente' in body.lower() or 'success' in body.lower() or 'creado' in body.lower()

    def test_create_role_duplicate_name(self, app, client):
        """POST with existing name 'admin' shows error flash."""
        login_admin(client, app)
        response = client.post('/admin/roles/create', data={
            'name': 'admin',
            'display_name': 'Duplicate Admin',
            'description': '',
            'clone_from': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        assert 'existe' in body.lower() or 'error' in body.lower()

    def test_delete_system_role_fails(self, app, client, staff_role_id):
        """POST delete on system role shows error."""
        login_admin(client, app)
        response = client.post(f'/admin/roles/{staff_role_id}/delete',
                               follow_redirects=True)
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        assert 'sistema' in body.lower() or 'error' in body.lower()

    def test_api_save_permissions(self, app, client, staff_role_id):
        """POST JSON with permission_ids returns success."""
        login_admin(client, app)

        # Get some valid permission IDs
        with app.app_context():
            from models.permission import get_all_permissions
            all_perms = get_all_permissions()
            perm_ids = [all_perms[0]['id'], all_perms[1]['id']]

        response = client.post(
            f'/admin/api/roles/{staff_role_id}/permissions',
            data=json.dumps({'permission_ids': perm_ids}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_api_save_admin_permissions_forbidden(self, app, client, admin_role_id):
        """POST to admin role returns 403."""
        login_admin(client, app)
        response = client.post(
            f'/admin/api/roles/{admin_role_id}/permissions',
            data=json.dumps({'permission_ids': [1]}),
            content_type='application/json'
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data['success'] is False

    def test_api_audit_log(self, app, client):
        """GET audit log returns entries and total."""
        login_admin(client, app)

        # Create a role and log an entry so there is data
        with app.app_context():
            from blueprints.admin.services.role_service import (
                create_custom_role, log_permission_change
            )
            result = create_custom_role('audit-route-test', 'Audit Route')
            role_id = result['role_id']
            log_permission_change(1, role_id, 'role_created',
                                  {'name': 'audit-route-test'})

        response = client.get(f'/admin/api/roles/{role_id}/audit-log')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'total' in data
        assert data['total'] >= 1
