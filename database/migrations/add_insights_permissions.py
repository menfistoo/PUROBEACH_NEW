"""
Migration: Add insights permissions.
"""

from database import get_db


def migrate():
    """Add insights module permissions."""
    with get_db() as conn:
        # Check if permissions already exist
        cursor = conn.execute(
            "SELECT COUNT(*) FROM permissions WHERE code LIKE 'beach.insights.%'"
        )
        if cursor.fetchone()[0] > 0:
            print("Insights permissions already exist, skipping...")
            return

        # Insert insights permissions
        permissions = [
            ('beach.insights.view', 'Ver Dashboard Operativo', 'beach', 1, 'fa-chart-line', '/beach/insights', 85),
            ('beach.insights.analytics', 'Ver Analiticas Avanzadas', 'beach', 1, 'fa-chart-bar', '/beach/insights/analytics', 86),
        ]

        for code, name, module, is_menu, icon, menu_url, order in permissions:
            conn.execute('''
                INSERT INTO permissions (code, name, module, is_menu_item, menu_icon, menu_url, menu_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (code, name, module, is_menu, icon, menu_url, order))

        # Grant to admin role (id=1)
        conn.execute('''
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
            SELECT 1, id FROM permissions WHERE code LIKE 'beach.insights.%'
        ''')

        # Grant to manager role (id=2) if exists
        conn.execute('''
            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
            SELECT 2, id FROM permissions WHERE code LIKE 'beach.insights.%'
        ''')

        conn.commit()
        print("Insights permissions added successfully.")


if __name__ == '__main__':
    migrate()
