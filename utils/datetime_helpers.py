"""Timezone-aware date/time helpers for the beach club application."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import current_app


def get_timezone() -> ZoneInfo:
    """Get the configured timezone."""
    tz_name = current_app.config.get('TIMEZONE', 'Europe/Madrid')
    return ZoneInfo(tz_name)


def get_today() -> date:
    """Get today's date in the configured timezone."""
    return datetime.now(get_timezone()).date()


def get_now() -> datetime:
    """Get current datetime in the configured timezone."""
    return datetime.now(get_timezone())
