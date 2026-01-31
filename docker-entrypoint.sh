#!/bin/bash
set -e

echo "=== PuroBeach Production Startup ==="

# Copy static files to shared volume (for Nginx direct serving)
if [ -d /app/static-shared ]; then
    echo "Syncing static files to shared volume..."
    cp -r /app/static/* /app/static-shared/ 2>/dev/null || true
fi

# Ensure log directory exists
mkdir -p /app/logs

# Initialize database if it doesn't exist
if [ ! -f "${DATABASE_PATH:-/app/instance/beach_club.db}" ]; then
    echo "Database not found, initializing..."
    flask init-db
else
    echo "Database found, skipping init."
fi

# Run pending migrations
echo "Running migrations..."
flask run-migrations

echo "=== Starting Gunicorn ==="
exec gunicorn wsgi:application -c gunicorn.conf.py
