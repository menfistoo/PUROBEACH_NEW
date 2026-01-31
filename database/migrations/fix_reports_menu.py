"""
Fix Reports Menu Item Migration
Updates the Reportes menu item to show 'Conciliación de Pagos'
and link directly to /beach/reports/payment-reconciliation.
"""

from database import get_db


def migrate_fix_reports_menu() -> bool:
    """
    Update reports menu item name and URL.

    Returns:
        bool: True if migration applied, False if already correct
    """
    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Check current state
            cursor.execute("""
                SELECT name, menu_url FROM permissions
                WHERE code = 'beach.reports.view'
            """)
            row = cursor.fetchone()

            if not row:
                print("[INFO] beach.reports.view permission not found, skipping...")
                return False

            if row[0] == 'Conciliación de Pagos':
                print("[INFO] Reports menu already updated, skipping...")
                return False

            cursor.execute("""
                UPDATE permissions
                SET name = 'Conciliación de Pagos',
                    menu_url = '/beach/reports/payment-reconciliation'
                WHERE code = 'beach.reports.view'
            """)

            conn.commit()
            print("[OK] Reports menu item updated to 'Conciliación de Pagos'")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Migration failed: {e}")
            raise
