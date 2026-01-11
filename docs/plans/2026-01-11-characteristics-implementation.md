# Características System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded preferences with a unified, configurable "Características" system for matching furniture to reservations.

**Architecture:** New `beach_characteristics` table with M2M junction tables for furniture, reservations, and customers. Direct ID matching in suggestion algorithm (no hardcoded mapping). Migration preserves existing preference data.

**Tech Stack:** Flask, SQLite, Jinja2, Bootstrap 5, FontAwesome 6

---

## Task 1: Database Schema - New Tables

**Files:**
- Modify: `database/schema.py`

**Step 1: Add new tables to schema.py**

Find the `beach_preferences` table creation (around line 282-300) and add the new tables **after** `beach_customer_preferences`:

```python
    # Características system (unified preferences + features)
    db.execute('''
        CREATE TABLE beach_characteristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            color TEXT DEFAULT '#D4AF37',
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('''
        CREATE TABLE beach_furniture_characteristics (
            furniture_id INTEGER REFERENCES beach_furniture(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (furniture_id, characteristic_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_reservation_characteristics (
            reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (reservation_id, characteristic_id)
        )
    ''')

    db.execute('''
        CREATE TABLE beach_customer_characteristics (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, characteristic_id)
        )
    ''')
```

**Step 2: Add tables to drop_tables function**

In `drop_tables()`, add after `beach_customer_preferences`:
```python
        'beach_customer_characteristics',
        'beach_reservation_characteristics',
        'beach_furniture_characteristics',
        'beach_characteristics',
```

**Step 3: Verify syntax**

Run: `python -c "from database.schema import create_tables; print('Schema OK')"`
Expected: `Schema OK`

**Step 4: Commit**

```bash
git add database/schema.py
git commit -m "feat(db): add characteristics tables schema"
```

---

## Task 2: Database Migration Script

**Files:**
- Create: `migrations/migrate_preferences_to_characteristics.py`

**Step 1: Create migration script**

```python
"""
Migration: Convert preferences to características system.

Run: python migrations/migrate_preferences_to_characteristics.py
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db


def check_tables_exist(conn):
    """Check if old tables exist."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_preferences'
    """)
    return cursor.fetchone() is not None


def check_new_tables_exist(conn):
    """Check if new tables already exist."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='beach_characteristics'
    """)
    return cursor.fetchone() is not None


def create_new_tables(conn):
    """Create new características tables."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_characteristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT,
            color TEXT DEFAULT '#D4AF37',
            active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_furniture_characteristics (
            furniture_id INTEGER REFERENCES beach_furniture(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (furniture_id, characteristic_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_reservation_characteristics (
            reservation_id INTEGER REFERENCES beach_reservations(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (reservation_id, characteristic_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS beach_customer_characteristics (
            customer_id INTEGER REFERENCES beach_customers(id) ON DELETE CASCADE,
            characteristic_id INTEGER REFERENCES beach_characteristics(id) ON DELETE CASCADE,
            PRIMARY KEY (customer_id, characteristic_id)
        )
    ''')
    conn.commit()
    print("Created new tables")


def migrate_preferences_to_characteristics(conn):
    """Migrate beach_preferences to beach_characteristics."""
    # Map old preference codes to cleaner codes (remove 'pref_' prefix)
    cursor = conn.execute("""
        SELECT id, code, name, description, icon, active
        FROM beach_preferences
    """)
    preferences = cursor.fetchall()

    if not preferences:
        print("No preferences to migrate")
        return {}

    code_mapping = {}  # old_code -> new_id

    for pref in preferences:
        old_id, old_code, name, description, icon, active = pref

        # Clean up code: remove 'pref_' prefix if present
        new_code = old_code.replace('pref_', '') if old_code.startswith('pref_') else old_code

        # Assign colors based on typical use
        color = '#D4AF37'  # Default gold
        if 'sombra' in new_code:
            color = '#4A7C59'  # Green for shade
        elif 'primera' in new_code or 'mar' in new_code:
            color = '#1A3A5C'  # Ocean blue
        elif 'vip' in new_code:
            color = '#D4AF37'  # Gold for VIP
        elif 'bar' in new_code:
            color = '#C1444F'  # Red for bar
        elif 'familia' in new_code:
            color = '#E5A33D'  # Orange for family
        elif 'tranquil' in new_code:
            color = '#6B7280'  # Gray for quiet

        conn.execute("""
            INSERT INTO beach_characteristics (code, name, description, icon, color, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (new_code, name, description, icon, color, active))

        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        code_mapping[old_code] = new_id
        print(f"  Migrated preference: {old_code} -> {new_code} (id={new_id})")

    conn.commit()
    return code_mapping


def migrate_customer_preferences(conn, code_mapping):
    """Migrate beach_customer_preferences to beach_customer_characteristics."""
    cursor = conn.execute("""
        SELECT cp.customer_id, p.code
        FROM beach_customer_preferences cp
        JOIN beach_preferences p ON cp.preference_id = p.id
    """)
    records = cursor.fetchall()

    migrated = 0
    for customer_id, old_code in records:
        new_id = code_mapping.get(old_code)
        if new_id:
            conn.execute("""
                INSERT OR IGNORE INTO beach_customer_characteristics (customer_id, characteristic_id)
                VALUES (?, ?)
            """, (customer_id, new_id))
            migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} customer preferences")


def migrate_reservation_preferences(conn, code_mapping):
    """Migrate reservation preferences from CSV column to junction table."""
    cursor = conn.execute("""
        SELECT id, preferences FROM beach_reservations
        WHERE preferences IS NOT NULL AND preferences != ''
    """)
    reservations = cursor.fetchall()

    migrated = 0
    for res_id, prefs_csv in reservations:
        codes = [c.strip() for c in prefs_csv.split(',') if c.strip()]
        for code in codes:
            new_id = code_mapping.get(code)
            if new_id:
                conn.execute("""
                    INSERT OR IGNORE INTO beach_reservation_characteristics
                    (reservation_id, characteristic_id)
                    VALUES (?, ?)
                """, (res_id, new_id))
                migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} reservation preferences")


def migrate_furniture_features(conn):
    """Migrate furniture.features CSV to junction table."""
    cursor = conn.execute("""
        SELECT id, features FROM beach_furniture
        WHERE features IS NOT NULL AND features != ''
    """)
    furniture_rows = cursor.fetchall()

    migrated = 0
    for furn_id, features_csv in furniture_rows:
        codes = [c.strip() for c in features_csv.split(',') if c.strip()]
        for code in codes:
            # Look up characteristic by code
            char_cursor = conn.execute("""
                SELECT id FROM beach_characteristics WHERE code = ?
            """, (code,))
            char_row = char_cursor.fetchone()
            if char_row:
                conn.execute("""
                    INSERT OR IGNORE INTO beach_furniture_characteristics
                    (furniture_id, characteristic_id)
                    VALUES (?, ?)
                """, (furn_id, char_row[0]))
                migrated += 1

    conn.commit()
    print(f"  Migrated {migrated} furniture features")


def run_migration():
    """Run the full migration."""
    print("=" * 60)
    print("MIGRATION: Preferences -> Características")
    print("=" * 60)

    with get_db() as conn:
        # Check if migration needed
        if not check_tables_exist(conn):
            print("ERROR: beach_preferences table not found. Nothing to migrate.")
            return False

        if check_new_tables_exist(conn):
            # Check if already has data
            count = conn.execute("SELECT COUNT(*) FROM beach_characteristics").fetchone()[0]
            if count > 0:
                print(f"WARNING: beach_characteristics already has {count} records.")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Migration cancelled.")
                    return False

        # Step 1: Create new tables
        print("\n1. Creating new tables...")
        create_new_tables(conn)

        # Step 2: Migrate preferences
        print("\n2. Migrating preferences to características...")
        code_mapping = migrate_preferences_to_characteristics(conn)

        # Step 3: Migrate customer preferences
        print("\n3. Migrating customer preferences...")
        migrate_customer_preferences(conn, code_mapping)

        # Step 4: Migrate reservation preferences
        print("\n4. Migrating reservation preferences...")
        migrate_reservation_preferences(conn, code_mapping)

        # Step 5: Migrate furniture features
        print("\n5. Migrating furniture features...")
        migrate_furniture_features(conn)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Verify data: SELECT * FROM beach_characteristics;")
        print("  2. Test the application")
        print("  3. After confirming success, run cleanup migration")

        return True


if __name__ == '__main__':
    run_migration()
```

