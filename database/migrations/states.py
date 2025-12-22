"""
Reservation states migrations.
Enhancements to beach_reservation_states table.
"""

from database.connection import get_db


def migrate_add_sentada_state() -> bool:
    """
    Migration: Add 'Sentada' state for tracking when customers are at the beach.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM beach_reservation_states WHERE code = 'sentada'")
    if cursor.fetchone():
        print("Migration already applied - Sentada state exists.")
        return False

    print("Applying add_sentada_state migration...")

    try:
        cursor.execute("SELECT MAX(display_order) as max_order FROM beach_reservation_states")
        row = cursor.fetchone()
        next_order = (row['max_order'] or 0) + 1

        cursor.execute('''
            INSERT INTO beach_reservation_states
            (code, name, color, icon, is_availability_releasing, display_order, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('sentada', 'Sentada', '#28A745', 'fa-couch', 0, next_order, 1))

        db.commit()
        print("Migration add_sentada_state applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise


def migrate_reservation_states_configurable() -> bool:
    """
    Migration: Make reservation states fully configurable.

    Adds columns for display_priority, creates_incident, is_system, is_default.
    Updates existing states and replaces with 6 core states.

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("PRAGMA table_info(beach_reservation_states)")
    existing_columns = [row['name'] for row in cursor.fetchall()]

    if 'display_priority' in existing_columns:
        print("Migration already applied - configurable states columns exist.")
        return False

    print("Applying reservation_states_configurable migration...")

    try:
        # Add new columns
        columns_to_add = [
            ('ALTER TABLE beach_reservation_states ADD COLUMN display_priority INTEGER DEFAULT 0', 'display_priority'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN creates_incident INTEGER DEFAULT 0', 'creates_incident'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN is_system INTEGER DEFAULT 0', 'is_system'),
            ('ALTER TABLE beach_reservation_states ADD COLUMN is_default INTEGER DEFAULT 0', 'is_default'),
        ]

        for sql, col_name in columns_to_add:
            if col_name not in existing_columns:
                db.execute(sql)
                print(f"  Added column: {col_name}")

        # Deactivate legacy states
        cursor.execute('''
            UPDATE beach_reservation_states
            SET active = 0
            WHERE code IN ('pendiente', 'checkin', 'activa', 'completada')
        ''')
        print("  Deactivated legacy states: pendiente, checkin, activa, completada")

        # Update core states with new properties
        # Confirmada: display_priority=3, is_system=1, is_default=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 3, is_system = 1, is_default = 1, color = '#28A745',
                display_order = 1
            WHERE code = 'confirmada'
        ''')

        # Sentada: display_priority=6, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 6, is_system = 1, color = '#2E8B57',
                display_order = 2
            WHERE code = 'sentada'
        ''')

        # Cancelada: is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                display_order = 3
            WHERE code = 'cancelada'
        ''')

        # No-Show: creates_incident=1, is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                creates_incident = 1, color = '#FF4444', display_order = 4
            WHERE code = 'noshow'
        ''')

        # Liberada: is_availability_releasing=1, is_system=1
        cursor.execute('''
            UPDATE beach_reservation_states
            SET display_priority = 0, is_system = 1, is_availability_releasing = 1,
                display_order = 5
            WHERE code = 'liberada'
        ''')

        print("  Updated core states with configurable properties")

        db.commit()
        print("Migration reservation_states_configurable applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
