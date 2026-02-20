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

    # Register security headers
    register_security_headers(app)

    # Register CLI commands
    register_cli_commands(app)

    # Register context processors
    register_context_processors(app)

    # Register teardown handlers
    register_teardown_handlers(app)

    # Configure logging
    configure_logging(app)

    # Expire old waitlist entries on startup
    expire_waitlist_entries(app)

    return app


def initialize_extensions(app):
    """Initialize Flask extensions."""
    # Initialize Flask-Login
    login_manager.init_app(app)
    # Initialize CSRF Protection
    csrf.init_app(app)
    # Initialize rate limiter
    from extensions import limiter
    limiter.init_app(app)


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
    """Register error handlers with JSON support for API requests."""
    from flask import jsonify, request

    def _is_api_request() -> bool:
        """Check if current request expects a JSON response."""
        if '/api/' in request.path:
            return True
        if request.is_json:
            return True
        if request.accept_mimetypes.best == 'application/json':
            return True
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        return False

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        if _is_api_request():
            return jsonify({'success': False, 'error': 'Recurso no encontrado'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        # Rollback database on error
        db = g.get('db')
        if db:
            db.rollback()
        if _is_api_request():
            return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        if _is_api_request():
            return jsonify({
                'success': False,
                'error': 'No tiene permisos para realizar esta acción'
            }), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 errors."""
        if _is_api_request():
            return jsonify({'success': False, 'error': 'Solicitud inválida'}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 errors."""
        if _is_api_request():
            return jsonify({'success': False, 'error': 'Método no permitido'}), 405
        return render_template('errors/405.html'), 405


def register_security_headers(app):
    """Register security headers for all responses (non-debug mode only)."""

    @app.after_request
    def set_security_headers(response):
        """Add baseline security headers to every response."""
        if not app.debug:
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response


def register_cli_commands(app):
    """Register Flask CLI commands."""
    import re

    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        Returns (is_valid, error_message).
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        return True, ""

    @app.cli.command('init-db')
    @click.option('--confirm', is_flag=True, help='Confirmar inicialización (requerido)')
    def init_db_command(confirm):
        """Initialize database with schema and seed data."""
        if not confirm:
            click.echo('ADVERTENCIA: Este comando reinicializa la base de datos.')
            click.echo('Todos los datos existentes serán eliminados.')
            click.echo('')
            click.echo('Para continuar, ejecute: flask init-db --confirm')
            raise SystemExit(1)

        click.echo('Initializing database...')
        with app.app_context():
            try:
                init_db()
                app.logger.info('Database initialized via CLI')
                click.echo('Database initialized successfully!')
            except Exception as e:
                app.logger.error(f'Database initialization failed: {e}')
                click.echo(f'Error: {e}', err=True)
                raise SystemExit(1)

    @app.cli.command('run-migrations')
    def run_migrations_command():
        """Run all pending database migrations."""
        from database.migrations import run_all_migrations

        click.echo('Running migrations...')
        with app.app_context():
            result = run_all_migrations()

            for name, success, status in result['results']:
                if success:
                    app.logger.info(f'Migration {name}: {status}')
                else:
                    app.logger.error(f'Migration {name} failed: {status}')

        if result['failed'] > 0:
            app.logger.warning(f"Migrations completed with {result['failed']} failures")
            click.echo(f"Migrations complete with {result['failed']} failures!", err=True)
        else:
            app.logger.info('All migrations completed successfully')
            click.echo('Migrations complete!')

    @app.cli.command('create-user')
    @click.argument('username')
    @click.argument('email')
    @click.password_option()
    def create_user_command(username, email, password):
        """Create a new user with validation."""
        from models.user import create_user
        from models.role import get_role_by_name

        # Validate email format
        if not validate_email(email):
            click.echo('Error: Invalid email format', err=True)
            raise SystemExit(1)

        # Validate password strength
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            click.echo(f'Error: {error_msg}', err=True)
            raise SystemExit(1)

        # Validate username (alphanumeric, 3-50 chars)
        if not username or len(username) < 3 or len(username) > 50:
            click.echo('Error: Username must be 3-50 characters', err=True)
            raise SystemExit(1)

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
                app.logger.info(f'User created via CLI: {username} (ID: {user_id})')
                click.echo(f'User created successfully! ID: {user_id}')
            except Exception as e:
                app.logger.error(f'Failed to create user {username}: {e}')
                click.echo(f'Error creating user: {str(e)}', err=True)
                raise SystemExit(1)


def register_context_processors(app):
    """Register template context processors."""

    @app.context_processor
    def utility_processor():
        """Inject utility functions into templates."""
        from utils.permissions import get_menu_items
        from utils.datetime_helpers import get_now
        from flask import url_for

        app_version = app.config.get('APP_VERSION', '1.0.0')

        def versioned_static(filename: str) -> str:
            """Generate versioned static file URL for cache busting."""
            return url_for('static', filename=filename) + '?v=' + app_version

        return {
            'get_menu_items': get_menu_items,
            'current_year': get_now().year,
            'app_name': app.config.get('APP_NAME', 'PuroBeach'),
            'app_version': app_version,
            'versioned_static': versioned_static,
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
        except (ValueError, TypeError, AttributeError):
            return date_str

    @app.template_filter('from_json')
    def from_json_filter(json_str):
        """Parse JSON string into Python object."""
        import json
        if not json_str:
            return {}
        try:
            return json.loads(json_str) if isinstance(json_str, str) else json_str
        except (ValueError, TypeError, AttributeError):
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


def expire_waitlist_entries(app):
    """
    Expire old waitlist entries on startup.
    Called during app initialization to clean up past entries.
    """
    try:
        with app.app_context():
            from models.waitlist import expire_old_entries
            count = expire_old_entries()
            if count > 0:
                app.logger.info(f'Expired {count} old waitlist entries')
    except Exception as e:
        # Don't crash the app if waitlist cleanup fails
        app.logger.warning(f'Could not expire waitlist entries: {e}')


# Create application instance for development server
if __name__ == '__main__':
    app = create_app()
    # host='0.0.0.0' allows access from other devices on the network
    # Port can be set via PORT environment variable (default: 5000)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
