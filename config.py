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
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF token expires after 1 hour
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.environ.get('SESSION_TIMEOUT_HOURS', 8))
    )

    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'png', 'jpg', 'jpeg'}

    # Pagination
    ITEMS_PER_PAGE = 20

    # Application settings
    APP_NAME = 'PuroBeach'
    APP_VERSION = '1.1.0'


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
    SESSION_COOKIE_SECURE = True  # Require HTTPS
    WTF_CSRF_SSL_STRICT = True

    # Override with strong secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")

    # Validate SECRET_KEY strength (minimum 32 characters)
    if len(SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters in production")

    # HTTPS preference for URL generation
    PREFERRED_URL_SCHEME = 'https'

    # Ensure DATABASE_PATH is explicitly set (not using default)
    DATABASE_PATH = os.environ.get('DATABASE_PATH')
    if not DATABASE_PATH:
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