**Step 2: Test migration script syntax**

Run: `python -c "import migrations.migrate_preferences_to_characteristics; print('Script OK')"`
Expected: `Script OK`

**Step 3: Commit**

```bash
git add migrations/migrate_preferences_to_characteristics.py
git commit -m "feat(migration): add preferences to características migration script"
```

---

## Task 3: Characteristic Model - CRUD Operations

**Files:**
- Create: `models/characteristic.py`

**Step 1: Create the model file**

```python
"""
Characteristic data access functions.
CRUD operations for the unified características system.
"""

from database import get_db


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_all_characteristics(active_only: bool = True) -> list:
    """
    Get all characteristics.

    Args:
        active_only: If True, only return active characteristics

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        query = '''
            SELECT c.*,
                   (SELECT COUNT(*) FROM beach_furniture_characteristics
                    WHERE characteristic_id = c.id) as furniture_count,
                   (SELECT COUNT(*) FROM beach_reservation_characteristics
                    WHERE characteristic_id = c.id) as reservation_count,
                   (SELECT COUNT(*) FROM beach_customer_characteristics
                    WHERE characteristic_id = c.id) as customer_count
            FROM beach_characteristics c
        '''

        if active_only:
            query += ' WHERE c.active = 1'

        query += ' ORDER BY c.display_order, c.name'

        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def get_characteristic_by_id(characteristic_id: int) -> dict | None:
    """
    Get characteristic by ID.

    Args:
        characteristic_id: Characteristic ID

    Returns:
        Characteristic dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.execute(
            'SELECT * FROM beach_characteristics WHERE id = ?',
            (characteristic_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_characteristic_by_code(code: str) -> dict | None:
    """
    Get characteristic by code.

    Args:
        code: Characteristic code

    Returns:
        Characteristic dict or None if not found
    """
    with get_db() as conn:
        cursor = conn.execute(
            'SELECT * FROM beach_characteristics WHERE code = ?',
            (code,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# =============================================================================
# CREATE OPERATIONS
# =============================================================================

def create_characteristic(
    code: str,
    name: str,
    description: str = None,
    icon: str = None,
    color: str = '#D4AF37'
) -> int:
    """
    Create new characteristic.

    Args:
        code: Unique characteristic code (snake_case)
        name: Display name
        description: Description text
        icon: FontAwesome icon class
        color: Hex color for UI display

    Returns:
        New characteristic ID

    Raises:
        ValueError: If code already exists
    """
    existing = get_characteristic_by_code(code)
    if existing:
        raise ValueError(f'Ya existe una caracteristica con el codigo "{code}"')

    with get_db() as conn:
        # Get next display_order
        cursor = conn.execute(
            'SELECT COALESCE(MAX(display_order), 0) + 1 FROM beach_characteristics'
        )
        next_order = cursor.fetchone()[0]

        cursor = conn.execute('''
            INSERT INTO beach_characteristics
            (code, name, description, icon, color, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, description, icon, color, next_order))

        conn.commit()
        return cursor.lastrowid


# =============================================================================
# UPDATE OPERATIONS
# =============================================================================

def update_characteristic(characteristic_id: int, **kwargs) -> bool:
    """
    Update characteristic fields.

    Args:
        characteristic_id: Characteristic ID to update
        **kwargs: Fields to update (name, description, icon, color, active)

    Returns:
        True if updated successfully
    """
    allowed_fields = ['name', 'description', 'icon', 'color', 'active', 'display_order']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(characteristic_id)
    query = f'UPDATE beach_characteristics SET {", ".join(updates)} WHERE id = ?'

    with get_db() as conn:
        cursor = conn.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def reorder_characteristics(ordered_ids: list) -> bool:
    """
    Reorder characteristics by setting display_order.

    Args:
        ordered_ids: List of characteristic IDs in desired order

    Returns:
        True if reordered successfully
    """
    with get_db() as conn:
        for order, char_id in enumerate(ordered_ids):
            conn.execute(
                'UPDATE beach_characteristics SET display_order = ? WHERE id = ?',
                (order, char_id)
            )
        conn.commit()
        return True


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

def delete_characteristic(characteristic_id: int, hard: bool = False) -> bool:
    """
    Delete characteristic.

    Args:
        characteristic_id: Characteristic ID to delete
        hard: If True, permanently delete. If False, soft delete (set active=0)

    Returns:
        True if deleted successfully
    """
    with get_db() as conn:
        if hard:
            cursor = conn.execute(
                'DELETE FROM beach_characteristics WHERE id = ?',
                (characteristic_id,)
            )
        else:
            cursor = conn.execute(
                'UPDATE beach_characteristics SET active = 0 WHERE id = ?',
                (characteristic_id,)
            )
        conn.commit()
        return cursor.rowcount > 0
```

