"""
Authentication routes: login, logout, profile.
Handles user authentication and profile management.
"""

from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from blueprints.auth.forms import LoginForm, ProfileForm, ChangePasswordForm
from models.user import get_user_by_username, update_last_login, update_user, update_password, check_password
from utils.messages import MESSAGES
from utils.permissions import cache_user_permissions

auth_bp = Blueprint('auth', __name__, template_folder='../../templates/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route with form handling.

    GET: Display login form
    POST: Process login credentials
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('beach.map'))

    form = LoginForm()

    if form.validate_on_submit():
        # Get user by username
        user_dict = get_user_by_username(form.username.data)

        # Check credentials
        if user_dict is None or not check_password(user_dict, form.password.data):
            flash(MESSAGES['invalid_credentials'], 'error')
            return redirect(url_for('auth.login'))

        # Check if user is active
        if not user_dict.get('active'):
            flash('Su cuenta ha sido desactivada. Contacte al administrador.', 'error')
            return redirect(url_for('auth.login'))

        # Create User object for Flask-Login
        from models.user import User
        user = User(user_dict)

        # Log user in
        login_user(user, remember=form.remember_me.data)

        # Update last login timestamp
        update_last_login(user.id)

        # Cache user permissions in session
        cache_user_permissions(user.id)

        # Flash success message
        flash(MESSAGES['login_success'].format(name=user.full_name or user.username), 'success')

        # Redirect to next page or default
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('beach.map')

        return redirect(next_page)

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout current user."""
    logout_user()
    flash(MESSAGES['logout_success'], 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile."""
    from models.user import get_user_by_id

    user_dict = get_user_by_id(current_user.id)

    return render_template('profile.html', user=user_dict)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Edit user profile."""
    from models.user import get_user_by_id

    form = ProfileForm()

    if form.validate_on_submit():
        # Update user profile
        updated = update_user(
            current_user.id,
            email=form.email.data,
            full_name=form.full_name.data,
            theme_preference=form.theme_preference.data
        )

        if updated:
            flash(MESSAGES['profile_updated'], 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Error al actualizar el perfil', 'error')

    # Pre-populate form
    user_dict = get_user_by_id(current_user.id)
    if request.method == 'GET':
        form.email.data = user_dict['email']
        form.full_name.data = user_dict['full_name']
        form.theme_preference.data = user_dict.get('theme_preference', 'light')

    return render_template('profile_edit.html', form=form, user=user_dict)


@auth_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    from models.user import get_user_by_id

    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Verify current password
        user_dict = get_user_by_id(current_user.id)
        if not check_password(user_dict, form.current_password.data):
            flash('La contraseña actual es incorrecta', 'error')
            return render_template('change_password.html', form=form)

        # Update password
        updated = update_password(current_user.id, form.new_password.data)

        if updated:
            flash(MESSAGES['password_updated'], 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Error al cambiar la contraseña', 'error')

    return render_template('change_password.html', form=form)
