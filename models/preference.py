"""
Beach customer preference data access functions.
Handles preference CRUD operations for the suggestion algorithm.
"""

from database import get_db


def get_all_preferences(active_only: bool = True) -> list:
    """
    Get all customer preferences.

    Args:
        active_only: If True, only return active preferences

    Returns:
        List of preference dicts
    """
    db = get_db()
    cursor = db.cursor()

    query = '''
        SELECT p.*,
               (SELECT COUNT(*) FROM beach_customer_preferences
                WHERE preference_id = p.id) as usage_count
        FROM beach_preferences p
    '''

    if active_only:
        query += ' WHERE p.active = 1'

    query += ' ORDER BY p.name'

    cursor.execute(query)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_preference_by_id(preference_id: int) -> dict:
    """
    Get preference by ID.

    Args:
        preference_id: Preference ID

    Returns:
        Preference dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM beach_preferences WHERE id = ?', (preference_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_preference_by_code(code: str) -> dict:
    """
    Get preference by code.

    Args:
        code: Preference code

    Returns:
        Preference dict or None if not found
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM beach_preferences WHERE code = ?', (code,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_preference(code: str, name: str, description: str = None,
                       icon: str = None, maps_to_feature: str = None) -> int:
    """
    Create new preference.

    Args:
        code: Unique preference code
        name: Display name
        description: Description
        icon: FontAwesome icon class
        maps_to_feature: Feature code this preference maps to for suggestions

    Returns:
        New preference ID

    Raises:
        ValueError if code already exists
    """
    db = get_db()
    cursor = db.cursor()

    # Check if code exists
    existing = get_preference_by_code(code)
    if existing:
        raise ValueError(f'Ya existe una preferencia con el codigo "{code}"')

    cursor.execute('''
        INSERT INTO beach_preferences (code, name, description, icon, maps_to_feature)
        VALUES (?, ?, ?, ?, ?)
    ''', (code, name, description, icon, maps_to_feature))

    db.commit()
    return cursor.lastrowid


def update_preference(preference_id: int, **kwargs) -> bool:
    """
    Update preference fields.

    Args:
        preference_id: Preference ID to update
        **kwargs: Fields to update

    Returns:
        True if updated successfully
    """
    db = get_db()

    allowed_fields = ['name', 'description', 'icon', 'maps_to_feature', 'active']
    updates = []
    values = []

    for field in allowed_fields:
        if field in kwargs:
            updates.append(f'{field} = ?')
            values.append(kwargs[field])

    if not updates:
        return False

    values.append(preference_id)
    query = f'UPDATE beach_preferences SET {", ".join(updates)} WHERE id = ?'

    cursor = db.cursor()
    cursor.execute(query, values)
    db.commit()

    return cursor.rowcount > 0


def delete_preference(preference_id: int) -> bool:
    """
    Soft delete preference (set active = 0).

    Args:
        preference_id: Preference ID to delete

    Returns:
        True if deleted successfully
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        UPDATE beach_preferences SET active = 0
        WHERE id = ?
    ''', (preference_id,))

    db.commit()
    return cursor.rowcount > 0


def get_customer_preferences(customer_id: int) -> list:
    """
    Get preferences assigned to a customer.

    Args:
        customer_id: Customer ID

    Returns:
        List of preference dicts
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT p.*
        FROM beach_preferences p
        JOIN beach_customer_preferences cp ON p.id = cp.preference_id
        WHERE cp.customer_id = ?
        ORDER BY p.name
    ''', (customer_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def assign_preference_to_customer(customer_id: int, preference_id: int) -> bool:
    """
    Assign a preference to a customer.

    Args:
        customer_id: Customer ID
        preference_id: Preference ID

    Returns:
        True if assigned successfully
    """
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO beach_customer_preferences (customer_id, preference_id)
            VALUES (?, ?)
        ''', (customer_id, preference_id))
        db.commit()
        return True
    except Exception:
        return False


def remove_preference_from_customer(customer_id: int, preference_id: int) -> bool:
    """
    Remove a preference from a customer.

    Args:
        customer_id: Customer ID
        preference_id: Preference ID

    Returns:
        True if removed successfully
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        DELETE FROM beach_customer_preferences
        WHERE customer_id = ? AND preference_id = ?
    ''', (customer_id, preference_id))

    db.commit()
    return cursor.rowcount > 0
