"""
Flask extensions initialization.
Extensions are initialized here and then initialized with the app in app.py.
"""

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask-Login
login_manager = LoginManager()

# Initialize CSRF Protection
csrf = CSRFProtect()

# Initialize rate limiter (disabled during testing via app config)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

# Configure Login Manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'


@login_manager.user_loader
def load_user(user_id):
    """
    Load user by ID for Flask-Login.

    Args:
        user_id: The user ID as a string

    Returns:
        User object or None if not found
    """
    from models.user import get_user_by_id, User

    user_dict = get_user_by_id(int(user_id))
    if user_dict:
        return User(user_dict)
    return None
