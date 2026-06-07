"""
Flask application configuration classes.
Provides configuration for development, production, and testing environments.
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class with common settings."""

    # Secret key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'instance/beach_club.db'

    # SQLAlchemy disabled (using raw SQLite)
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings
    WTF_CSRF_ENABLED = True
    # Tie the CSRF token to the session lifetime instead of expiring after 1h.
    # Ops tablets keep the map open all shift; a 1h limit caused spurious 400s
    # ("CSRF token expired") on long-open pages.
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    # Session lifetime covers a full shift, and rolls forward on each request so an
    # active user is never logged out mid-shift.
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.environ.get('SESSION_TIMEOUT_HOURS', 12))
    )
    SESSION_REFRESH_EACH_REQUEST = True
    # Flask-Login "remember me" cookie: persists across browser/tablet sleeps and
    # WiFi drops so the device silently re-authenticates instead of getting 401s and
    # bouncing staff to the login screen.
    REMEMBER_COOKIE_DURATION = timedelta(
        days=int(os.environ.get('REMEMBER_COOKIE_DAYS', 7))
    )
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False  # Overridden in production

    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'}

    # Pagination
    ITEMS_PER_PAGE = 20

    # Timezone
    TIMEZONE = 'Europe/Madrid'

    # Application settings
    APP_NAME = 'PuroBeach'
    APP_VERSION = '1.2.3'


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    WTF_CSRF_SSL_STRICT = SESSION_COOKIE_SECURE

    SECRET_KEY = os.environ.get('SECRET_KEY') or Config.SECRET_KEY
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or Config.DATABASE_PATH

    # URL scheme preference (follows SESSION_COOKIE_SECURE setting)
    PREFERRED_URL_SCHEME = 'https' if SESSION_COOKIE_SECURE else 'http'

    @classmethod
    def validate(cls) -> None:
        """Validate that required production environment variables are set."""
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if not os.environ.get('DATABASE_PATH'):
            raise ValueError("DATABASE_PATH environment variable must be set in production")


class TestConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for tests
    RATELIMIT_ENABLED = False  # Disable rate limiting for tests
    DATABASE_PATH = os.environ.get('DATABASE_PATH', ':memory:')
    SECRET_KEY = 'test-secret-key'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
    'default': DevelopmentConfig
}