**Step 2: Verify syntax**

Run: `python -c "from models.characteristic import get_all_characteristics; print('Model OK')"`
Expected: `Model OK`

**Step 3: Commit**

```bash
git add models/characteristic.py
git commit -m "feat(models): add characteristic CRUD operations"
```

---

## Task 4: Characteristic Assignments Model

**Files:**
- Create: `models/characteristic_assignments.py`

**Step 1: Create the assignments model**

```python
"""
Characteristic assignment functions.
Handles assigning characteristics to furniture, reservations, and customers.
"""

from database import get_db


# =============================================================================
# FURNITURE CHARACTERISTICS
# =============================================================================

def get_furniture_characteristics(furniture_id: int) -> list:
    """
    Get characteristics assigned to a furniture item.

    Args:
        furniture_id: Furniture ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_furniture_characteristics fc ON c.id = fc.characteristic_id
            WHERE fc.furniture_id = ?
            ORDER BY c.display_order, c.name
        ''', (furniture_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_furniture_characteristic_ids(furniture_id: int) -> list[int]:
    """
    Get characteristic IDs assigned to a furniture item.

    Args:
        furniture_id: Furniture ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_furniture_characteristics
            WHERE furniture_id = ?
        ''', (furniture_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_furniture_characteristics(furniture_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set characteristics for a furniture item (replaces existing).

    Args:
        furniture_id: Furniture ID
        characteristic_ids: List of characteristic IDs to assign

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_furniture_characteristics WHERE furniture_id = ?',
            (furniture_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_furniture_characteristics (furniture_id, characteristic_id)
                VALUES (?, ?)
            ''', (furniture_id, char_id))

        conn.commit()
        return True


# =============================================================================
# RESERVATION CHARACTERISTICS
# =============================================================================

def get_reservation_characteristics(reservation_id: int) -> list:
    """
    Get characteristics requested by a reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_reservation_characteristics rc ON c.id = rc.characteristic_id
            WHERE rc.reservation_id = ?
            ORDER BY c.display_order, c.name
        ''', (reservation_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_reservation_characteristic_ids(reservation_id: int) -> list[int]:
    """
    Get characteristic IDs requested by a reservation.

    Args:
        reservation_id: Reservation ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_reservation_characteristics
            WHERE reservation_id = ?
        ''', (reservation_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_reservation_characteristics(reservation_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set characteristics for a reservation (replaces existing).

    Args:
        reservation_id: Reservation ID
        characteristic_ids: List of characteristic IDs to request

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_reservation_characteristics WHERE reservation_id = ?',
            (reservation_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_reservation_characteristics (reservation_id, characteristic_id)
                VALUES (?, ?)
            ''', (reservation_id, char_id))

        conn.commit()
        return True


# =============================================================================
# CUSTOMER CHARACTERISTICS (DEFAULT PREFERENCES)
# =============================================================================

def get_customer_characteristics(customer_id: int) -> list:
    """
    Get default characteristics for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic dicts
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT c.*
            FROM beach_characteristics c
            JOIN beach_customer_characteristics cc ON c.id = cc.characteristic_id
            WHERE cc.customer_id = ?
            ORDER BY c.display_order, c.name
        ''', (customer_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_customer_characteristic_ids(customer_id: int) -> list[int]:
    """
    Get default characteristic IDs for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of characteristic IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT characteristic_id
            FROM beach_customer_characteristics
            WHERE customer_id = ?
        ''', (customer_id,))
        return [row['characteristic_id'] for row in cursor.fetchall()]


def set_customer_characteristics(customer_id: int, characteristic_ids: list[int]) -> bool:
    """
    Set default characteristics for a customer (replaces existing).

    Args:
        customer_id: Customer ID
        characteristic_ids: List of characteristic IDs

    Returns:
        True if successful
    """
    with get_db() as conn:
        # Remove existing
        conn.execute(
            'DELETE FROM beach_customer_characteristics WHERE customer_id = ?',
            (customer_id,)
        )

        # Add new
        for char_id in characteristic_ids:
            conn.execute('''
                INSERT INTO beach_customer_characteristics (customer_id, characteristic_id)
                VALUES (?, ?)
            ''', (customer_id, char_id))

        conn.commit()
        return True


# =============================================================================
# SCORING (FOR SUGGESTION ALGORITHM)
# =============================================================================

def score_characteristic_match(furniture_id: int, requested_ids: list[int]) -> dict:
    """
    Calculate how well furniture matches requested characteristics.

    Args:
        furniture_id: Furniture ID to score
        requested_ids: List of characteristic IDs requested

    Returns:
        dict: {
            'score': float (0.0 to 1.0),
            'matched': list of matched characteristic IDs,
            'missing': list of missing characteristic IDs
        }
    """
    if not requested_ids:
        return {'score': 1.0, 'matched': [], 'missing': []}

    furniture_ids = set(get_furniture_characteristic_ids(furniture_id))
    requested_set = set(requested_ids)

    matched = list(furniture_ids & requested_set)
    missing = list(requested_set - furniture_ids)

    score = len(matched) / len(requested_ids) if requested_ids else 1.0

    return {
        'score': score,
        'matched': matched,
        'missing': missing
    }
```

