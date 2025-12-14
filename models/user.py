"""
User model and data access functions.
Handles user authentication, CRUD operations, and Flask-Login integration.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from datetime import datetime


class User:
    """
    User class for Flask-Login integration.
    Wraps database row dictionary with required Flask-Login properties.
    """

    def __init__(self, user_dict):
        """
        Initialize User from database row.

        Args:
            user_dict: Dictionary with user data from database
        """
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.email = user_dict['email']
        self.full_name = user_dict['full_name']
        self.role_id = user_dict['role_id']
        self.active = user_dict['active']
        self.theme_preference = user_dict.get('theme_preference', 'light')
        self.created_at = user_dict['created_at']
        self.last_login = user_dict.get('last_login')

    @property
    def is_authenticated(self):
        """Required by Flask-Login."""
        return True

    @property
    def is_active(self):
        """Required by Flask-Login."""
        return self.active == 1

    @property
    def is_anonymous(self):
        """Required by Flask-Login."""
        return False

    def get_id(self):
        """Required by Flask-Login. Returns user ID as unicode string."""
        return str(self.id)


def get_user_by_id(user_id: int) -> dict:
    """
    Get user by ID.

    Args:
        user_id: User ID

    Returns:
        User dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT u.*, r.name as role_name, r.display_name as role_display_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict:
    """
    Get user by username.

    Args:
        username: Username to search for

    Returns:
        User dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT u.*, r.name as role_name, r.display_name as role_display_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.username = ?
    ''', (username,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> dict:
    """
    Get user by email.

    Args:
        email: Email to search for

    Returns:
        User dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT u.*, r.name as role_name, r.display_name as role_display_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.email = ?
    ''', (email,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_users(active_only: bool = True) -> list:
    """
    Get all users.

    Args:
        active_only: If True, only return active users

    Returns:
        List of user dicts
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT u.*, r.name as role_name, r.display_name as role_display_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
    '''

    if active_only:
        query += ' WHERE u.active = 1'

    query += ' ORDER BY u.created_at DESC'

    cursor.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def create_user(username: str, email: str, password: str, full_name: str = None, role_id: int = None) -> int:
    """
    Create new user with hashed password.

    Args:
        username: Unique username
        email: Unique email
        password: Plain text password (will be hashed)
        full_name: User's full name
        role_id: Role ID to assign

    Returns:
        New user ID

    Raises:
        sqlite3.IntegrityError if username or email already exists
    """
    db = get_db()
    password_hash = generate_password_hash(password)

    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, email, password_hash, full_name, role_id))

    db.commit()
    return cursor.lastrowid


def update_user(user_id: int, **kwargs) -> bool:
    """
    Update user fields.

    Args:
        user_id: User ID to update
        **kwargs: Fields to update (email, full_name, role_id, active, theme_preference)

    Returns:
        True if updated successfully
    """
    db = get_db()

    # Build dynamic update query
    allowed_fields = ['email', 'full_name', 'role_id', 'active', 'theme_preference']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    # Add updated_at timestamp
    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(user_id)

    query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def update_password(user_id: int, new_password: str) -> bool:
    """
    Update user password.

    Args:
        user_id: User ID
        new_password: New plain text password (will be hashed)

    Returns:
        True if updated successfully
    """
    db = get_db()
    password_hash = generate_password_hash(new_password)

    cursor = db.cursor()
    cursor.execute('''
        UPDATE users
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (password_hash, user_id))

    db.commit()
    return cursor.rowcount > 0


def delete_user(user_id: int) -> bool:
    """
    Soft delete user (set active = 0).

    Args:
        user_id: User ID to delete

    Returns:
        True if deleted successfully
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE users SET active = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (user_id,))

    db.commit()
    return cursor.rowcount > 0


def update_last_login(user_id: int) -> None:
    """
    Update last login timestamp.

    Args:
        user_id: User ID
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE users SET last_login = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (user_id,))
    db.commit()


def check_password(user_dict: dict, password: str) -> bool:
    """
    Verify password against stored hash.

    Args:
        user_dict: User dictionary with password_hash
        password: Plain text password to check

    Returns:
        True if password matches
    """
    return check_password_hash(user_dict['password_hash'], password)
