"""
Database connection management.
Handles connection pooling, initialization, and teardown.
"""

import sqlite3
import os
from flask import g, current_app


def get_db():
    """
    Get thread-safe database connection with row factory.

    Returns:
        sqlite3.Connection: Database connection object
    """
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE_PATH', 'instance/beach_club.db')
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraints
        g.db.execute('PRAGMA foreign_keys = ON')
        # Enable WAL mode for better concurrency
        g.db.execute('PRAGMA journal_mode = WAL')
    return g.db


def close_db(e=None):
    """
    Close database connection.

    Args:
        e: Exception if any (from Flask teardown context)
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Initialize database: drop existing tables, create new schema, insert seed data.
    WARNING: This will delete all existing data!
    """
    from database.schema import drop_tables, create_tables, create_indexes
    from database.seed import seed_database

    db = get_db()

    # Drop existing tables (in reverse order of dependencies)
    drop_tables(db)

    # Create all tables
    create_tables(db)

    # Create indexes
    create_indexes(db)

    # Insert seed data
    seed_database(db)

    db.commit()
    print("Database initialized successfully!")