**Step 2: Verify syntax**

Run: `python -c "from models.characteristic_assignments import get_furniture_characteristics; print('Assignments OK')"`
Expected: `Assignments OK`

**Step 3: Commit**

```bash
git add models/characteristic_assignments.py
git commit -m "feat(models): add characteristic assignment functions"
```

---

## Task 5: Admin Routes - Characteristics Configuration

**Files:**
- Create: `blueprints/beach/routes/config/characteristics.py`
- Modify: `blueprints/beach/routes/config/__init__.py`

**Step 1: Create the characteristics routes**

```python
"""
Characteristics configuration routes.
Admin CRUD for the unified características system.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from utils.decorators import permission_required


def register_routes(bp):
    """Register characteristic routes on the blueprint."""

    @bp.route('/characteristics')
    @login_required
    @permission_required('beach.characteristics.view')
    def characteristics():
        """List all characteristics."""
        from models.characteristic import get_all_characteristics

        show_inactive = request.args.get('show_inactive') == '1'
        all_chars = get_all_characteristics(active_only=not show_inactive)

        return render_template(
            'beach/config/characteristics.html',
            characteristics=all_chars,
            show_inactive=show_inactive
        )

    @bp.route('/characteristics/create', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.characteristics.manage')
    def characteristics_create():
        """Create new characteristic."""
        from models.characteristic import create_characteristic

        if request.method == 'POST':
            code = request.form.get('code', '').strip().lower().replace(' ', '_')
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            color = request.form.get('color', '#D4AF37').strip()

            if not code or not name:
                flash('Codigo y nombre son obligatorios', 'error')
                return redirect(url_for('beach.beach_config.characteristics_create'))

            try:
                create_characteristic(
                    code=code,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    color=color
                )
                flash('Caracteristica creada correctamente', 'success')
                return redirect(url_for('beach.beach_config.characteristics'))

            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error al crear: {str(e)}', 'error')

        return render_template(
            'beach/config/characteristic_form.html',
            characteristic=None,
            mode='create'
        )

    @bp.route('/characteristics/<int:characteristic_id>/edit', methods=['GET', 'POST'])
    @login_required
    @permission_required('beach.characteristics.manage')
    def characteristics_edit(characteristic_id):
        """Edit existing characteristic."""
        from models.characteristic import get_characteristic_by_id, update_characteristic

        char = get_characteristic_by_id(characteristic_id)
        if not char:
            flash('Caracteristica no encontrada', 'error')
            return redirect(url_for('beach.beach_config.characteristics'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip()
            color = request.form.get('color', '#D4AF37').strip()
            active = 1 if request.form.get('active') == '1' else 0

            if not name:
                flash('El nombre es obligatorio', 'error')
                return redirect(url_for(
                    'beach.beach_config.characteristics_edit',
                    characteristic_id=characteristic_id
                ))

            try:
                updated = update_characteristic(
                    characteristic_id,
                    name=name,
                    description=description if description else None,
                    icon=icon if icon else None,
                    color=color,
                    active=active
                )

                if updated:
                    flash('Caracteristica actualizada correctamente', 'success')
                else:
                    flash('No se realizaron cambios', 'warning')
                return redirect(url_for('beach.beach_config.characteristics'))

            except Exception as e:
                flash(f'Error al actualizar: {str(e)}', 'error')

        return render_template(
            'beach/config/characteristic_form.html',
            characteristic=char,
            mode='edit'
        )

    @bp.route('/characteristics/<int:characteristic_id>/delete', methods=['POST'])
    @login_required
    @permission_required('beach.characteristics.manage')
    def characteristics_delete(characteristic_id):
        """Delete characteristic (soft delete)."""
        from models.characteristic import delete_characteristic

        try:
            deleted = delete_characteristic(characteristic_id)
            if deleted:
                flash('Caracteristica eliminada correctamente', 'success')
            else:
                flash('Error al eliminar caracteristica', 'error')
        except Exception as e:
            flash(f'Error al eliminar: {str(e)}', 'error')

        return redirect(url_for('beach.beach_config.characteristics'))

    @bp.route('/characteristics/reorder', methods=['POST'])
    @login_required
    @permission_required('beach.characteristics.manage')
    def characteristics_reorder():
        """Reorder characteristics via AJAX."""
        from models.characteristic import reorder_characteristics

        data = request.get_json()
        ordered_ids = data.get('order', [])

        if not ordered_ids:
            return jsonify({'success': False, 'error': 'No order provided'}), 400

        try:
            reorder_characteristics(ordered_ids)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
```

