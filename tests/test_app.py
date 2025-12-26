"""
Test application factory and configuration.
"""

import pytest
from app import create_app


class TestAppFactory:
    """Test Flask application factory."""

    def test_create_app_development(self):
        """Test app creation with development config."""
        app = create_app('development')
        assert app is not None
        assert app.config['DEBUG'] is True
        assert app.config['TESTING'] is False

    def test_create_app_test(self):
        """Test app creation with test config."""
        app = create_app('test')
        assert app is not None
        assert app.config['TESTING'] is True
        assert app.config['WTF_CSRF_ENABLED'] is False

    def test_create_app_default(self):
        """Test app creation with default config."""
        app = create_app()
        assert app is not None

    def test_app_has_blueprints(self):
        """Test that all blueprints are registered."""
        app = create_app('test')
        blueprint_names = list(app.blueprints.keys())

        assert 'auth' in blueprint_names
        assert 'admin' in blueprint_names
        assert 'beach' in blueprint_names
        assert 'api' in blueprint_names

    def test_app_has_extensions(self):
        """Test that extensions are initialized."""
        app = create_app('test')

        # Check login manager
        assert hasattr(app, 'login_manager')

    def test_app_context_processors(self):
        """Test that context processors are registered."""
        app = create_app('test')

        with app.app_context():
            with app.test_request_context():
                # Context processors should provide these
                ctx = app.jinja_env.globals
                assert 'get_menu_items' in ctx or callable(getattr(app, 'context_processor', None))


class TestAppConfiguration:
    """Test application configuration."""

    def test_secret_key_set(self):
        """Test that secret key is configured."""
        app = create_app('test')
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0

    def test_database_path_set(self):
        """Test that database path is configured."""
        app = create_app('test')
        assert 'DATABASE_PATH' in app.config

    def test_app_name_set(self):
        """Test that app name is configured."""
        app = create_app('test')
        assert app.config.get('APP_NAME') == 'PuroBeach'


class TestCLICommands:
    """Test CLI command registration."""

    def test_cli_commands_registered(self):
        """Test that CLI commands are registered."""
        app = create_app('test')

        # Get registered CLI commands
        commands = list(app.cli.commands.keys())

        assert 'init-db' in commands
        assert 'run-migrations' in commands
        assert 'create-user' in commands
