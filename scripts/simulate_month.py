#!/usr/bin/env python
"""
Beach Club Month Simulation Script.

Generates realistic data for one month of beach club operations:
- 100+ customers (60% interno, 40% externo, 10% VIP)
- 300-400 reservations with decreasing occupancy pattern
- 2-3 temporary furniture items for high-demand weekends
- 1-2 furniture blocks (maintenance, VIP hold)

Usage:
    python scripts/simulate_month.py                    # Run simulation
    python scripts/simulate_month.py --dry-run          # Preview what would be created
    python scripts/simulate_month.py --start-date 2026-02-01  # Custom start date
    python scripts/simulate_month.py --month 2026-03    # Simulate specific month
    python scripts/simulate_month.py --high-occupancy   # Force 80-100% occupancy
    python scripts/simulate_month.py --sim-db           # Use simulation database
"""

import sys
import os
import random
import argparse
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging for simulation debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# These imports must happen after path setup
from database import get_db
from models.customer_crud import create_customer, get_all_customers
from models.reservation_crud import create_beach_reservation
from models.reservation_multiday import create_linked_multiday_reservations
from models.reservation_state import change_reservation_state
from models.furniture import get_all_furniture
from models.furniture_daily import create_temporary_furniture, get_next_temp_furniture_number
from models.furniture_block import create_furniture_block
from models.zone import get_all_zones


# =============================================================================
# SIMULATION DATABASE PATH
# =============================================================================

SIM_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'database', 'beach_club_sim.db'
)

HIGH_OCCUPANCY_WEEKDAY = (80, 100)
HIGH_OCCUPANCY_WEEKEND = (95, 100)


# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Customer distribution
CUSTOMER_INTERNO_RATIO = 0.60
CUSTOMER_EXTERNO_RATIO = 0.40
CUSTOMER_VIP_RATIO = 0.10

# Reservation distribution by type
RESERVATION_SINGLE_DAY_RATIO = 0.70
RESERVATION_MULTIDAY_RATIO = 0.20
RESERVATION_WALKIN_RATIO = 0.10

# Reservation state distribution for PAST dates (completed - stay as Confirmada)
STATE_DISTRIBUTION_PAST = {
    'Confirmada': 0.85,
    'Cancelada': 0.08,
    'No-Show': 0.05,
    'Liberada': 0.02
}

# Reservation state distribution for TODAY (can be seated)
STATE_DISTRIBUTION_TODAY = {
    'Confirmada': 0.35,
    'Sentada': 0.50,
    'Cancelada': 0.08,
    'No-Show': 0.05,
    'Liberada': 0.02
}

# Reservation state distribution for FUTURE dates
STATE_DISTRIBUTION_FUTURE = {
    'Confirmada': 0.92,
    'Cancelada': 0.06,
    'Liberada': 0.02
}

# Payment methods by customer type
PAYMENT_INTERNO = {'cargo_habitacion': 0.70, 'tarjeta': 0.20, 'efectivo': 0.10}
PAYMENT_EXTERNO = {'tarjeta': 0.50, 'efectivo': 0.40, None: 0.10}

# Weekly occupancy targets (week_number: (min%, max%))
WEEKLY_OCCUPANCY = {
    1: (80, 100),
    2: (70, 90),
    3: (60, 80),
    4: (50, 70),
    5: (50, 70)  # In case month has 5 weeks
}

# Spanish names
SPANISH_FIRST_NAMES = [
    'Maria', 'Carmen', 'Ana', 'Laura', 'Isabel', 'Rosa', 'Lucia', 'Elena', 'Paula', 'Sofia',
    'Jose', 'Antonio', 'Juan', 'Manuel', 'Francisco', 'David', 'Carlos', 'Miguel', 'Pedro', 'Pablo',
    'Alejandro', 'Daniel', 'Adrian', 'Sergio', 'Fernando', 'Jorge', 'Alberto', 'Roberto', 'Diego', 'Javier',
    'Marta', 'Sara', 'Cristina', 'Patricia', 'Andrea', 'Raquel', 'Beatriz', 'Silvia', 'Teresa', 'Alicia'
]

