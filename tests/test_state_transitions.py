"""
Tests for state transition validation.

Validates that the state transition matrix is enforced correctly,
preventing invalid flows like Completada -> Pendiente.
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
    """Tests for the validate_state_transition function."""

    def test_valid_transition_confirmada_to_sentada(self, app):
        """Confirmada -> Sentada should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            # Should not raise
            validate_state_transition('Confirmada', 'Sentada')

    def test_valid_transition_confirmada_to_cancelada(self, app):
        """Confirmada -> Cancelada should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Confirmada', 'Cancelada')

    def test_valid_transition_confirmada_to_noshow(self, app):
        """Confirmada -> No-Show should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Confirmada', 'No-Show')

    def test_valid_transition_sentada_to_completada(self, app):
        """Sentada -> Completada should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Sentada', 'Completada')

    def test_valid_transition_sentada_to_cancelada(self, app):
        """Sentada -> Cancelada should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Sentada', 'Cancelada')

    def test_valid_transition_sentada_to_liberada(self, app):
        """Sentada -> Liberada should be allowed."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Sentada', 'Liberada')

    def test_valid_transition_cancelada_to_confirmada(self, app):
        """Cancelada -> Confirmada should be allowed (reopen)."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('Cancelada', 'Confirmada')

    def test_valid_transition_noshow_to_confirmada(self, app):
        """No-Show -> Confirmada should be allowed (reopen)."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition('No-Show', 'Confirmada')

    def test_valid_transition_from_none(self, app):
        """None -> Confirmada should be allowed (new reservation)."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            validate_state_transition(None, 'Confirmada')
            validate_state_transition('', 'Confirmada')

    def test_invalid_transition_completada_to_confirmada(self, app):
        """Completada -> Confirmada should be rejected (terminal state)."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Completada', 'Confirmada')
            assert 'Completada' in str(exc_info.value)
            assert 'terminal' in str(exc_info.value).lower()

    def test_invalid_transition_completada_to_sentada(self, app):
        """Completada -> Sentada should be rejected."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError):
                validate_state_transition('Completada', 'Sentada')

    def test_invalid_transition_liberada_to_anything(self, app):
        """Liberada is terminal - no transitions allowed."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            for target in ['Confirmada', 'Sentada', 'Cancelada', 'No-Show', 'Completada']:
                with pytest.raises(InvalidStateTransitionError):
                    validate_state_transition('Liberada', target)

    def test_invalid_transition_confirmada_to_completada(self, app):
        """Confirmada -> Completada should be rejected (must go through Sentada)."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Confirmada', 'Completada')
            assert 'Confirmada' in str(exc_info.value)
            assert 'Completada' in str(exc_info.value)

    def test_invalid_transition_sentada_to_noshow(self, app):
        """Sentada -> No-Show should be rejected (No-Show only from Confirmada)."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError):
                validate_state_transition('Sentada', 'No-Show')

    def test_invalid_transition_cancelada_to_completada(self, app):
        """Cancelada -> Completada should be rejected."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError):
                validate_state_transition('Cancelada', 'Completada')

    def test_bypass_validation_allows_any_transition(self, app):
        """bypass_validation=True should allow any transition."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            # These would normally fail
            validate_state_transition('Completada', 'Confirmada', bypass_validation=True)
            validate_state_transition('Liberada', 'Sentada', bypass_validation=True)

    def test_error_message_in_spanish(self, app):
        """Error messages should be in Spanish."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Confirmada', 'Completada')
            msg = str(exc_info.value)
            assert 'No se puede cambiar' in msg

    def test_error_message_lists_allowed_transitions(self, app):
        """Error message should list allowed transitions."""
        from models.reservation_state import validate_state_transition, InvalidStateTransitionError

        with app.app_context():
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                validate_state_transition('Confirmada', 'Completada')
            msg = str(exc_info.value)
            assert 'Transiciones permitidas' in msg
            # Should list valid targets
            assert 'Cancelada' in msg
            assert 'Sentada' in msg

    def test_unknown_state_allows_transition(self, app):
        """Unknown/custom states not in matrix should allow any transition."""
        from models.reservation_state import validate_state_transition

        with app.app_context():
            # Custom state not in matrix - should not raise
            validate_state_transition('CustomState', 'Confirmada')


