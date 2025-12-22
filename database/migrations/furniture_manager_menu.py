"""
Furniture Manager menu migration.
Consolidates three separate menu items into unified Furniture Manager.
"""

from database.connection import get_db


def migrate_furniture_manager_menu() -> bool:
    """
    Migration: Consolidate furniture menu items into unified Furniture Manager.

    Changes:
    - Updates 'beach.furniture.view' to become 'Gestor de Mobiliario' at /beach/config/furniture-manager
    - Hides 'beach.map_editor.view' and 'beach.furniture_types.view' from menu (keeps permissions)

    Returns:
        bool: True if migration applied, False if already applied
    """
    db = get_db()
    cursor = db.cursor()

    # Check if migration already applied
    cursor.execute("""
        SELECT menu_url FROM permissions
        WHERE code = 'beach.furniture.view' AND is_menu_item = 1
    """)
    row = cursor.fetchone()
    if row and row['menu_url'] == '/beach/config/furniture-manager':
        print("Migration already applied - furniture manager menu exists.")
        return False

    print("Applying furniture_manager_menu migration...")

    try:
        # Update beach.furniture.view to be the unified menu item
        cursor.execute("""
            UPDATE permissions
            SET name = 'Gestor de Mobiliario',
                menu_url = '/beach/config/furniture-manager',
                menu_icon = 'fa-tools',
                menu_order = 15
            WHERE code = 'beach.furniture.view'
        """)
        print("  Updated beach.furniture.view -> Gestor de Mobiliario")

        # Hide map_editor from menu (keep permission for API access)
        cursor.execute("""
            UPDATE permissions
            SET is_menu_item = 0
            WHERE code = 'beach.map_editor.view'
        """)
        print("  Hidden beach.map_editor.view from menu")

        # Hide furniture_types from menu (keep permission for form access)
        cursor.execute("""
            UPDATE permissions
            SET is_menu_item = 0
            WHERE code = 'beach.furniture_types.view'
        """)
        print("  Hidden beach.furniture_types.view from menu")

        db.commit()
        print("Migration furniture_manager_menu applied successfully!")
        return True

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