SPANISH_LAST_NAMES = [
    'Garcia', 'Rodriguez', 'Martinez', 'Lopez', 'Gonzalez', 'Hernandez', 'Perez', 'Sanchez', 'Ramirez', 'Torres',
    'Flores', 'Rivera', 'Gomez', 'Diaz', 'Reyes', 'Morales', 'Cruz', 'Ortiz', 'Gutierrez', 'Chavez',
    'Ramos', 'Vargas', 'Castillo', 'Jimenez', 'Romero', 'Moreno', 'Alvarez', 'Ruiz', 'Mendez', 'Aguilar',
    'Fernandez', 'Navarro', 'Vega', 'Delgado', 'Molina', 'Campos', 'Santos', 'Guerrero', 'Medina', 'Castro'
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_spanish_phone() -> str:
    """Generate a realistic Spanish mobile phone number."""
    prefix = random.choice(['6', '7'])
    number = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    # Format: +34 6XX XXX XXX
    return f"+34 {prefix}{number[:2]} {number[2:5]} {number[5:]}"


def generate_email(first_name: str, last_name: str) -> str:
    """Generate a realistic email address."""
    domains = ['gmail.com', 'hotmail.com', 'yahoo.es', 'outlook.com', 'telefonica.net']
    separators = ['.', '_', '']
    separator = random.choice(separators)
    domain = random.choice(domains)

    base = f"{first_name.lower()}{separator}{last_name.lower()}"
    if random.random() > 0.7:
        base += str(random.randint(1, 99))

    return f"{base}@{domain}"


def weighted_choice(options: dict):
    """Select from options based on weights."""
    items = list(options.keys())
    weights = list(options.values())
    return random.choices(items, weights=weights, k=1)[0]


def get_occupancy_target(week_number: int, high_occupancy: bool = False) -> tuple:
    """Get occupancy target range for a week."""
    if high_occupancy:
        return HIGH_OCCUPANCY_WEEKDAY
    return WEEKLY_OCCUPANCY.get(week_number, (50, 70))


def get_week_number(start_date: datetime, current_date: datetime) -> int:
    """Get week number (1-based) from simulation start."""
    days_elapsed = (current_date - start_date).days
    return (days_elapsed // 7) + 1


def is_weekend(date: datetime) -> bool:
    """Check if date is weekend."""
    return date.weekday() >= 5  # Saturday=5, Sunday=6


# =============================================================================
# CUSTOMER GENERATION
# =============================================================================

def generate_customers(count: int, dry_run: bool = False) -> list:
    """
    Generate customers with realistic distribution.

    Args:
        count: Number of customers to generate
        dry_run: If True, don't actually create

    Returns:
        List of customer IDs created
    """
    customer_ids = []
    interno_count = int(count * CUSTOMER_INTERNO_RATIO)
    externo_count = count - interno_count
    vip_count = int(count * CUSTOMER_VIP_RATIO)

    # Track VIP assignments
    vip_indices = set(random.sample(range(count), vip_count))

    for i in range(count):
        first_name = random.choice(SPANISH_FIRST_NAMES)
        last_name = random.choice(SPANISH_LAST_NAMES)
        phone = generate_spanish_phone()
        is_vip = i in vip_indices

        if i < interno_count:
            # Internal customer (hotel guest)
            room_number = str(random.randint(101, 350))

            if not dry_run:
                customer_id = create_customer(
                    customer_type='interno',
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    room_number=room_number,
                    vip_status=1 if is_vip else 0,
                    country_code='+34'
                )
                customer_ids.append(customer_id)
        else:
            # External customer
            email = generate_email(first_name, last_name)

            if not dry_run:
                customer_id = create_customer(
                    customer_type='externo',
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    vip_status=1 if is_vip else 0,
                    country_code='+34'
                )
                customer_ids.append(customer_id)

    return customer_ids


# =============================================================================
# RESERVATION GENERATION
# =============================================================================

def get_state_distribution_for_date(reservation_date: datetime) -> dict:
    """
    Get the appropriate state distribution based on date.

    - Past dates: Completada, Cancelada, No-Show, Liberada
    - Today: Confirmada, Sentada, Cancelada, No-Show, Liberada
    - Future dates: Confirmada, Cancelada, Liberada
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if reservation_date.date() < today.date():
        return STATE_DISTRIBUTION_PAST
    elif reservation_date.date() == today.date():
        return STATE_DISTRIBUTION_TODAY
    else:
        return STATE_DISTRIBUTION_FUTURE


def generate_reservations_for_date(
    date: datetime,
    customers: list,
    furniture: list,
    occupancy_percent: int,
    dry_run: bool = False
) -> tuple:
    """
    Generate reservations for a specific date.

    Args:
        date: Target date
        customers: List of customer dicts
        furniture: List of available furniture dicts
        occupancy_percent: Target occupancy percentage
        dry_run: If True, don't actually create

    Returns:
        Tuple of (list of reservation IDs, count of reservations)
    """
    reservation_ids = []
    date_str = date.strftime('%Y-%m-%d')

    # Get appropriate state distribution for this date
    state_distribution = get_state_distribution_for_date(date)

    # Calculate how many furniture items to reserve
    available_furniture = [f for f in furniture if not f.get('is_temporary', False)]
    target_reservations = max(1, int(len(available_furniture) * (occupancy_percent / 100)))

    # Shuffle furniture for random selection
    shuffled_furniture = available_furniture.copy()
    random.shuffle(shuffled_furniture)

    # Track used furniture for this date
    used_furniture_ids = set()

    reservations_created = 0
    furniture_index = 0

    while reservations_created < target_reservations and furniture_index < len(shuffled_furniture):
        furn = shuffled_furniture[furniture_index]
        furniture_index += 1

        if furn['id'] in used_furniture_ids:
            continue

        # Select random customer
        customer = random.choice(customers)

        # Determine reservation type
        res_type = random.random()

        if res_type < RESERVATION_SINGLE_DAY_RATIO:
            # Single day reservation
            furniture_ids = [furn['id']]
            used_furniture_ids.add(furn['id'])

            # Add additional furniture sometimes (group booking)
            if random.random() < 0.2 and furniture_index < len(shuffled_furniture):
                extra_furn = shuffled_furniture[furniture_index]
                if extra_furn['id'] not in used_furniture_ids:
                    furniture_ids.append(extra_furn['id'])
                    used_furniture_ids.add(extra_furn['id'])
                    furniture_index += 1

            # Determine payment info
            if customer.get('customer_type') == 'interno':
                payment_method = weighted_choice(PAYMENT_INTERNO)
                charge_to_room = 1 if payment_method == 'cargo_habitacion' else 0
            else:
                payment_method = weighted_choice(PAYMENT_EXTERNO)
                charge_to_room = 0

            paid = 1 if payment_method else 0
            num_people = random.randint(1, max(1, min(4, furn.get('capacity', 4))))

            if not dry_run:
                try:
                    res_id, ticket = create_beach_reservation(
                        customer_id=customer['id'],
                        reservation_date=date_str,
                        num_people=num_people,
                        furniture_ids=furniture_ids,
                        payment_method=payment_method,
                        charge_to_room=charge_to_room,
                        paid=paid,
                        created_by='simulation'
                    )
                    reservation_ids.append(res_id)

                    # Change state based on distribution (excluding Confirmada which is default)
                    final_state = weighted_choice(state_distribution)
                    if final_state != 'Confirmada':
                        change_reservation_state(res_id, final_state, 'simulation', 'Simulacion automatica')

                except Exception as e:
                    # Log skipped reservations for debugging
                    logger.debug(f"Skipped single-day reservation on {date_str}: {e}")

            reservations_created += 1

        elif res_type < RESERVATION_SINGLE_DAY_RATIO + RESERVATION_MULTIDAY_RATIO:
            # Multi-day reservation (2-5 days)
            num_days = random.randint(2, 5)
            dates = [(date + timedelta(days=d)).strftime('%Y-%m-%d') for d in range(num_days)]

            furniture_ids = [furn['id']]
            used_furniture_ids.add(furn['id'])

            if customer.get('customer_type') == 'interno':
                payment_method = weighted_choice(PAYMENT_INTERNO)
                charge_to_room = 1 if payment_method == 'cargo_habitacion' else 0
            else:
                payment_method = weighted_choice(PAYMENT_EXTERNO)
                charge_to_room = 0

            paid = 1 if payment_method else 0
            num_people = random.randint(1, max(1, min(4, furn.get('capacity', 4))))

            if not dry_run:
                try:
                    result = create_linked_multiday_reservations(
                        customer_id=customer['id'],
                        dates=dates,
                        num_people=num_people,
                        furniture_ids=furniture_ids,
                        payment_method=payment_method,
                        charge_to_room=charge_to_room,
                        paid=paid,
                        created_by='simulation',
                        validate_availability=True,
                        validate_duplicates=False
                    )
                    if result['success']:
                        reservation_ids.append(result['parent_id'])
                        for child in result['children']:
                            reservation_ids.append(child['id'])

                        # Change state for parent (children inherit state handling)
                        final_state = weighted_choice(state_distribution)
                        if final_state != 'Confirmada':
                            change_reservation_state(result['parent_id'], final_state, 'simulation', 'Simulacion automatica')

                except Exception as e:
                    # Log skipped multi-day reservations for debugging
                    logger.debug(f"Skipped multi-day reservation starting {date_str}: {e}")

            reservations_created += 1

        else:
            # Walk-in - only valid for TODAY, otherwise treat as normal reservation
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            is_today = date.date() == today.date()

            furniture_ids = [furn['id']]
            used_furniture_ids.add(furn['id'])

            if customer.get('customer_type') == 'interno':
                payment_method = weighted_choice(PAYMENT_INTERNO)
                charge_to_room = 1 if payment_method == 'cargo_habitacion' else 0
            else:
                payment_method = weighted_choice(PAYMENT_EXTERNO)
                charge_to_room = 0

            paid = 1 if payment_method else 0
            num_people = random.randint(1, max(1, min(4, furn.get('capacity', 4))))

            if not dry_run:
                try:
                    res_id, ticket = create_beach_reservation(
                        customer_id=customer['id'],
                        reservation_date=date_str,
                        num_people=num_people,
                        furniture_ids=furniture_ids,
                        payment_method=payment_method,
                        charge_to_room=charge_to_room,
                        paid=paid,
                        created_by='simulation'
                    )
                    reservation_ids.append(res_id)

                    if is_today:
                        # Walk-ins go to Sentada only on today
                        change_reservation_state(res_id, 'Sentada', 'simulation', 'Walk-in simulado')
                    else:
                        # For other dates, use the state distribution (like normal reservations)
                        final_state = weighted_choice(state_distribution)
                        if final_state != 'Confirmada':
                            change_reservation_state(res_id, final_state, 'simulation', 'Simulacion automatica')

                except Exception as e:
                    # Log skipped walk-in reservations for debugging
                    logger.debug(f"Skipped walk-in reservation on {date_str}: {e}")

            reservations_created += 1

    return reservation_ids, reservations_created


# =============================================================================
# TEMPORARY FURNITURE GENERATION
# =============================================================================

def generate_temporary_furniture(
    start_date: datetime,
    zones: list,
    dry_run: bool = False
) -> list:
    """
    Generate temporary furniture for high-demand weekends.

    Args:
        start_date: Simulation start date
        zones: List of zone dicts
        dry_run: If True, don't actually create

    Returns:
        List of created furniture info
    """
    created = []

    if not zones:
        return created

    # Create 2-3 temporary items
    num_temp = random.randint(2, 3)

    # Find weekend dates in first two weeks
    weekend_dates = []
    for day_offset in range(14):
        check_date = start_date + timedelta(days=day_offset)
        if is_weekend(check_date):
            weekend_dates.append(check_date)

    if not weekend_dates:
        return created

    zone = random.choice(zones)

    for i in range(num_temp):
        if not weekend_dates:
            break

        # Pick a random weekend period (1-3 days)
        start_weekend = random.choice(weekend_dates)
        duration = random.randint(1, 3)
        end_weekend = start_weekend + timedelta(days=duration - 1)

        start_str = start_weekend.strftime('%Y-%m-%d')
        end_str = end_weekend.strftime('%Y-%m-%d')

        if not dry_run:
            number = get_next_temp_furniture_number('hamaca', zone['id'])

            furniture_id = create_temporary_furniture(
                zone_id=zone['id'],
                furniture_type='hamaca',
                number=number,
                capacity=2,
                position_x=random.randint(100, 500),
                position_y=random.randint(100, 300),
                start_date=start_str,
                end_date=end_str
            )

            created.append({
                'id': furniture_id,
                'number': number,
                'start_date': start_str,
                'end_date': end_str
            })
        else:
            created.append({
                'number': f'T{i+1}',
                'start_date': start_str,
                'end_date': end_str
            })

        # Remove used weekend dates
        weekend_dates = [d for d in weekend_dates if d < start_weekend or d > end_weekend]

    return created


# =============================================================================
# FURNITURE BLOCKS GENERATION
# =============================================================================

def generate_furniture_blocks(
    start_date: datetime,
    furniture: list,
    dry_run: bool = False
) -> list:
    """
    Generate furniture blocks (maintenance, VIP holds).

    Args:
        start_date: Simulation start date
        furniture: List of furniture dicts
        dry_run: If True, don't actually create

    Returns:
        List of created block info
    """
    created = []

    if not furniture:
        return created

    # Create 1-2 blocks
    num_blocks = random.randint(1, 2)
    block_types = ['maintenance', 'vip_hold']

    # Pick furniture items to block (avoid same item)
    available_furniture = [f for f in furniture if not f.get('is_temporary', False)]
    if len(available_furniture) < num_blocks:
        return created

    selected_furniture = random.sample(available_furniture, num_blocks)

    for i, furn in enumerate(selected_furniture):
        block_type = block_types[i % len(block_types)]

        # Random start date (week 2-4)
        day_offset = random.randint(7, 25)
        block_start = start_date + timedelta(days=day_offset)

        # Duration 1-5 days
        duration = random.randint(1, 5)
        block_end = block_start + timedelta(days=duration - 1)

        start_str = block_start.strftime('%Y-%m-%d')
        end_str = block_end.strftime('%Y-%m-%d')

        reason = 'Mantenimiento programado' if block_type == 'maintenance' else 'Reserva VIP especial'

        if not dry_run:
            block_id = create_furniture_block(
                furniture_id=furn['id'],
                start_date=start_str,
                end_date=end_str,
                block_type=block_type,
                reason=reason,
                created_by='simulation'
            )

            created.append({
                'id': block_id,
                'furniture_number': furn['number'],
                'type': block_type,
                'start_date': start_str,
                'end_date': end_str
            })
        else:
            created.append({
                'furniture_number': furn['number'],
                'type': block_type,
                'start_date': start_str,
                'end_date': end_str
            })

    return created


# =============================================================================
# MAIN SIMULATION
# =============================================================================

def run_simulation(start_date: datetime, dry_run: bool = False, high_occupancy: bool = False) -> dict:
    """
    Run the full month simulation.

    Args:
        start_date: Simulation start date
        dry_run: If True, don't actually create anything
        high_occupancy: If True, force 80-100% occupancy every day

    Returns:
        Summary of created data
    """
    end_date = start_date + timedelta(days=30)

    # Print header
    print("=" * 60)
    print("BEACH CLUB MONTH SIMULATION")
    print("=" * 60)
    print(f"Start Date: {start_date.strftime('%Y-%m-%d')}")
    print(f"End Date: {end_date.strftime('%Y-%m-%d')}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE'}")
    print(f"High Occupancy: {'YES (80-100% weekdays, 95-100% weekends)' if high_occupancy else 'NO (normal pattern)'}")
    print("=" * 60)
    print()

    results = {
        'customers_created': 0,
        'reservations_created': 0,
        'temporary_furniture': 0,
        'furniture_blocks': 0,
        'days_processed': 0,
        'weekly_stats': {}
    }

    # Step 1: Load existing data
    print("[1/5] Loading existing data...")
    zones = get_all_zones(active_only=True)
    furniture = get_all_furniture(active_only=True)
    existing_customers = get_all_customers()
    print(f"  Found {len(zones)} zones, {len(furniture)} furniture items, {len(existing_customers)} existing customers")
    print()

    # Step 2: Generate customers
    print("[2/5] Generating customers...")
    customer_count = 100
    if not dry_run:
        customer_ids = generate_customers(customer_count, dry_run=False)
        results['customers_created'] = len(customer_ids)
        # Reload customers
        all_customers = get_all_customers()
    else:
        generate_customers(customer_count, dry_run=True)
        results['customers_created'] = customer_count
        all_customers = existing_customers if existing_customers else [{'id': i, 'customer_type': 'interno' if i < 60 else 'externo'} for i in range(100)]
    print(f"  {'Would create' if dry_run else 'Created'} {customer_count} customers")
    print()

    # Step 3: Generate temporary furniture
    print("[3/5] Generating temporary furniture...")
    temp_furniture = generate_temporary_furniture(start_date, zones, dry_run)
    results['temporary_furniture'] = len(temp_furniture)
    for tf in temp_furniture:
        print(f"  {'Would create' if dry_run else 'Created'} {tf['number']}: {tf['start_date']} to {tf['end_date']}")
    print()

    # Step 4: Generate furniture blocks
    print("[4/5] Generating furniture blocks...")
    blocks = generate_furniture_blocks(start_date, furniture, dry_run)
    results['furniture_blocks'] = len(blocks)
    for block in blocks:
        print(f"  {'Would create' if dry_run else 'Created'} {block['type']} block on {block['furniture_number']}: {block['start_date']} to {block['end_date']}")
    print()

    # Step 5: Generate reservations
    print("[5/5] Generating reservations...")

    current_week = 0
    week_reservations = 0
    week_start = start_date

    current_date = start_date
    while current_date <= end_date:
        week_num = get_week_number(start_date, current_date)

        # Track weekly progress
        if week_num != current_week:
            if current_week > 0:
                min_occ, max_occ = get_occupancy_target(current_week, high_occupancy)
                target_avg = (min_occ + max_occ) / 2
                results['weekly_stats'][current_week] = week_reservations
                print(f"  Week {current_week} complete: {week_reservations} reservations, ~{int(target_avg)}% target occupancy")

            current_week = week_num
            week_reservations = 0
            week_start = current_date

        # Get occupancy target for current week
        if high_occupancy and is_weekend(current_date):
            min_occupancy, max_occupancy = HIGH_OCCUPANCY_WEEKEND
        else:
            min_occupancy, max_occupancy = get_occupancy_target(week_num, high_occupancy)

        occupancy = random.randint(min_occupancy, max_occupancy)

        # Reload furniture for this date (to include temp furniture)
        date_str = current_date.strftime('%Y-%m-%d')
        date_furniture = get_all_furniture(active_only=True, for_date=date_str) if not dry_run else furniture

        # Generate reservations for this date
        day_reservation_ids, day_count = generate_reservations_for_date(
            current_date,
            all_customers,
            date_furniture,
            occupancy,
            dry_run
        )

        # In dry-run mode, count estimated reservations; in live mode, count actual
        actual_count = len(day_reservation_ids) if not dry_run else day_count
        results['reservations_created'] += actual_count
        week_reservations += actual_count
        results['days_processed'] += 1

        current_date += timedelta(days=1)

    # Final week stats
    if current_week > 0:
        min_occ, max_occ = get_occupancy_target(current_week, high_occupancy)
        target_avg = (min_occ + max_occ) / 2
        results['weekly_stats'][current_week] = week_reservations
        print(f"  Week {current_week} complete: {week_reservations} reservations, ~{int(target_avg)}% target occupancy")

    print()

    # Print summary
    print("=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"  Customers created: {results['customers_created']}")
    print(f"  Reservations created: {results['reservations_created']}")
    print(f"  Temporary furniture: {results['temporary_furniture']}")
    print(f"  Furniture blocks: {results['furniture_blocks']}")
    print(f"  Days processed: {results['days_processed']}")
    print("=" * 60)

    return results


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate one month of beach club simulation data'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be created without making changes')
    parser.add_argument('--start-date', type=str, default=None,
                        help='Start date for simulation (YYYY-MM-DD). Default: today')
    parser.add_argument('--month', type=str, default=None,
                        help='Month for simulation (YYYY-MM). Alternative to --start-date')
    parser.add_argument('--high-occupancy', action='store_true',
                        help='Force 80-100%% occupancy every day (stress test mode)')
    parser.add_argument('--sim-db', action='store_true',
                        help=f'Use simulation database: {SIM_DB_PATH}')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show debug output including skipped reservations')

    args = parser.parse_args()

    # Set simulation database BEFORE creating Flask app
    if args.sim_db:
        if not os.path.exists(SIM_DB_PATH):
            print(f"Error: Simulation database not found at {SIM_DB_PATH}")
            print("Run: cp instance/beach_club.db database/beach_club_sim.db")
            sys.exit(1)
        os.environ['DATABASE_PATH'] = SIM_DB_PATH
        print(f"Using simulation database: {SIM_DB_PATH}")

    # Create Flask app AFTER setting DATABASE_PATH
    from app import create_app
    app = create_app('development')

    if args.verbose:
        logging.getLogger(__name__).setLevel(logging.DEBUG)

    # Parse start date
    if args.month:
        try:
            start_date = datetime.strptime(args.month, '%Y-%m')
        except ValueError:
            print(f"Error: Invalid month format '{args.month}'. Use YYYY-MM")
            sys.exit(1)
    elif args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    with app.app_context():
        try:
            results = run_simulation(
                start_date,
                dry_run=args.dry_run,
                high_occupancy=args.high_occupancy
            )
            sys.exit(0)
        except Exception as e:
            print(f"\nError during simulation: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
