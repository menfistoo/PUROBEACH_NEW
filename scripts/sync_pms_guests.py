#!/usr/bin/env python3
"""
PMS Guest Sync Script
=====================
Downloads hotel guest Excel file from Nextcloud (WebDAV) and imports it
into the beach club system automatically.

Usage:
    python scripts/sync_pms_guests.py              # Run once
    python scripts/sync_pms_guests.py --force       # Force import even if file unchanged
    python scripts/sync_pms_guests.py --dry-run     # Check without importing

Designed to run as a cron job every 2-4 hours.
"""

import os
import sys
import hashlib
import logging
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CONFIGURATION
# =============================================================================

NEXTCLOUD_URL = os.environ.get(
    'NEXTCLOUD_URL',
    'http://localhost:8081'
)
NEXTCLOUD_USER = os.environ.get('NEXTCLOUD_USER', 'admin')
NEXTCLOUD_PASS = os.environ.get('NEXTCLOUD_PASS', '')
NEXTCLOUD_FILE_PATH = os.environ.get(
    'NEXTCLOUD_FILE_PATH',
    'FrontOffice/PMS/GuestInHouse.xlsx'
)

# Local state file to track last imported file hash
STATE_DIR = PROJECT_ROOT / 'data'
STATE_FILE = STATE_DIR / '.pms_sync_state'

# Logging
LOG_DIR = PROJECT_ROOT / 'logs'
LOG_FILE = LOG_DIR / 'pms_sync.log'

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger('pms_sync')
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(console_handler)

    return logger


log = setup_logging()

# =============================================================================
# NEXTCLOUD WEBDAV
# =============================================================================

def get_webdav_url() -> str:
    """Build the full WebDAV URL for the guest file."""
    base = NEXTCLOUD_URL.rstrip('/')
    file_path = NEXTCLOUD_FILE_PATH.strip('/')
    return f"{base}/remote.php/dav/files/{NEXTCLOUD_USER}/{file_path}"


def download_file_from_nextcloud() -> tuple[bytes | None, str | None]:
    """
    Download the Excel file from Nextcloud via WebDAV.

    Returns:
        Tuple of (file_content_bytes, etag) or (None, None) on failure.
    """
    url = get_webdav_url()
    log.info(f"Downloading from: {url}")

    try:
        response = requests.get(
            url,
            auth=(NEXTCLOUD_USER, NEXTCLOUD_PASS),
            timeout=30
        )

        if response.status_code == 200:
            etag = response.headers.get('ETag', '')
            log.info(f"Downloaded {len(response.content)} bytes (ETag: {etag})")
            return response.content, etag

        elif response.status_code == 404:
            log.warning("File not found in Nextcloud. Waiting for upload.")
            return None, None

        else:
            log.error(f"HTTP {response.status_code}: {response.text[:200]}")
            return None, None

    except requests.ConnectionError:
        log.error("Cannot connect to Nextcloud. Is it running?")
        return None, None
    except requests.Timeout:
        log.error("Nextcloud request timed out.")
        return None, None
    except Exception as e:
        log.error(f"Unexpected error downloading: {e}")
        return None, None


def get_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def get_last_sync_hash() -> str | None:
    """Read the hash of the last successfully imported file."""
    try:
        if STATE_FILE.exists():
            return STATE_FILE.read_text().strip()
    except Exception:
        pass
    return None


def save_sync_hash(file_hash: str) -> None:
    """Save the hash after successful import."""
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(file_hash)

# =============================================================================
# IMPORT
# =============================================================================

def run_import(file_content: bytes) -> dict:
    """
    Save content to temp file and run the hotel guest import.

    Returns:
        Import result dictionary with created/updated/errors counts.
    """
    from app import create_app
    from blueprints.admin.services.user_service import import_hotel_guests_from_excel

    # Save to temp file
    with tempfile.NamedTemporaryFile(
        suffix='.xlsx',
        prefix='pms_sync_',
        delete=False
    ) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        app = create_app()
        with app.app_context():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            source_name = f"pms_auto_sync_{timestamp}"

            result = import_hotel_guests_from_excel(
                file_path=tmp_path,
                source_name=source_name
            )

            return result
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description='Sync PMS guests from Nextcloud')
    parser.add_argument('--force', action='store_true',
                        help='Force import even if file unchanged')
    parser.add_argument('--dry-run', action='store_true',
                        help='Download and check but do not import')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("PMS Guest Sync started")
    log.info("=" * 60)

    # Validate configuration
    if not NEXTCLOUD_PASS:
        log.error("NEXTCLOUD_PASS not set. Use environment variable.")
        sys.exit(1)

    # Step 1: Download from Nextcloud
    content, etag = download_file_from_nextcloud()
    if content is None:
        log.info("No file to process. Exiting.")
        sys.exit(0)

    # Step 2: Check if file changed
    file_hash = get_file_hash(content)
    last_hash = get_last_sync_hash()

    if file_hash == last_hash and not args.force:
        log.info("File unchanged since last sync. Skipping.")
        sys.exit(0)

    log.info(f"File changed (hash: {file_hash[:12]}...)")

    # Step 3: Dry run check
    if args.dry_run:
        log.info("[DRY RUN] Would import file. Exiting.")
        sys.exit(0)

    # Step 4: Run import
    try:
        result = run_import(content)

        created = result.get('created', 0)
        updated = result.get('updated', 0)
        total = result.get('total', 0)
        errors = result.get('errors', [])
        room_changes = result.get('room_changes', [])

        log.info(f"Import complete: {total} processed, "
                 f"{created} created, {updated} updated")

        if room_changes:
            for change in room_changes:
                log.info(f"  Room change: {change['guest_name']} "
                         f"{change['old_room']} → {change['new_room']}")

        if errors:
            log.warning(f"  {len(errors)} errors:")
            for err in errors[:5]:
                log.warning(f"    - {err}")

        # Step 5: Save state
        save_sync_hash(file_hash)
        log.info("Sync hash saved. Done.")

    except Exception as e:
        log.error(f"Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
