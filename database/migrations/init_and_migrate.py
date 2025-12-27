"""
Initialize database and run pricing migration.
"""

from app import create_app
from database import init_db

# Create Flask app
app = create_app()

# Initialize database within app context
with app.app_context():
    print("Initializing database...")
    init_db()
    print("\nDatabase initialized successfully!")

    # Run reservations migration to add base pricing fields
    print("\n" + "="*60)
    print("Running reservations migration...")
    print("="*60)

    from database.migrations.reservations import migrate_reservations_v2
    migrate_reservations_v2()

    # Now run the pricing integration migration
    print("\n" + "="*60)
    print("Running pricing integration migration...")
    print("="*60)

    from database.migrations.pricing_integration import run_migration
    run_migration()
