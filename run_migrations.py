#!/usr/bin/env python
"""
Run database migrations.
"""

from app import create_app
from database.connection import get_db
from database.migrations import run_all_migrations

def check_database_initialized():
    """Check if the database has been initialized."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='users'
    """)
    return cursor.fetchone() is not None

if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        # Check if database needs initialization
        if not check_database_initialized():
            print("Database not initialized. Initializing from schema...")
            from database.connection import init_db
            init_db()
            print("\nDatabase initialized. Now running migrations...\n")

        print("Running migrations...")
        result = run_all_migrations()

        print(f"\n{'='*60}")
        print(f"Migration Summary:")
        print(f"{'='*60}")
        print(f"Total migrations: {result['total']}")
        print(f"Applied: {result['applied']}")
        print(f"Skipped: {result['skipped']}")
        print(f"Failed: {result['failed']}")

        if result.get('errors'):
            print(f"\nErrors:")
            for name, msg in result['errors']:
                print(f"  - {name}: {msg}")

        print(f"{'='*60}")
