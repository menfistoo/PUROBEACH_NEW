"""
PuroBeach - Beach Club Management System
Flask application factory and initialization
"""

import os
import sys
import click
import logging
from flask import Flask, render_template, g
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration
from config import config

# Import extensions
from extensions import login_manager, csrf

# Import database functions
from database import close_db, init_db, get_db


def create_app(config_name=None):
    """
    Application factory for Flask app.

    Args:
        config_name: Configuration name ('development', 'production', 'test')

    Returns:
        Flask application instance
    """
    # Determine config
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    initialize_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    # Register context processors
    register_context_processors(app)

    # Register teardown handlers
    register_teardown_handlers(app)

    # Configure logging
    configure_logging(app)

    return app


def initialize_extensions(app):
    """Initialize Flask extensions."""
    # Initialize Flask-Login
    login_manager.init_app(app)
    # Initialize CSRF Protection
    csrf.init_app(app)


def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints
    from blueprints.auth.routes import auth_bp
    from blueprints.admin.routes import admin_bp
    from blueprints.beach import beach_bp
    from blueprints.api.routes import api_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(beach_bp, url_prefix='/beach')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Set default route
    @app.route('/')
    def index():
        """Redirect to beach map."""
        from flask import redirect, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for('beach.map'))
        return redirect(url_for('auth.login'))


def register_error_handlers(app):
    """Register error handlers."""

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        # Rollback database on error
        db = g.get('db')
        if db:
            db.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        return render_template('errors/403.html'), 403


def register_cli_commands(app):
    """Register Flask CLI commands."""

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize database with schema and seed data."""
        click.echo('Initializing database...')
        with app.app_context():
            init_db()
        click.echo('Database initialized successfully!')

    @app.cli.command('create-user')
    @click.argument('username')
    @click.argument('email')
    @click.password_option()
    def create_user_command(username, email, password):
        """Create a new user."""
        from models.user import create_user
        from models.role import get_role_by_name

        with app.app_context():
            # Get admin role
            admin_role = get_role_by_name('admin')

            try:
                user_id = create_user(
                    username=username,
                    email=email,
                    password=password,
                    role_id=admin_role['id']
                )
                click.echo(f'User created successfully! ID: {user_id}')
            except Exception as e:
                click.echo(f'Error creating user: {str(e)}', err=True)


def register_context_processors(app):
    """Register template context processors."""

    @app.context_processor
    def utility_processor():
        """Inject utility functions into templates."""
        from utils.permissions import get_menu_items
        from datetime import datetime

        return {
            'get_menu_items': get_menu_items,
            'current_year': datetime.now().year,
            'app_name': app.config.get('APP_NAME', 'PuroBeach'),
            'app_version': app.config.get('APP_VERSION', '1.0.0')
        }

    # Add custom template filters
    @app.template_filter('format_date')
    def format_date_filter(date_str, format='%d/%m/%Y'):
        """Format date string."""
        from datetime import datetime
        if not date_str:
            return ''
        try:
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date_obj = date_str
            return date_obj.strftime(format)
        except:
            return date_str

    @app.template_filter('from_json')
    def from_json_filter(json_str):
        """Parse JSON string into Python object."""
        import json
        if not json_str:
            return {}
        try:
            return json.loads(json_str) if isinstance(json_str, str) else json_str
        except:
            return {}


def register_teardown_handlers(app):
    """Register teardown handlers."""

    @app.teardown_appcontext
    def teardown_db(error):
        """Close database connection at end of request."""
        close_db(error)


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = logging.FileHandler('logs/purobeach.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('PuroBeach startup')
    else:
        # Development logging
        app.logger.setLevel(logging.DEBUG)


# Create application instance for development server
if __name__ == '__main__':
    app = create_app()
    # host='0.0.0.0' allows access from other devices on the network
    app.run(host='0.0.0.0', debug=True)