**Step 2: Register routes in __init__.py**

In `blueprints/beach/routes/config/__init__.py`, add after the preferences import:

```python
from blueprints.beach.routes.config import characteristics
```

And add after `preferences.register_routes(config_bp)`:

```python
characteristics.register_routes(config_bp)
```

**Step 3: Verify syntax**

Run: `python -c "from blueprints.beach.routes.config.characteristics import register_routes; print('Routes OK')"`
Expected: `Routes OK`

**Step 4: Commit**

```bash
git add blueprints/beach/routes/config/characteristics.py blueprints/beach/routes/config/__init__.py
git commit -m "feat(routes): add characteristics admin routes"
```

---

## Task 6: Admin Templates - List View

**Files:**
- Create: `templates/beach/config/characteristics.html`

**Step 1: Create the list template**

```html
{% extends "base.html" %}

{% set page_title = "Caracteristicas" %}

{% block title %}Caracteristicas - PuroBeach{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="mb-0"><i class="fa-solid fa-list-check"></i> Caracteristicas</h2>
        {% if show_inactive %}
        <small class="text-muted">Mostrando caracteristicas inactivas</small>
        {% endif %}
    </div>
    <div class="d-flex gap-2">
        {% if show_inactive %}
        <a href="{{ url_for('beach.beach_config.characteristics') }}" class="btn btn-outline-secondary btn-sm">
            <i class="fa-solid fa-eye-slash"></i> Ocultar Inactivas
        </a>
        {% else %}
        <a href="{{ url_for('beach.beach_config.characteristics', show_inactive='1') }}" class="btn btn-outline-secondary btn-sm">
            <i class="fa-solid fa-eye"></i> Ver Inactivas
        </a>
        {% endif %}
        <a href="{{ url_for('beach.beach_config.characteristics_create') }}" class="btn btn-primary">
            <i class="fa-solid fa-plus"></i> Nueva Caracteristica
        </a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        {% if characteristics %}
        <div class="table-responsive">
            <table class="table table-hover" id="characteristics-table">
                <thead>
                    <tr>
                        <th style="width: 40px;"></th>
                        <th style="width: 60px;" class="text-center">Color</th>
                        <th>Nombre</th>
                        <th>Codigo</th>
                        <th class="text-center" style="width: 100px;">Mobiliario</th>
                        <th class="text-center" style="width: 100px;">Reservas</th>
                        <th style="width: 80px;" class="text-center">Estado</th>
                        <th style="width: 120px;" class="text-center">Acciones</th>
                    </tr>
                </thead>
                <tbody id="sortable-characteristics">
                    {% for char in characteristics %}
                    <tr class="{% if not char.active %}table-secondary{% endif %}" data-id="{{ char.id }}">
                        <td class="text-center drag-handle" style="cursor: grab;">
                            <i class="fa-solid fa-grip-vertical text-muted"></i>
                        </td>
                        <td class="text-center">
                            <span class="badge" style="background-color: {{ char.color }}; min-width: 30px;">
                                {% if char.icon %}
                                <i class="fa-solid {{ char.icon }}"></i>
                                {% else %}
                                &nbsp;
                                {% endif %}
                            </span>
                        </td>
                        <td>
                            <strong>{{ char.name }}</strong>
                            {% if char.description %}
                            <br><small class="text-muted">{{ char.description }}</small>
                            {% endif %}
                        </td>
                        <td><code>{{ char.code }}</code></td>
                        <td class="text-center">
                            <span class="badge bg-secondary">{{ char.furniture_count or 0 }}</span>
                        </td>
                        <td class="text-center">
                            <span class="badge bg-secondary">{{ char.reservation_count or 0 }}</span>
                        </td>
                        <td class="text-center">
                            {% if char.active %}
                            <span class="badge bg-success">Activa</span>
                            {% else %}
                            <span class="badge bg-secondary">Inactiva</span>
                            {% endif %}
                        </td>
                        <td class="text-center">
                            <a href="{{ url_for('beach.beach_config.characteristics_edit', characteristic_id=char.id) }}"
                               class="btn btn-sm btn-outline-primary" title="Editar">
                                <i class="fa-solid fa-edit"></i>
                            </a>
                            <form method="POST"
                                  action="{{ url_for('beach.beach_config.characteristics_delete', characteristic_id=char.id) }}"
                                  class="d-inline"
                                  onsubmit="return confirm('¿Eliminar caracteristica {{ char.name }}?')">
                                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                                <button type="submit" class="btn btn-sm btn-outline-danger" title="Eliminar">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="text-center py-5">
            <i class="fa-solid fa-list-check fa-3x text-muted mb-3"></i>
            <p class="text-muted">No hay caracteristicas configuradas</p>
            <a href="{{ url_for('beach.beach_config.characteristics_create') }}" class="btn btn-primary">
                <i class="fa-solid fa-plus"></i> Crear primera caracteristica
            </a>
        </div>
        {% endif %}
    </div>
</div>

<div class="card mt-4">
    <div class="card-header">
        <h5 class="card-title mb-0"><i class="fa-solid fa-info-circle"></i> Como funcionan las caracteristicas</h5>
    </div>
    <div class="card-body">
        <p class="mb-2">Las caracteristicas unifican el sistema de preferencias:</p>
        <ul class="mb-0">
            <li><strong>Mobiliario:</strong> Asigna caracteristicas al mobiliario para definir sus atributos (ej: "Primera Linea", "Sombra")</li>
            <li><strong>Reservas:</strong> El cliente indica que caracteristicas desea y el sistema sugiere mobiliario compatible</li>
            <li><strong>Matching:</strong> El algoritmo de sugerencias compara directamente las caracteristicas</li>
        </ul>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const tbody = document.getElementById('sortable-characteristics');
    if (tbody) {
        new Sortable(tbody, {
            handle: '.drag-handle',
            animation: 150,
            onEnd: function() {
                const order = Array.from(tbody.querySelectorAll('tr'))
                    .map(row => parseInt(row.dataset.id));

                fetch('{{ url_for("beach.beach_config.characteristics_reorder") }}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': '{{ csrf_token() }}'
                    },
                    body: JSON.stringify({ order: order })
                });
            }
        });
    }
});
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/beach/config/characteristics.html
git commit -m "feat(templates): add characteristics list view"
```