class TestGetAllowedTransitions:
    """Tests for the get_allowed_transitions function."""

    def test_confirmada_transitions(self, app):
        """Confirmada should allow Sentada, Cancelada, No-Show."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('Confirmada')
            assert allowed == {'Sentada', 'Cancelada', 'No-Show'}

    def test_completada_transitions(self, app):
        """Completada is terminal - no transitions."""
        from models.reservation_state import get_allowed_transitions

        with app.app_context():
            allowed = get_allowed_transitions('Completada')
            assert allowed == set()

    def test_cancelada_transitions(self, app):
        """Cancelada allows reopening to Confirmada."""
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
    """Tests for the get_valid_transitions function."""

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
        """Matrix should contain all seeded states."""
        from models.reservation_state import VALID_TRANSITIONS

        with app.app_context():
            seeded_states = ['Confirmada', 'Sentada', 'Cancelada', 'No-Show', 'Liberada', 'Completada']
            for state in seeded_states:
                assert state in VALID_TRANSITIONS, f"State '{state}' not in transition matrix"


class TestStateTransitionIntegration:
    """Integration tests: validate transitions through actual model functions."""

    def test_add_state_validates_transition(self, app, setup_transition_test_data):
        """add_reservation_state should enforce transition validation."""
        from models.reservation_state import add_reservation_state, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=10
            )

            # Trying to add Confirmada to a Completada reservation should fail
            with pytest.raises(InvalidStateTransitionError):
                add_reservation_state(reservation_id, 'Confirmada', changed_by='test')

    def test_add_state_allows_valid_transition(self, app, setup_transition_test_data):
        """add_reservation_state should allow valid transitions."""
        from models.reservation_state import add_reservation_state

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Confirmada state
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Confirmada',
                data['state_ids'].get('Confirmada'), date_offset=11
            )

            # Transition to Sentada should work
            result = add_reservation_state(reservation_id, 'Sentada', changed_by='test')
            assert result is True

    def test_change_state_validates_transition(self, app, setup_transition_test_data):
        """change_reservation_state should enforce transition validation."""
        from models.reservation_state import change_reservation_state, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=12
            )

            # Trying to change to Confirmada should fail
            with pytest.raises(InvalidStateTransitionError):
                change_reservation_state(reservation_id, 'Confirmada', changed_by='test')

    def test_change_state_allows_valid_transition(self, app, setup_transition_test_data):
        """change_reservation_state should allow valid transitions."""
        from models.reservation_state import change_reservation_state

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Confirmada state
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Confirmada',
                data['state_ids'].get('Confirmada'), date_offset=13
            )

            # Transition to Cancelada should work
            result = change_reservation_state(reservation_id, 'Cancelada', changed_by='test')
            assert result is True

    def test_cancel_shortcut_validates_transition(self, app, setup_transition_test_data):
        """cancel_beach_reservation should enforce transition validation."""
        from models.reservation_state import cancel_beach_reservation, InvalidStateTransitionError

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state (terminal)
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=14
            )

            # Cancelling a completed reservation should fail
            with pytest.raises(InvalidStateTransitionError):
                cancel_beach_reservation(reservation_id, cancelled_by='test')

    def test_cancel_shortcut_bypass_works(self, app, setup_transition_test_data):
        """cancel_beach_reservation with bypass should always work."""
        from models.reservation_state import cancel_beach_reservation

        data = setup_transition_test_data

        with app.app_context():
            # Create reservation in Completada state (terminal)
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Completada',
                data['state_ids'].get('Completada'), date_offset=15
            )

            # Bypass should allow it
            result = cancel_beach_reservation(
                reservation_id, cancelled_by='test', bypass_validation=True
            )
            assert result is True

    def test_full_lifecycle_flow(self, app, setup_transition_test_data):
        """Test a full valid lifecycle: Confirmada -> Sentada -> Completada."""
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

    def test_reopen_cancelled_reservation(self, app, setup_transition_test_data):
        """Test reopening: Confirmada -> Cancelada -> Confirmada."""
        from models.reservation_state import add_reservation_state, change_reservation_state
        from database import get_db

        data = setup_transition_test_data

        with app.app_context():
            # Start with Confirmada
            reservation_id = _create_reservation(
                app, data['customer_id'], 'Confirmada',
                data['state_ids'].get('Confirmada'), date_offset=17
            )

            # Cancel it
            result = add_reservation_state(reservation_id, 'Cancelada', changed_by='test')
            assert result is True

            # Reopen it by changing state (not adding, since CSV accumulation
            # would keep Cancelada as the current state due to priority)
            result = change_reservation_state(reservation_id, 'Confirmada', changed_by='test')
            assert result is True

            # Verify
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT current_state FROM beach_reservations WHERE id = ?',
                          (reservation_id,))
            row = cursor.fetchone()
            assert row['current_state'] == 'Confirmada'
