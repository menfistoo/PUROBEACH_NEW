"""Check furniture data in database"""
from app import create_app
from database import get_db

app = create_app()

with app.app_context():
    db = get_db()
    cursor = db.cursor()

    # Check total furniture
    cursor.execute('SELECT COUNT(*) as count FROM beach_furniture')
    total = cursor.fetchone()['count']
    print(f'Total furniture in database: {total}')

    # Check zone 1 furniture
    cursor.execute('SELECT COUNT(*) as count FROM beach_furniture WHERE zone_id = 1')
    zone1_count = cursor.fetchone()['count']
    print(f'Zone 1 furniture: {zone1_count}')

    # Show ALL furniture from zone 1
    cursor.execute('''
        SELECT id, number, zone_id, furniture_type, position_x, position_y
        FROM beach_furniture
        WHERE zone_id = 1
        ORDER BY id
    ''')

    print('\nAll furniture from Zone 1:')
    for row in cursor.fetchall():
        print(f"  ID:{row['id']} #{row['number']} Type:{row['furniture_type']} " +
              f"Pos:({row['position_x']},{row['position_y']})")

    # Check all zones
    cursor.execute('''
        SELECT z.id, z.name, COUNT(f.id) as furniture_count
        FROM beach_zones z
        LEFT JOIN beach_furniture f ON f.zone_id = z.id
        GROUP BY z.id, z.name
        ORDER BY z.id
    ''')

    print('\nFurniture count by zone:')
    for row in cursor.fetchall():
        print(f"  Zone {row['id']} ({row['name']}): {row['furniture_count']} items")

    # Show all furniture grouped by type
    cursor.execute('''
        SELECT furniture_type, COUNT(*) as count
        FROM beach_furniture
        GROUP BY furniture_type
    ''')

    print('\nFurniture by type:')
    for row in cursor.fetchall():
        print(f"  {row['furniture_type']}: {row['count']} items")