---

## Task 7: Admin Templates - Form View

**Files:**
- Create: `templates/beach/config/characteristic_form.html`

**Step 1: Create the form template**

```html
{% extends "base.html" %}

{% set page_title = "Crear Caracteristica" if mode == 'create' else "Editar Caracteristica" %}

{% block title %}{{ page_title }} - PuroBeach{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>
        <i class="fa-solid fa-list-check"></i>
        {{ page_title }}
    </h2>
    <a href="{{ url_for('beach.beach_config.characteristics') }}" class="btn btn-secondary">
        <i class="fa-solid fa-arrow-left"></i> Volver
    </a>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="code" class="form-label">Codigo <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="code" name="code"
                                       value="{{ characteristic.code if characteristic else '' }}"
                                       {% if mode == 'edit' %}readonly{% endif %}
                                       required maxlength="50" pattern="[a-z0-9_]+"
                                       placeholder="primera_linea">
                                <div class="form-text">Identificador unico (minusculas, sin espacios)</div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="name" class="form-label">Nombre <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="name" name="name"
                                       value="{{ characteristic.name if characteristic else '' }}"
                                       required maxlength="50" placeholder="Primera Linea">
                            </div>
                        </div>
                    </div>

                    <div class="mb-3">
                        <label for="description" class="form-label">Descripcion</label>
                        <textarea class="form-control" id="description" name="description"
                                  rows="2" maxlength="200"
                                  placeholder="Mobiliario ubicado en primera linea de playa">{{ characteristic.description if characteristic else '' }}</textarea>
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="icon" class="form-label">Icono FontAwesome</label>
                                <div class="input-group">
                                    <span class="input-group-text" id="icon-preview">
                                        <i class="fa-solid {{ characteristic.icon if characteristic and characteristic.icon else 'fa-circle' }}"></i>
                                    </span>
                                    <input type="text" class="form-control" id="icon" name="icon"
                                           value="{{ characteristic.icon if characteristic else '' }}"
                                           placeholder="fa-water">
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="color" class="form-label">Color</label>
                                <div class="input-group">
                                    <input type="color" class="form-control form-control-color" id="color" name="color"
                                           value="{{ characteristic.color if characteristic else '#D4AF37' }}" style="width: 60px;">
                                    <input type="text" class="form-control" id="color_text"
                                           value="{{ characteristic.color if characteristic else '#D4AF37' }}" readonly>
                                </div>
                            </div>
                        </div>
                    </div>

                    {% if mode == 'edit' %}
                    <hr>
                    <div class="mb-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="active" name="active" value="1"
                                   {% if characteristic.active %}checked{% endif %}>
                            <label class="form-check-label" for="active">Caracteristica activa</label>
                        </div>
                    </div>
                    {% endif %}

                    <hr>

                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">
                            <i class="fa-solid fa-save"></i>
                            {{ 'Crear Caracteristica' if mode == 'create' else 'Guardar Cambios' }}
                        </button>
                        <a href="{{ url_for('beach.beach_config.characteristics') }}" class="btn btn-secondary">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Vista Previa</h5>
            </div>
            <div class="card-body text-center py-4">
                <span id="preview-badge" class="badge fs-5 px-3 py-2"
                      style="background-color: {{ characteristic.color if characteristic else '#D4AF37' }};">
                    <i id="preview-icon" class="fa-solid {{ characteristic.icon if characteristic and characteristic.icon else 'fa-circle' }} me-1"></i>
                    <span id="preview-name">{{ characteristic.name if characteristic else 'Caracteristica' }}</span>
                </span>
            </div>
        </div>

        <div class="card mt-3">
            <div class="card-header">
                <h5 class="card-title mb-0">Iconos Sugeridos</h5>
            </div>
            <div class="card-body">
                <div class="d-flex flex-wrap gap-2">
                    {% set icons = ['fa-water', 'fa-umbrella', 'fa-sun', 'fa-anchor', 'fa-star',
                                    'fa-martini-glass', 'fa-children', 'fa-wheelchair', 'fa-volume-off',
                                    'fa-couch', 'fa-tree', 'fa-wind'] %}
                    {% for ic in icons %}
                    <button type="button" class="btn btn-outline-secondary icon-btn" data-icon="{{ ic }}" title="{{ ic }}">
                        <i class="fa-solid {{ ic }}"></i>
                    </button>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="card mt-3">
            <div class="card-header">
                <h5 class="card-title mb-0">Colores Sugeridos</h5>
            </div>
            <div class="card-body">
                <div class="d-flex flex-wrap gap-2">
                    {% set colors = ['#D4AF37', '#1A3A5C', '#4A7C59', '#C1444F', '#E5A33D', '#6B7280', '#17A2B8', '#6F42C1'] %}
                    {% for c in colors %}
                    <button type="button" class="btn color-btn"
                            style="background-color: {{ c }}; width: 36px; height: 36px; border: 2px solid white; border-radius: 50%;"
                            data-color="{{ c }}">
                    </button>
                    {% endfor %}
                </div>
            </div>
        </div>

        {% if mode == 'edit' and characteristic %}
        <div class="card mt-3">
            <div class="card-header">
                <h5 class="card-title mb-0">Uso</h5>
            </div>
            <div class="card-body">
                <p class="small mb-1">
                    <i class="fa-solid fa-couch me-1"></i>
                    <strong>Mobiliario:</strong> {{ characteristic.furniture_count or 0 }}
                </p>
                <p class="small mb-1">
                    <i class="fa-solid fa-calendar me-1"></i>
                    <strong>Reservas:</strong> {{ characteristic.reservation_count or 0 }}
                </p>
                <p class="small mb-0">
                    <i class="fa-solid fa-user me-1"></i>
                    <strong>Clientes:</strong> {{ characteristic.customer_count or 0 }}
                </p>
            </div>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.getElementById('color').addEventListener('input', function() {
    document.getElementById('color_text').value = this.value;
    document.getElementById('preview-badge').style.backgroundColor = this.value;
});

document.getElementById('name').addEventListener('input', function() {
    document.getElementById('preview-name').textContent = this.value || 'Caracteristica';
});

document.getElementById('icon').addEventListener('input', function() {
    const icon = this.value || 'fa-circle';
    document.getElementById('icon-preview').innerHTML = '<i class="fa-solid ' + icon + '"></i>';
    document.getElementById('preview-icon').className = 'fa-solid ' + icon + ' me-1';
});

document.querySelectorAll('.icon-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const icon = this.dataset.icon;
        document.getElementById('icon').value = icon;
        document.getElementById('icon-preview').innerHTML = '<i class="fa-solid ' + icon + '"></i>';
        document.getElementById('preview-icon').className = 'fa-solid ' + icon + ' me-1';
    });
});

document.querySelectorAll('.color-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const color = this.dataset.color;
        document.getElementById('color').value = color;
        document.getElementById('color_text').value = color;
        document.getElementById('preview-badge').style.backgroundColor = color;
    });
});

// Auto-generate code from name (only on create)
{% if mode == 'create' %}
document.getElementById('name').addEventListener('input', function() {
    const code = this.value.toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_|_$/g, '');
    document.getElementById('code').value = code;
});
{% endif %}
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/beach/config/characteristic_form.html
git commit -m "feat(templates): add characteristics form view"
```

