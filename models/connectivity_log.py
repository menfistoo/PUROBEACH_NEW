"""
Connectivity event log model.
Stores client-reported network drops so staff WiFi issues can be audited.
"""

from database import get_db


def log_connectivity_event(
    user_id: int = None,
    username: str = None,
    offline_at: str = None,
    online_at: str = None,
    duration_seconds: int = None,
    page: str = None,
    user_agent: str = None,
    ip: str = None
) -> int:
    """
    Record a connectivity event (a client reconnecting after a drop).

    Returns:
        New event ID
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO beach_connectivity_events
            (user_id, username, offline_at, online_at, duration_seconds, page, user_agent, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, offline_at, online_at, duration_seconds,
              page, user_agent, ip))
        conn.commit()
        return cursor.lastrowid


def get_recent_connectivity_events(limit: int = 200, offset: int = 0) -> list:
    """Get recent connectivity events, newest first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM beach_connectivity_events
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        return [dict(row) for row in cursor.fetchall()]


def get_connectivity_summary(days: int = 14) -> list:
    """
    Per-day summary of drops for the last N days: count and total/avg downtime.

    Returns:
        List of dicts: {day, drops, total_seconds, avg_seconds}
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(created_at) AS day,
                   COUNT(*) AS drops,
                   COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                   CAST(COALESCE(AVG(duration_seconds), 0) AS INTEGER) AS avg_seconds
            FROM beach_connectivity_events
            WHERE created_at >= date('now', ?)
            GROUP BY date(created_at)
            ORDER BY day DESC
        ''', (f'-{int(days)} days',))
        return [dict(row) for row in cursor.fetchall()]
