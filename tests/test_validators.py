"""
Tests for input validation utilities.
"""

import pytest
from utils.validators import (
    normalize_phone,
    validate_email,
    validate_phone,
    validate_date_range,
    validate_room_number,
    validate_password,
    validate_date_format,
    sanitize_input
)


class TestNormalizePhone:
    """Tests for phone number normalization."""

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert normalize_phone(None) is None

    def test_empty_returns_empty(self):
        """Test that empty string returns empty string."""
        assert normalize_phone('') == ''

    def test_strips_spaces(self):
        """Test that spaces are removed."""
        assert normalize_phone('666 123 456') == '666123456'

    def test_strips_dashes(self):
        """Test that dashes are removed."""
        assert normalize_phone('666-123-456') == '666123456'

    def test_strips_parentheses(self):
        """Test that parentheses are removed."""
        assert normalize_phone('(666) 123 456') == '666123456'

    def test_strips_dots(self):
        """Test that dots are removed."""
        assert normalize_phone('666.123.456') == '666123456'

    def test_removes_plus_34_prefix(self):
        """Test removal of +34 country code."""
        assert normalize_phone('+34 666-123-456') == '666123456'
        assert normalize_phone('+34666123456') == '666123456'

    def test_removes_0034_prefix(self):
        """Test removal of 0034 country code."""
        assert normalize_phone('0034666123456') == '666123456'
        assert normalize_phone('00 34 666123456') == '666123456'

    def test_removes_34_prefix_when_longer_than_9_digits(self):
        """Test removal of 34 prefix when total digits > 9."""
        assert normalize_phone('34666123456') == '666123456'

    def test_keeps_34_prefix_when_9_or_fewer_digits(self):
        """Test that 34 is NOT stripped when total is 9 digits or fewer (not a country code)."""
        # '345678901' is 9 digits, starts with 34 but is not a country code prefix
        assert normalize_phone('345678901') == '345678901'

    def test_plain_number_unchanged(self):
        """Test that a plain digit-only number is returned as-is."""
        assert normalize_phone('666123456') == '666123456'

    def test_international_format_with_spaces(self):
        """Test full international format with mixed separators."""
        assert normalize_phone('+34 666 123 456') == '666123456'

    def test_whitespace_only_returns_empty(self):
        """Test that whitespace-only input returns empty string."""
        assert normalize_phone('   ') == ''

    def test_non_digit_only_returns_empty(self):
        """Test that input with no digits returns empty string."""
        assert normalize_phone('abc') == ''

    def test_mixed_separators(self):
        """Test phone with mixed separator characters."""
        assert normalize_phone('+34-(666) 123.456') == '666123456'


class TestValidateEmail:
    """Tests for email validation."""

    def test_valid_email(self):
        """Test valid email formats."""
        assert validate_email('user@example.com') is True
        assert validate_email('user.name@example.com') is True
        assert validate_email('user+tag@example.co.uk') is True
        assert validate_email('user123@domain.org') is True

    def test_invalid_email(self):
        """Test invalid email formats."""
        assert validate_email('') is False
        assert validate_email(None) is False
        assert validate_email('invalid') is False
        assert validate_email('missing@domain') is False
        assert validate_email('@nodomain.com') is False
        assert validate_email('spaces in@email.com') is False


class TestValidatePhone:
    """Tests for Spanish phone validation."""

    def test_valid_spanish_phones(self):
        """Test valid Spanish phone formats."""
        assert validate_phone('+34612345678') is True
        assert validate_phone('34612345678') is True
        assert validate_phone('612345678') is True
        assert validate_phone('912345678') is True
        assert validate_phone('712345678') is True
        assert validate_phone('812345678') is True

    def test_valid_phones_with_separators(self):
        """Test phones with spaces and separators."""
        assert validate_phone('+34 612 345 678') is True
        assert validate_phone('612 345 678') is True
        assert validate_phone('612-345-678') is True
        assert validate_phone('(612) 345 678') is True

    def test_invalid_phones(self):
        """Test invalid phone formats."""
        assert validate_phone('') is False
        assert validate_phone(None) is False
        assert validate_phone('123456789') is False  # Doesn't start with 6-9
        assert validate_phone('12345') is False  # Too short
        assert validate_phone('abc123456') is False  # Contains letters


