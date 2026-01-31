#!/bin/bash
# =============================================================================
# PuroBeach Database Backup Script
# =============================================================================
# Uses SQLite's .backup command for a safe, consistent snapshot.
# Run via host cron:
#   0 3 * * * docker exec purobeach-app /app/scripts/backup.sh
# =============================================================================

set -e

BACKUP_DIR="/app/instance/backups"
DB_PATH="${DATABASE_PATH:-/app/instance/beach_club.db}"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/beach_club_${TIMESTAMP}.db"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform SQLite backup (safe, does not lock the database)
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Compress the backup
gzip "${BACKUP_FILE}"

echo "[$(date)] Backup created: ${BACKUP_FILE}.gz"

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "beach_club_*.db.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Cleanup complete. Backups older than ${RETENTION_DAYS} days removed."
