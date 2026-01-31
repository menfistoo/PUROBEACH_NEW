"""
Admin routes for user and role management.
Provides CRUD operations for users and roles (Phase 1: basic functionality).
"""

import json
import os
import time
import tempfile
from flask import render_template, redirect, url_for, flash, request, Blueprint, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from utils.decorators import permission_required
from utils.messages import MESSAGES
from models.user import (get_all_users, get_user_by_id, create_user, update_user,
                          delete_user, get_user_by_username, get_user_by_email)
from models.role import (get_all_roles, get_role_by_id, get_role_permissions,
                          bulk_set_permissions, update_role, delete_role)
from models.permission import get_all_permissions
from models.hotel_guest import (get_all_hotel_guests, get_hotel_guest_by_id,
                                  get_guest_count, get_distinct_rooms, delete_hotel_guest)
from blueprints.admin.services import (validate_user_creation, can_delete_user,
                                         import_hotel_guests_from_excel, validate_excel_file)
from blueprints.admin.services.role_service import (
    validate_role_name, create_custom_role, can_delete_role,
    can_edit_permissions, get_permissions_matrix, log_permission_change,
    get_role_audit_log
)

admin_bp = Blueprint('admin', __name__, template_folder='../../templates/admin')


@admin_bp.route('/dashboard')
@login_required
@permission_required('admin.users.view')
def dashboard():
    """Admin dashboard with summary statistics."""
    users = get_all_users(active_only=False)
    roles = get_all_roles(active_only=False)

    stats = {
        'total_users': len(users),
        'active_users': len([u for u in users if u['active']]),
        'total_roles': len(roles),
        'active_reservations': 0  # Placeholder for Phase 6
    }

    return render_template('dashboard.html', stats=stats)


@admin_bp.route('/users')
@login_required
@permission_required('admin.users.view')
def users():
    """List all users with filtering."""
    # Get filter parameters
    role_filter = request.args.get('role', '')
    active_filter = request.args.get('active', '')
    search = request.args.get('search', '')

    # Get all users
    all_users = get_all_users(active_only=False)

    # Apply filters
    if role_filter:
        all_users = [u for u in all_users if str(u['role_id']) == role_filter]

    if active_filter:
        is_active = active_filter == '1'
        all_users = [u for u in all_users if bool(u['active']) == is_active]

    if search:
        search_lower = search.lower()
        all_users = [u for u in all_users if
                     search_lower in u['username'].lower() or
                     search_lower in (u['email'] or '').lower() or
                     search_lower in (u['full_name'] or '').lower()]

    # Get roles for filter dropdown
    roles = get_all_roles()

    return render_template('users.html', users=all_users, roles=roles,
                           role_filter=role_filter, active_filter=active_filter, search=search)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@permission_required('admin.users.manage')
