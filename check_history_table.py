"""Check reservation_status_history table schema"""
from app import create_app
from database import get_db

app = create_app()

with app.app_context():
    db = get_db()
    cursor = db.cursor()

    # Get table schema
    cursor.execute("PRAGMA table_info(reservation_status_history)")
    columns = cursor.fetchall()

    print("reservation_status_history table columns:")
    for col in columns:
        print(f"  {col['name']:30} {col['type']:15} {'NOT NULL' if col['notnull'] else 'NULL':10} {'PK' if col['pk'] else ''}")
