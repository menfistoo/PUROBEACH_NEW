# PuroBeach - Beach Club Management System

Sistema profesional de gestion y reservas de beach club. Gestiona hamacas/balinesas, clientes internos (huespedes) y externos, reservas multi-dia, precios diferenciados, estados configurables, y mapa interactivo con disponibilidad en tiempo real.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
flask init-db --confirm

# 3. Create admin user
flask create-user admin admin@example.com --password

# 4. Run development server
python app.py
```

The app will be available at `http://localhost:5000`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Environment: development, production, test |
| `SECRET_KEY` | dev key | **Required in production** (min 32 chars) |
| `DATABASE_PATH` | `instance/beach_club.db` | SQLite database path |
| `PORT` | `5000` | Server port |
| `SESSION_TIMEOUT_HOURS` | `8` | Session expiration |

## Tech Stack

- **Backend:** Flask 3.1+, Python 3.11+, SQLite 3 (WAL mode)
- **Frontend:** Jinja2, Bootstrap 5, FontAwesome 6, vanilla JS ES6+
- **Auth:** Flask-Login, Flask-WTF CSRF, role-based permissions
- **Export:** openpyxl (Excel), ReportLab (PDF)

## Running Tests

```bash
python -m pytest tests/ -v
```

## Production Deployment

See `docker-compose.yml` and `nginx/` for Docker + Nginx + Gunicorn setup with Let's Encrypt SSL.

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development conventions and project structure
