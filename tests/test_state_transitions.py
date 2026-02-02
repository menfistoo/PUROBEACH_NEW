"""
Tests for state transition validation.

Validates that the VALID_TRANSITIONS matrix exists as reference/documentation
and that validation works when explicitly enabled (bypass_validation=False).
By default, validation is BYPASSED so users can freely choose any state.
"""

import pytest
from datetime import date, timedelta


@pytest.fixture
def setup_transition_test_data(app):
    """Setup test data for state transition tests."""
    from database import get_db

    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Get zone
        cursor.execute('SELECT id FROM beach_zones LIMIT 1')
        zone = cursor.fetchone()
        zone_id = zone['id'] if zone else 1

        # Create test furniture
        cursor.execute('''
            INSERT INTO beach_furniture (number, zone_id, furniture_type, capacity, active)
            VALUES ('TRANS_TEST_01', ?, 'hamaca', 2, 1)
        ''', (zone_id,))
        furniture_id = cursor.lastrowid

        # Create test customer
        cursor.execute('''
            INSERT INTO beach_customers (customer_type, first_name, last_name, phone)
            VALUES ('externo', 'Transition', 'TestCustomer', '600999001')
        ''')
        customer_id = cursor.lastrowid

        # Get state IDs
        state_ids = {}
        for name in ['Confirmada', 'Sentada', 'Cancelada', 'No-Show', 'Liberada', 'Completada']:
            cursor.execute("SELECT id FROM beach_reservation_states WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                state_ids[name] = row['id']

        db.commit()

        yield {
            'furniture_id': furniture_id,
            'customer_id': customer_id,
            'zone_id': zone_id,
            'state_ids': state_ids,
        }


def _create_reservation(app, customer_id, state_name, state_id, date_offset=0):
    """Helper to create a reservation with a given state."""
    from database import get_db

    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        test_date = (date.today() + timedelta(days=200 + date_offset)).isoformat()

        cursor.execute('''
            INSERT INTO beach_reservations (
                customer_id, ticket_number, reservation_date, start_date, end_date,
                num_people, current_states, current_state, state_id
            ) VALUES (?, ?, ?, ?, ?, 2, ?, ?, ?)
        ''', (customer_id, f'TRANS-{date_offset}', test_date, test_date, test_date,
              state_name, state_name, state_id))
        reservation_id = cursor.lastrowid
        db.commit()
        return reservation_id


class TestValidateStateTransition:
    """Tests for the validate_state_transition function.

    By default, bypass_validation=True so all transitions pass.
    Tests verify that:
    1. Default behavior allows ANY transition (no enforcement)
    2. Explicit bypass_validation=False re-enables enforcement
    3. VALID_TRANSITIONS dict is kept as reference
    """

    def test_default_allows_any_transition(self, app):
        """Default (bypass_validation=True) should allow any transition."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            # All of these should pass with default bypass_validation=True
            validate_state_transition('Completada', 'Confirmada')
            validate_state_transition('Liberada', 'Sentada')
            validate_state_transition('Confirmada', 'Completada')
            validate_state_transition('Sentada', 'No-Show')
            validate_state_transition(None, 'Cancelada')
            validate_state_transition('', 'Sentada')

    def test_explicit_enforcement_rejects_invalid(self, app):
        """bypass_validation=False should enforce the transition matrix."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError):
                validate_state_transition('Completada', 'Confirmada', bypass_validation=False)

    def test_explicit_enforcement_allows_valid(self, app):
        """bypass_validation=False should still allow valid transitions."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Confirmada', 'Sentada', bypass_validation=False)
            validate_state_transition('Confirmada', 'Cancelada', bypass_validation=False)
            validate_state_transition('Sentada', 'Completada', bypass_validation=False)

    def test_error_message_in_spanish_when_enforced(self, app):
        """Error messages should be in Spanish when enforcement is on."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Confirmada', 'Completada', bypass_validation=False)
            msg = str(exc_info.value)
            assert 'No se puede cambiar' in msg

    def test_error_message_lists_allowed_when_enforced(self, app):
        """Error message should list allowed transitions when enforcement is on."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Confirmada', 'Completada', bypass_validation=False)
            msg = str(exc_info.value)
            assert 'Transiciones permitidas' in msg
            assert 'Cancelada' in msg
            assert 'Sentada' in msg

    def test_unknown_state_allows_transition_when_enforced(self, app):
        """Unknown/custom states not in matrix should allow any transition even when enforced."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('CustomState', 'Confirmada', bypass_validation=False)


class TestGetAllowedTransitions:
    """Tests for the get_allowed_transitions function.

    These verify the VALID_TRANSITIONS reference data is intact.
    The data is used for UI hints (suggested next states).
    """

    def test_confirmada_transitions(self, app):
        """Confirmada should suggest Sentada, Cancelada, No-Show."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('Confirmada')
            assert allowed == {'Sentada', 'Cancelada', 'No-Show'}

    def test_completada_transitions(self, app):
        """Completada suggests no transitions (terminal reference)."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('Completada')
            assert allowed == set()

    def test_cancelada_transitions(self, app):
        """Cancelada suggests reopening to Confirmada."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('Cancelada')
            assert allowed == {'Confirmada'}

    def test_unknown_state_returns_empty(self, app):
        """Unknown state returns empty set."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('NonExistentState')
            assert allowed == set()


class TestGetValidTransitions:
    """Tests for the get_valid_transitions function (reference data)."""

    def test_returns_copy(self, app):
        """Should return a copy, not the original."""
        from models.reservation_state import get_valid_transitions, VALID_TRANSITIONS

        with app.app_context():
            transitions = get_valid_transitions()
            # Modify the returned copy
            transitions['Confirmada'].add('SomeNewState')
            # Original should be unchanged
            assert 'SomeNewState' not in VALID_TRANSITIONS['Confirmada']

    def test_contains_all_seeded_states(self, app):
        """Matrix should contain all seeded states as reference."""
        from models.reservation_state import VALID_TRANSITIONS

        with app.app_context():
            seeded_states = ['Confirmada', 'Sentada', 'Cancelada', 'No-Show', 'Liberada', 'Completada']
            for state in seeded_states:
                assert state in VALID_TRANSITIONS, f"State '{state}' not in transition matrix"


class TestStateTransitionIntegration:
    """Integration tests: verify transitions work freely by default."""

    def test_add_state_allows_any_transition_by_default(self, app, setup_transition_test_data):
        """add_reservation_state should allow any transition by default (no enforcement)."""
        from models.reservation_state import add_reservation_state

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state (was terminal with enforcement)
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=10
            )

            # Adding Confirmada to a Completada reservation should now work
            result = add_reservation_state(reservation_id, 'Confirmada', changed_by='test')
            assert result is True

    def test_add_state_enforces_when_bypass_false(self, app, setup_transition_test_data):
        """add_reservation_state should enforce when bypass_validation=False."""
        from models.reservation_state import add_reservation_state, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=11
            )

            with pytest.raises(InvalidStateTransitionError):
                add_reservation_state(reservation_id, 'Confirmada', changed_by='test',
                                      bypass_validation=False)

    def test_change_state_allows_any_transition_by_default(self, app, setup_transition_test_data):
        """change_reservation_state should allow any transition by default."""
        from models.reservation_state import change_reservation_state

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=12
            )

            # Changing to Confirmada should work (was blocked before)
            result = change_reservation_state(reservation_id, 'Confirmada', changed_by='test')
            assert result is True

    def test_change_state_enforces_when_bypass_false(self, app, setup_transition_test_data):
        """change_reservation_state should enforce when bypass_validation=False."""
        from models.reservation_state import change_reservation_state, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=13
            )

            with pytest.raises(InvalidStateTransitionError):
                change_reservation_state(reservation_id, 'Confirmada', changed_by='test',
                                          bypass_validation=False)

    def test_cancel_allows_from_any_state_by_default(self, app, setup_transition_test_data):
        """cancel_beach_reservation should work from any state by default."""
        from models.reservation_state import cancel_beach_reservation

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state (terminal)
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=14
            )

            # Cancelling a completed reservation should now work
            result = cancel_beach_reservation(reservation_id, cancelled_by='test')
            assert result is True

    def test_cancel_enforces_when_bypass_false(self, app, setup_transition_test_data):
        """cancel_beach_reservation should enforce when bypass_validation=False."""
        from models.reservation_state import cancel_beach_reservation, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=15
            )

            with pytest.raises(InvalidStateTransitionError):
                cancel_beach_reservation(reservation_id, cancelled_by='test',
                                          bypass_validation=False)

    def test_full_lifecycle_flow(self, app, setup_transition_test_data):
        """Test a full lifecycle: Confirmada -> Sentada -> Completada."""
        from models.reservation_state import add_reservation_state
        from database import get_db

        data = setup_transition_test_data

        with app.app_context():
            # Start with Confirmada
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Confirmada',
                data['state_ids'].get('Confirmada'), date_offset=16
            )

            # Step 1: Confirmada -> Sentada
            result = add_reservation_state(reservation_id, 'Sentada', changed_by='test')
            assert result is True

            # Step 2: Sentada -> Completada
            result = add_reservation_state(reservation_id, 'Completada', changed_by='test')
            assert result is True

            # Verify final state
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT current_state FROM beach_reservations WHERE id = ?',
                          (reservation_id,))
            row = cursor.fetchone()
            assert row['current_state'] == 'Completada'

    def test_free_form_state_changes(self, app, setup_transition_test_data):
        """Test that users can freely pick any state without restrictions."""
        from models.reservation_state import change_reservation_state
        from database import get_db

        data = setup_transition_test_data

        with app.app_context():
            # Start with Confirmada
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Confirmada',
                data['state_ids'].get('Confirmada'), date_offset=17
            )

            # Jump directly to Completada (skipping Sentada) - previously blocked
            result = change_reservation_state(reservation_id, 'Completada', changed_by='test')
            assert result is True

            # Go back to Confirmada from Completada - previously blocked (terminal)
            result = change_reservation_state(reservation_id, 'Confirmada', changed_by='test')
            assert result is True

            # Jump to Liberada from Confirmada - previously blocked
            result = change_reservation_state(reservation_id, 'Liberada', changed_by='test')
            assert result is True

            # Come back from Liberada - previously blocked (terminal)
            result = change_reservation_state(reservation_id, 'Sentada', changed_by='test')
            assert result is True

            # Verify final state
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT current_state FROM beach_reservations WHERE id = ?',
                          (reservation_id,))
            row = cursor.fetchone()
            assert row['current_state'] == 'Sentada'