class TestValidateDateRange:
    """Tests for date range validation."""

    def test_valid_date_range(self):
        """Test valid date ranges."""
        assert validate_date_range('2025-01-01', '2025-01-05') is True
        assert validate_date_range('2025-01-01', '2025-01-01') is True  # Same day
        assert validate_date_range('2024-12-31', '2025-01-01') is True

    def test_invalid_date_range(self):
        """Test invalid date ranges (end before start)."""
        assert validate_date_range('2025-01-05', '2025-01-01') is False

    def test_invalid_date_format(self):
        """Test invalid date formats."""
        assert validate_date_range('01-01-2025', '05-01-2025') is False
        assert validate_date_range('invalid', '2025-01-01') is False
        assert validate_date_range('2025-01-01', 'invalid') is False


class TestValidateRoomNumber:
    """Tests for room number validation."""

    def test_valid_room_numbers(self):
        """Test valid room number formats."""
        assert validate_room_number('101') is True
        assert validate_room_number('A12') is True
        assert validate_room_number('SU01') is True
        assert validate_room_number('1') is True
        assert validate_room_number('PENT1') is True

    def test_invalid_room_numbers(self):
        """Test invalid room number formats."""
        assert validate_room_number('') is False
        assert validate_room_number(None) is False
        assert validate_room_number('VERYLONGROOM') is False  # Too long
        assert validate_room_number('room-101') is False  # Contains hyphen


class TestValidatePassword:
    """Tests for password validation."""

    def test_valid_password(self):
        """Test valid passwords with uppercase, lowercase, and digit."""
        is_valid, msg = validate_password('Password1')
        assert is_valid is True
        assert msg == ''

    def test_valid_password_custom_length(self):
        """Test password with custom minimum length."""
        is_valid, msg = validate_password('Abcdefgh1', min_length=8)
        assert is_valid is True

    def test_password_too_short(self):
        """Test password too short."""
        is_valid, msg = validate_password('Pass1')
        assert is_valid is False
        assert 'al menos 8 caracteres' in msg

    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        is_valid, msg = validate_password('password1')
        assert is_valid is False
        assert 'mayúscula' in msg

    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        is_valid, msg = validate_password('PASSWORD1')
        assert is_valid is False
        assert 'minúscula' in msg

    def test_password_no_digit(self):
        """Test password without digit."""
        is_valid, msg = validate_password('Passwordx')
        assert is_valid is False
        assert 'número' in msg

    def test_password_empty(self):
        """Test empty password."""
        is_valid, msg = validate_password('')
        assert is_valid is False
        assert 'requerida' in msg

    def test_password_none(self):
        """Test None password."""
        is_valid, msg = validate_password(None)
        assert is_valid is False


class TestValidateDateFormat:
    """Tests for date format validation."""

    def test_valid_date_format(self):
        """Test valid YYYY-MM-DD format."""
        assert validate_date_format('2025-01-15') is True
        assert validate_date_format('2025-12-31') is True
        assert validate_date_format('2020-02-29') is True  # Leap year

    def test_invalid_date_format(self):
        """Test invalid date formats."""
        assert validate_date_format('15-01-2025') is False  # DD-MM-YYYY
        assert validate_date_format('01/15/2025') is False  # MM/DD/YYYY
        assert validate_date_format('2025/01/15') is False  # Wrong separator
        assert validate_date_format('invalid') is False
        assert validate_date_format('') is False

    def test_invalid_date_values(self):
        """Test invalid date values."""
        assert validate_date_format('2025-13-01') is False  # Invalid month
        assert validate_date_format('2025-01-32') is False  # Invalid day
        assert validate_date_format('2021-02-29') is False  # Not leap year


class TestSanitizeInput:
    """Tests for input sanitization."""

    def test_trim_whitespace(self):
        """Test trimming whitespace."""
        assert sanitize_input('  hello  ') == 'hello'
        assert sanitize_input('\n\ttext\n') == 'text'

    def test_limit_length(self):
        """Test limiting input length."""
        assert sanitize_input('hello world', max_length=5) == 'hello'
        assert sanitize_input('short', max_length=10) == 'short'

    def test_empty_input(self):
        """Test empty input handling."""
        assert sanitize_input('') == ''
        assert sanitize_input(None) == ''

    def test_no_modification_needed(self):
        """Test input that doesn't need modification."""
        assert sanitize_input('clean input') == 'clean input'
