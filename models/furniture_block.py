"""
Furniture Block model.
CRUD operations for furniture blocking (maintenance, VIP holds, events).
"""

from database import get_db
from typing import Optional


# =============================================================================
# BLOCK TYPES
# =============================================================================

BLOCK_TYPES = {
    'maintenance': {'name': 'Mantenimiento', 'color': '#9CA3AF'},
    'vip_hold': {'name': 'Reserva VIP', 'color': '#D4AF37'},
    'event': {'name': 'Evento', 'color': '#3B82F6'},
    'other': {'name': 'Otro', 'color': '#6B7280'}
}


# =============================================================================
# CRUD OPERATIONS
# =============================================================================

def create_furniture_block(
    furniture_id: int,
    start_date: str,
    end_date: str,
    block_type: str = 'other',
    reason: str = None,
    notes: str = None,
    created_by: str = None
) -> int:
    """
    Create a new furniture block.

    Args:
        furniture_id: Furniture ID to block
        start_date: Block start date (YYYY-MM-DD)
        end_date: Block end date (YYYY-MM-DD)
        block_type: Type of block (maintenance, vip_hold, event, other)
        reason: Reason for blocking
        notes: Additional notes
        created_by: Username creating the block

    Returns:
        int: Block ID

    Raises:
        ValueError: If validation fails
    """
    if block_type not in BLOCK_TYPES:
        raise ValueError(f"Tipo de bloqueo inválido: {block_type}")

    if start_date > end_date:
        raise ValueError("Fecha de inicio no puede ser posterior a fecha de fin")

    with get_db() as conn:
        # Fetch releasing states directly on this connection to avoid nested context manager.
        # (get_db() always returns the same g.db; a nested with-get_db() would commit this transaction.)
        releasing_rows = conn.execute(
            'SELECT name FROM beach_reservation_states WHERE is_availability_releasing = 1'
        ).fetchall()
        releasing_states = [row['name'] for row in releasing_rows]

        # Check for active reservations that conflict with this block's date range
        if releasing_states:
            placeholders = ','.join('?' * len(releasing_states))
            conflicts = conn.execute(f'''
                SELECT r.ticket_number
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                WHERE rf.furniture_id = ?
                  AND rf.assignment_date BETWEEN ? AND ?
                  AND r.current_state NOT IN ({placeholders})
                LIMIT 5
            ''', [furniture_id, start_date, end_date] + releasing_states).fetchall()
        else:
            conflicts = conn.execute('''
                SELECT r.ticket_number
                FROM beach_reservation_furniture rf
                JOIN beach_reservations r ON rf.reservation_id = r.id
                WHERE rf.furniture_id = ?
                  AND rf.assignment_date BETWEEN ? AND ?
                LIMIT 5
            ''', (furniture_id, start_date, end_date)).fetchall()

        if conflicts:
            tickets = ', '.join(row['ticket_number'] for row in conflicts)
            raise ValueError(f"Mobiliario con reservas activas en estas fechas: {tickets}")

        cursor = conn.execute('''
            INSERT INTO beach_furniture_blocks
            (furniture_id, start_date, end_date, block_type, reason, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (furniture_id, start_date, end_date, block_type, reason, notes, created_by))

        conn.commit()
        return cursor.lastrowid


def get_block_by_id(block_id: int) -> Optional[dict]:
    """
    Get a block by ID.

    Args:
        block_id: Block ID

    Returns:
        dict or None: Block data
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT b.*, f.number as furniture_number, f.zone_id
            FROM beach_furniture_blocks b
            JOIN beach_furniture f ON b.furniture_id = f.id
            WHERE b.id = ?
        ''', (block_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_blocks_by_furniture(furniture_id: int, date_from: str = None, date_to: str = None) -> list:
    """
    Get all blocks for a furniture item.

    Args:
        furniture_id: Furniture ID
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        list: List of blocks
    """
    with get_db() as conn:
        query = '''
            SELECT b.*, f.number as furniture_number
            FROM beach_furniture_blocks b
            JOIN beach_furniture f ON b.furniture_id = f.id
            WHERE b.furniture_id = ?
        '''
        params = [furniture_id]

        if date_from:
            query += ' AND b.end_date >= ?'
            params.append(date_from)

        if date_to:
            query += ' AND b.start_date <= ?'
            params.append(date_to)

        query += ' ORDER BY b.start_date'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_blocks_for_date(target_date: str, zone_id: int = None) -> list:
    """
    Get all blocks active on a specific date.

    Args:
        target_date: Date to check (YYYY-MM-DD)
        zone_id: Optional zone filter

    Returns:
        list: List of blocks
    """
    with get_db() as conn:
        query = '''
            SELECT b.*, f.number as furniture_number, f.zone_id, z.name as zone_name
            FROM beach_furniture_blocks b
            JOIN beach_furniture f ON b.furniture_id = f.id
            JOIN beach_zones z ON f.zone_id = z.id
            WHERE b.start_date <= ? AND b.end_date >= ?
        '''
        params = [target_date, target_date]

        if zone_id:
            query += ' AND f.zone_id = ?'
            params.append(zone_id)

        query += ' ORDER BY f.zone_id, f.number'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def is_furniture_blocked(furniture_id: int, target_date: str) -> Optional[dict]:
    """
    Check if furniture is blocked on a specific date.

    Args:
        furniture_id: Furniture ID
        target_date: Date to check

    Returns:
        dict or None: Block data if blocked, None otherwise
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT b.*, f.number as furniture_number
            FROM beach_furniture_blocks b
            JOIN beach_furniture f ON b.furniture_id = f.id
            WHERE b.furniture_id = ?
            AND b.start_date <= ?
            AND b.end_date >= ?
            LIMIT 1
        ''', (furniture_id, target_date, target_date))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_block(
    block_id: int,
    start_date: str = None,
    end_date: str = None,
    block_type: str = None,
    reason: str = None,
    notes: str = None
) -> bool:
    """
    Update a furniture block.

    Args:
        block_id: Block ID
        start_date: New start date
        end_date: New end date
        block_type: New block type
        reason: New reason
        notes: New notes

    Returns:
        bool: True if updated
    """
    updates = []
    params = []

    if start_date is not None:
        updates.append('start_date = ?')
        params.append(start_date)

    if end_date is not None:
        updates.append('end_date = ?')
        params.append(end_date)

    if block_type is not None:
        if block_type not in BLOCK_TYPES:
            raise ValueError(f"Tipo de bloqueo inválido: {block_type}")
        updates.append('block_type = ?')
        params.append(block_type)

    if reason is not None:
        updates.append('reason = ?')
        params.append(reason)

    if notes is not None:
        updates.append('notes = ?')
        params.append(notes)

    if not updates:
        return False

    params.append(block_id)

    with get_db() as conn:
        conn.execute(f'''
            UPDATE beach_furniture_blocks
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)
        conn.commit()
        return True


def delete_block(block_id: int) -> bool:
    """
    Delete a furniture block.

    Args:
        block_id: Block ID

    Returns:
        bool: True if deleted
    """
    with get_db() as conn:
        cursor = conn.execute('''
            DELETE FROM beach_furniture_blocks WHERE id = ?
        ''', (block_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_blocks_for_furniture(furniture_id: int) -> int:
    """
    Delete all blocks for a furniture item.

    Args:
        furniture_id: Furniture ID

    Returns:
        int: Number of blocks deleted
    """
    with get_db() as conn:
        cursor = conn.execute('''
            DELETE FROM beach_furniture_blocks WHERE furniture_id = ?
        ''', (furniture_id,))
        conn.commit()
        return cursor.rowcount


def get_blocked_furniture_ids(target_date: str) -> list:
    """
    Get list of furniture IDs that are blocked on a date.

    Args:
        target_date: Date to check

    Returns:
        list: List of furniture IDs
    """
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT DISTINCT furniture_id
            FROM beach_furniture_blocks
            WHERE start_date <= ? AND end_date >= ?
        ''', (target_date, target_date))

        return [row['furniture_id'] for row in cursor.fetchall()]


def partial_unblock(block_id: int, unblock_start: str, unblock_end: str) -> dict:
    """
    Partially unblock a date range within an existing block.

    This may delete, shrink, or split the block depending on the unblock range:
    - If unblock covers entire block: delete block
    - If unblock is at start: shrink block (move start_date forward)
    - If unblock is at end: shrink block (move end_date back)
    - If unblock is in middle: split into two blocks

    Args:
        block_id: Block ID to partially unblock
        unblock_start: Start date to unblock (YYYY-MM-DD)
        unblock_end: End date to unblock (YYYY-MM-DD)

    Returns:
        dict: Result with action taken and any new block IDs

    Raises:
        ValueError: If validation fails
    """
    from datetime import datetime, timedelta

    block = get_block_by_id(block_id)
    if not block:
        raise ValueError("Bloqueo no encontrado")

    # Normalize dates to strings for comparison (handles both str and date objects)
    block_start = str(block['start_date'])
    block_end = str(block['end_date'])

    # Validate unblock range is within block range
    if unblock_start < block_start or unblock_end > block_end:
        raise ValueError("El rango a desbloquear debe estar dentro del bloqueo existente")

    if unblock_start > unblock_end:
        raise ValueError("Fecha de inicio no puede ser posterior a fecha de fin")

    # Calculate adjacent dates
    def add_days(date_str: str, days: int) -> str:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return (dt + timedelta(days=days)).strftime('%Y-%m-%d')

    result = {'action': None, 'block_ids': []}

    with get_db() as conn:
        # Case 1: Unblock covers entire block - delete it
        if unblock_start <= block_start and unblock_end >= block_end:
            conn.execute('DELETE FROM beach_furniture_blocks WHERE id = ?', (block_id,))
            result['action'] = 'deleted'

        # Case 2: Unblock at start - shrink block forward
        elif unblock_start <= block_start and unblock_end < block_end:
            new_start = add_days(unblock_end, 1)
            conn.execute('''
                UPDATE beach_furniture_blocks
                SET start_date = ?
                WHERE id = ?
            ''', (new_start, block_id))
            result['action'] = 'shrunk_start'
            result['block_ids'] = [block_id]

        # Case 3: Unblock at end - shrink block backward
        elif unblock_start > block_start and unblock_end >= block_end:
            new_end = add_days(unblock_start, -1)
            conn.execute('''
                UPDATE beach_furniture_blocks
                SET end_date = ?
                WHERE id = ?
            ''', (new_end, block_id))
            result['action'] = 'shrunk_end'
            result['block_ids'] = [block_id]

        # Case 4: Unblock in middle - split into two blocks
        else:
            # Update original block to end before unblock range
            new_end_first = add_days(unblock_start, -1)
            conn.execute('''
                UPDATE beach_furniture_blocks
                SET end_date = ?
                WHERE id = ?
            ''', (new_end_first, block_id))

            # Create new block starting after unblock range
            new_start_second = add_days(unblock_end, 1)
            cursor = conn.execute('''
                INSERT INTO beach_furniture_blocks
                (furniture_id, start_date, end_date, block_type, reason, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                block['furniture_id'],
                new_start_second,
                block_end,
                block['block_type'],
                block['reason'],
                block['notes'],
                block['created_by']
            ))

            result['action'] = 'split'
            result['block_ids'] = [block_id, cursor.lastrowid]

        conn.commit()

    return result
