# 🏗️ Architecture

## 🛠️ Tech Stack

- **Backend:** Flask 3.0+ (Python 3.11+), SQLite 3 (WAL mode)
- **Architecture:** Modular blueprints
- **Auth/Security:** Flask-Login, Flask-WTF CSRF, role-based permissions
- **Frontend:** Jinja2, Bootstrap 5, FontAwesome 6, JavaScript ES6+
- **Export:** openpyxl (Excel), ReportLab (PDF)

## 📂 Project Structure

```
beach_club/
├── app.py                      # Flask app factory
├── config.py                   # Configuration classes
├── extensions.py               # Flask extensions
├── database.py                 # Database connection & functions
├── blueprints/                 # Modular routes
│   ├── auth/                   # Authentication
│   ├── admin/                  # Users, roles, permissions
│   ├── beach/                  # Main beach club module
│   └── api/                    # REST API endpoints
├── models/                     # Database queries
├── utils/                      # Decorators, permissions, cache
├── templates/                  # Jinja2 templates
├── static/                     # CSS, JS, Images
└── docs/                       # Documentation
```

## 🗄️ Database Schema

### Core Tables
1. **users** - System users
2. **roles** - System and custom roles
3. **permissions** - Granular permissions
4. **beach_zones** - Hierarchical zones
5. **beach_furniture_types** - Hamaca, balinesa, etc.
6. **beach_furniture** - Individual items
7. **beach_reservations** - Main reservations
8. **beach_customers** - Interno/externo customers

*(See `Database/DATABASE_SCHEMA.md` for full details)*

## 📜 Architecture Decisions (ADRs)

### ADR-001: Blueprint Structure
Modular blueprints with sub-blueprints for related routes.

### ADR-002: Database Choice
SQLite with WAL mode for simple deployment.

### ADR-003: Bidirectional Preferences
Preferences sync between customers and reservations to "learn" from history.

### ADR-004: Feature Mapping
Preferences map to furniture features (e.g., `pref_sombra` -> `shaded`) for the suggestion algorithm.

### ADR-005: SVG Visual System
Furniture types define their own SVG representation (shape, color) for the map.

### ADR-006: Global State Colors
Reservation state colors are global (not per furniture type) to ensure consistency.

### ADR-007: Reservation Schema
Single `reservation_date` per record. Multi-day reservations use Parent/Child relationship.