---

## Task 8: Add Permissions for Characteristics

**Files:**
- Modify: `database/seed.py`

**Step 1: Add characteristics permissions to seed data**

Find the permissions section in `seed.py` and add after similar beach permissions:

```python
    # Characteristics permissions
    ('beach.characteristics.view', 'Ver Caracteristicas', 'Ver lista de caracteristicas',
     'beach', 'config', 1, 26, 'fa-list-check', '/beach/config/characteristics'),
    ('beach.characteristics.manage', 'Gestionar Caracteristicas', 'Crear, editar y eliminar caracteristicas',
     'beach', 'config', 0, 0, None, None),
```

**Step 2: Commit**

```bash
git add database/seed.py
git commit -m "feat(seed): add characteristics permissions"
```

---

## Task 9: Update Suggestion Scoring Algorithm

**Files:**
- Modify: `models/reservation_suggestions_scoring.py`

**Step 1: Replace hardcoded PREFERENCE_TO_FEATURE with characteristic matching**

Replace the `PREFERENCE_TO_FEATURE` constant and `score_preference_match` function:

```python
# Remove or comment out PREFERENCE_TO_FEATURE dict (lines 20-29)

# Replace score_preference_match function with:
def score_preference_match(furniture_id: int, preferences: list) -> dict:
    """
    Score how well furniture matches requested characteristics.

    Uses the unified características system - direct ID comparison.

    Args:
        furniture_id: Furniture ID to score
        preferences: List of characteristic IDs requested (NOT codes)

    Returns:
        dict: {
            'score': float (0.0 to 1.0),
            'matched': list of matched characteristic names,
            'total_requested': int
        }
    """
    from models.characteristic_assignments import score_characteristic_match

    # Handle empty preferences
    if not preferences:
        return {
            'score': 1.0,
            'matched': [],
            'total_requested': 0
        }

    # Use the new characteristic matching system
    result = score_characteristic_match(furniture_id, preferences)

    # Get matched characteristic names for display
    matched_names = []
    if result['matched']:
        from models.characteristic import get_characteristic_by_id
        for char_id in result['matched']:
            char = get_characteristic_by_id(char_id)
            if char:
                matched_names.append(char['name'])

    return {
        'score': result['score'],
        'matched': matched_names,
        'total_requested': len(preferences)
    }
```