def users_create():
    """Create new user."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        role_id = request.form.get('role_id')

        # Validate passwords match
        if password != confirm_password:
            flash(MESSAGES['password_mismatch'], 'error')
            return redirect(url_for('admin.users_create'))

        # Validate user creation
        is_valid, error_msg = validate_user_creation(username, email, password)
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('admin.users_create'))

        # Create user
        try:
            user_id = create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name if full_name else None,
                role_id=int(role_id) if role_id else None
            )

            flash(MESSAGES['user_created'], 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'error')
            return redirect(url_for('admin.users_create'))

    # GET: Show form
    roles = get_all_roles()
    return render_template('user_form.html', user=None, roles=roles, mode='create')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('admin.users.manage')
def users_edit(user_id):
    """Edit existing user."""
    user = get_user_by_id(user_id)
    if not user:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('admin.users'))

    # Prevent editing system admin if not admin
    if user.get('username') == 'admin' and current_user.username != 'admin':
        flash('No puede editar el usuario administrador', 'error')
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role_id = request.form.get('role_id')
        active = 1 if request.form.get('active') == '1' else 0

        # Check email uniqueness (excluding current user)
        existing_user = get_user_by_email(email)
        if existing_user and existing_user['id'] != user_id:
            flash(MESSAGES['email_exists'], 'error')
            return redirect(url_for('admin.users_edit', user_id=user_id))

        # Update user
        try:
            updated = update_user(
                user_id,
                email=email,
                full_name=full_name if full_name else None,
                role_id=int(role_id) if role_id else None,
                active=active
            )

            if updated:
                flash(MESSAGES['user_updated'], 'success')
                return redirect(url_for('admin.users'))
            else:
                flash('No se realizaron cambios', 'warning')

        except Exception as e:
            flash(f'Error al actualizar usuario: {str(e)}', 'error')

    # GET: Show form
    roles = get_all_roles()
    return render_template('user_form.html', user=user, roles=roles, mode='edit')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_required('admin.users.manage')
def users_delete(user_id):
    """Soft delete user."""
    # Validate deletion
    can_delete, error_msg = can_delete_user(user_id, current_user.id)
    if not can_delete:
        flash(error_msg, 'error')
        return redirect(url_for('admin.users'))

    # Delete user
    try:
        deleted = delete_user(user_id)
        if deleted:
            flash(MESSAGES['user_deleted'], 'success')
        else:
            flash('Error al eliminar usuario', 'error')

    except Exception as e:
        flash(f'Error al eliminar usuario: {str(e)}', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/roles')
@login_required
@permission_required('admin.roles.manage')
def roles():
    """List all roles."""
    all_roles = get_all_roles(active_only=False)

    return render_template('roles.html', roles=all_roles)


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

        try:
            clone_from_id = int(clone_from) if clone_from else None
        except (ValueError, TypeError):
            clone_from_id = None

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

    try:
        permission_ids = [int(pid) for pid in data['permission_ids']]
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Datos inválidos'}), 400

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
    page = max(1, request.args.get('page', 1, type=int))
    audit = get_role_audit_log(role_id, page=page)

    return jsonify(audit)


# ==================== Hotel Guests Routes ====================

@admin_bp.route('/hotel-guests')
@login_required
@permission_required('admin.hotel_guests.view')
def hotel_guests():
    """List all hotel guests with filtering."""
    # Get filter parameters
    search = request.args.get('search', '')
    room_filter = request.args.get('room', '')
    active_only = request.args.get('active', '1') == '1'

    # Get guests
    guests = get_all_hotel_guests(
        active_only=active_only,
        search=search if search else None,
        room_filter=room_filter if room_filter else None
    )

    # Get stats
    stats = get_guest_count()

    # Get distinct rooms for filter
    rooms = get_distinct_rooms()

    return render_template('hotel_guests.html',
                           guests=guests,
                           stats=stats,
                           rooms=rooms,
                           search=search,
                           room_filter=room_filter,
                           active_only=active_only)


@admin_bp.route('/hotel-guests/import', methods=['GET', 'POST'])
@login_required
@permission_required('admin.hotel_guests.import')
def hotel_guests_import():
    """Import hotel guests from Excel file."""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('admin.hotel_guests'))

        file = request.files['file']

        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('admin.hotel_guests'))

        # Check file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('El archivo debe ser Excel (.xlsx o .xls)', 'error')
            return redirect(url_for('admin.hotel_guests'))

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        try:
            # Import guests
            result = import_hotel_guests_from_excel(temp_path, source_name=filename)

            # Build result message
            if result['created'] or result['updated']:
                flash(f"Importación completada: {result['created']} creados, {result['updated']} actualizados de {result['total']} registros", 'success')
            else:
                flash('No se importaron registros', 'warning')

            # Show room changes if any
            if result.get('room_changes'):
                room_change_count = len(result['room_changes'])
                flash(f"Cambios de habitación detectados: {room_change_count}", 'info')

                for change in result['room_changes'][:5]:  # Show max 5 details
                    status_parts = []
                    if change['customer_updated']:
                        status_parts.append('cliente actualizado')
                    else:
                        status_parts.append('cliente no encontrado')

                    if change['reservations_updated'] > 0:
                        status_parts.append(f"{change['reservations_updated']} reserva(s) actualizada(s)")

                    status_text = ', '.join(status_parts)
                    flash(f"  • {change['guest_name']}: {change['old_room']} → {change['new_room']} ({status_text})", 'info')

                if room_change_count > 5:
                    flash(f"  ... y {room_change_count - 5} cambio(s) más", 'info')

            # Show errors if any
            if result['errors']:
                error_count = len(result['errors'])
                if error_count <= 3:
                    for error in result['errors']:
                        flash(error, 'error')
                else:
                    flash(f"Se encontraron {error_count} errores durante la importación", 'error')

        except Exception as e:
            flash(f'Error al importar: {str(e)}', 'error')

        finally:
            # Clean up temp file (with retry for Windows file locking)
            for _ in range(3):
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if os.path.exists(temp_dir):
                        os.rmdir(temp_dir)
                    break
                except PermissionError:
                    time.sleep(0.1)

        return redirect(url_for('admin.hotel_guests'))

    # GET: Show import form
    return render_template('hotel_guests_import.html')


@admin_bp.route('/hotel-guests/<int:guest_id>')
@login_required
@permission_required('admin.hotel_guests.view')
def hotel_guest_detail(guest_id):
    """View hotel guest details."""
    guest = get_hotel_guest_by_id(guest_id)
    if not guest:
        flash('Huésped no encontrado', 'error')
        return redirect(url_for('admin.hotel_guests'))

    return render_template('hotel_guest_detail.html', guest=guest)


@admin_bp.route('/hotel-guests/<int:guest_id>/delete', methods=['POST'])
@login_required
@permission_required('admin.hotel_guests.import')
def hotel_guest_delete(guest_id):
    """Delete hotel guest record."""
    try:
        deleted = delete_hotel_guest(guest_id)
        if deleted:
            flash('Huésped eliminado correctamente', 'success')
        else:
            flash('Error al eliminar huésped', 'error')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('admin.hotel_guests'))


@admin_bp.route('/api/hotel-guests/preview', methods=['POST'])
@login_required
@permission_required('admin.hotel_guests.import')
def hotel_guests_preview():
    """Preview Excel file before import (AJAX endpoint)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save temporarily
    filename = secure_filename(file.filename)
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    file.save(temp_path)

    try:
        is_valid, error_msg, preview_data = validate_excel_file(temp_path)

        if not is_valid:
            return jsonify({'error': error_msg}), 400

        return jsonify(preview_data)

    finally:
        # Clean up temp file (with retry for Windows file locking)
        for _ in range(3):
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                break
            except PermissionError:
                time.sleep(0.1)