**Step 2: Remove get_furniture_features function**

Delete or comment out the `get_furniture_features()` function that infers features from zone names (around lines 141-192). This is no longer needed.

**Step 3: Commit**

```bash
git add models/reservation_suggestions_scoring.py
git commit -m "refactor(suggestions): use characteristics for matching"
```

---

## Task 10: Remove Old Preferences System

**Files:**
- Delete: `models/preference.py`
- Delete: `models/reservation_preferences.py`
- Delete: `blueprints/beach/routes/config/preferences.py`
- Delete: `templates/beach/config/preferences.html`
- Delete: `templates/beach/config/preference_form.html`
- Modify: `blueprints/beach/routes/config/__init__.py`

**Step 1: Remove preferences route registration**

In `blueprints/beach/routes/config/__init__.py`, remove:
```python
from blueprints.beach.routes.config import preferences
```

And remove:
```python
preferences.register_routes(config_bp)
```

**Step 2: Delete old files**

```bash
rm models/preference.py
rm models/reservation_preferences.py
rm blueprints/beach/routes/config/preferences.py
rm templates/beach/config/preferences.html
rm templates/beach/config/preference_form.html
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove old preferences system"
```

---

## Task 11: Update Seed Data for Characteristics

**Files:**
- Modify: `database/seed.py`

**Step 1: Replace preferences seed with characteristics seed**

Find the preferences_data section (around line 255-271) and replace with:

```python
    # 11. Create Características
    characteristics_data = [
        ('primera_linea', 'Primera Linea', 'Mobiliario en primera linea de playa', 'fa-water', '#1A3A5C'),
        ('sombra', 'Sombra', 'Zona con sombra', 'fa-umbrella', '#4A7C59'),
        ('cerca_mar', 'Cerca del Mar', 'Lo mas cerca posible del mar', 'fa-anchor', '#1A3A5C'),
        ('tranquila', 'Zona Tranquila', 'Zona alejada y tranquila', 'fa-volume-off', '#6B7280'),
        ('vip', 'VIP', 'Zona premium', 'fa-star', '#D4AF37'),
        ('cerca_bar', 'Cerca del Bar', 'Cerca del bar o zona de servicio', 'fa-martini-glass', '#C1444F'),
        ('familia', 'Zona Familiar', 'Zona adecuada para familias', 'fa-children', '#E5A33D'),
        ('accesible', 'Acceso Facil', 'Acceso facil para movilidad reducida', 'fa-wheelchair', '#4A7C59'),
    ]

    for idx, (code, name, description, icon, color) in enumerate(characteristics_data):
        db.execute('''
            INSERT INTO beach_characteristics (code, name, description, icon, color, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, description, icon, color, idx))
```

**Step 2: Remove old preferences seed**

Remove the INSERT INTO beach_preferences section.

**Step 3: Commit**

```bash
git add database/seed.py
git commit -m "feat(seed): replace preferences with characteristics"
```

---

## Task 12: Run Migration and Test

**Step 1: Backup database**

```bash
cp instance/beach_club.db instance/beach_club.db.backup
```

**Step 2: Run migration**

```bash
python migrations/migrate_preferences_to_characteristics.py
```

Expected output:
```
================================================================
MIGRATION: Preferences -> Características
================================================================

1. Creating new tables...
Created new tables

2. Migrating preferences to características...
  Migrated preference: pref_sombra -> sombra (id=1)
  ...

3. Migrating customer preferences...
  Migrated X customer preferences

4. Migrating reservation preferences...
  Migrated X reservation preferences

5. Migrating furniture features...
  Migrated X furniture features

================================================================
MIGRATION COMPLETE
================================================================
```

**Step 3: Verify data**

```bash
python -c "from database import get_db; c=get_db(); print(list(c.execute('SELECT * FROM beach_characteristics')))"
```

**Step 4: Start application and test**

```bash
python app.py
```

Navigate to `/beach/config/characteristics` and verify:
- List shows migrated characteristics
- Can create new characteristic
- Can edit existing characteristic
- Can reorder via drag-drop

**Step 5: Commit any fixes**

---

## Task 13: Integration - Furniture Form (Future Task)

This task is documented for future implementation:

**Files to modify:**
- `blueprints/beach/routes/config/furniture.py` - Add characteristics to form data
- `templates/beach/config/furniture_form.html` - Add characteristics multi-select

**Pattern to follow:**
- Add `get_all_characteristics()` call in edit/create routes
- Pass to template
- Add checkbox group in form
- Save via `set_furniture_characteristics()` on POST

---

## Task 14: Integration - Reservation Panel (Future Task)

This task is documented for future implementation:

**Files to modify:**
- Reservation panel JavaScript - Replace preferences with characteristics
- API endpoints for reservation characteristics

**Pattern to follow:**
- Load characteristics via AJAX
- Display as selectable tags/checkboxes
- Auto-populate from customer defaults
- Save to `beach_reservation_characteristics`

---

## Summary

**Core Implementation (Tasks 1-12):**
1. Database schema for characteristics
2. Migration script
3. Characteristic CRUD model
4. Assignment functions model
5. Admin routes
6. List template
7. Form template
8. Permissions
9. Update suggestion algorithm
10. Remove old preferences
11. Update seed data
12. Run migration and test

**Future Integration (Tasks 13-14):**
- Furniture form integration
- Reservation panel integration
- Customer form integration

After completing Tasks 1-12, the characteristics system will be fully functional for admin configuration. The suggestion algorithm will use the new system. Integration into furniture and reservation forms can be done incrementally.
