"""Unit tests for validator service"""

import pytest
from datetime import datetime, date
from app.services.validator import (
    ValidationError,
    validate_required,
    validate_type,
    validate_length,
    validate_format,
    validate_range,
    validate_row,
    validate_rows,
)


class TestValidationError:
    """Tests for ValidationError class"""

    def test_validation_error_creation(self):
        """Test creating ValidationError"""
        error = ValidationError(
            column="email",
            error_type="format",
            message="Invalid email format",
            value="invalid-email",
        )

        assert error.column == "email"
        assert error.error_type == "format"
        assert error.message == "Invalid email format"
        assert error.value == "invalid-email"

    def test_validation_error_to_dict(self):
        """Test ValidationError.to_dict() method"""
        error = ValidationError(
            column="age", error_type="range", message="Value out of range", value=150
        )

        result = error.to_dict()

        assert result == {
            "column": "age",
            "error_type": "range",
            "message": "Value out of range",
            "value": 150,
        }


class TestValidateRequired:
    """Tests for validate_required function"""

    def test_validate_required_valid(self):
        """Test required validation passes with value"""
        assert validate_required("email", "alice@example.com") is None
        assert validate_required("count", 0) is None
        assert validate_required("flag", False) is None

    def test_validate_required_none_value(self):
        """Test required validation fails with None"""
        error = validate_required("email", None)

        assert error is not None
        assert error.column == "email"
        assert error.error_type == "required"
        assert "required" in error.message.lower()

    def test_validate_required_empty_string(self):
        """Test required validation fails with empty string"""
        error = validate_required("name", "")

        assert error is not None
        assert error.column == "name"
        assert error.error_type == "required"


class TestValidateType:
    """Tests for validate_type function"""

    def test_validate_type_int_valid(self):
        """Test int type validation"""
        assert validate_type("age", 25, "int") is None
        assert validate_type("age", "25", "int") is None  # String number

    def test_validate_type_int_invalid(self):
        """Test int type validation fails"""
        error = validate_type("age", "abc", "int")

        assert error is not None
        assert error.column == "age"
        assert error.error_type == "type"

    def test_validate_type_float_valid(self):
        """Test float type validation"""
        assert validate_type("price", 19.99, "float") is None
        assert validate_type("price", "19.99", "float") is None
        assert validate_type("price", 20, "float") is None  # Int to float

    def test_validate_type_float_invalid(self):
        """Test float type validation fails"""
        error = validate_type("price", "abc", "float")

        assert error is not None
        assert error.column == "price"
        assert error.error_type == "type"

    def test_validate_type_string_valid(self):
        """Test string type validation"""
        assert validate_type("name", "Alice", "string") is None
        assert validate_type("name", "", "string") is None
        assert validate_type("name", 123, "string") is None  # Coerced to string

    def test_validate_type_bool_valid(self):
        """Test bool type validation"""
        assert validate_type("active", True, "bool") is None
        assert validate_type("active", False, "bool") is None
        assert validate_type("active", "true", "bool") is None
        assert validate_type("active", 1, "bool") is None

    def test_validate_type_bool_invalid(self):
        """Test bool type validation fails"""
        error = validate_type("active", "maybe", "bool")

        assert error is not None
        assert error.column == "active"
        assert error.error_type == "type"

    def test_validate_type_date_valid(self):
        """Test date type validation"""
        assert validate_type("birthdate", "2000-01-15", "date") is None
        assert validate_type("birthdate", date(2000, 1, 15), "date") is None

    def test_validate_type_date_invalid(self):
        """Test date type validation fails"""
        error = validate_type("birthdate", "not-a-date", "date")

        assert error is not None
        assert error.column == "birthdate"
        assert error.error_type == "type"

    def test_validate_type_datetime_valid(self):
        """Test datetime type validation"""
        assert validate_type("created_at", "2024-01-15T10:30:00", "datetime") is None
        assert (
            validate_type("created_at", datetime(2024, 1, 15, 10, 30), "datetime")
            is None
        )

    def test_validate_type_datetime_invalid(self):
        """Test datetime type validation fails"""
        error = validate_type("created_at", "not-a-datetime", "datetime")

        assert error is not None
        assert error.column == "created_at"
        assert error.error_type == "type"

    def test_validate_type_none_value(self):
        """Test type validation with None returns None (no error)"""
        assert validate_type("field", None, "int") is None


class TestValidateLength:
    """Tests for validate_length function"""

    def test_validate_length_valid(self):
        """Test length validation passes"""
        assert validate_length("name", "Alice", 10) is None
        assert validate_length("name", "Alice", 5) is None  # Exactly max

    def test_validate_length_exceeds_max(self):
        """Test length validation fails when exceeds max"""
        error = validate_length("name", "Alice", 3)

        assert error is not None
        assert error.column == "name"
        assert error.error_type == "length"
        assert "3" in error.message

    def test_validate_length_non_string(self):
        """Test length validation returns None for non-strings"""
        assert validate_length("count", 123, 5) is None

    def test_validate_length_none_value(self):
        """Test length validation with None returns None"""
        assert validate_length("field", None, 10) is None


class TestValidateFormat:
    """Tests for validate_format function"""

    def test_validate_format_email_valid(self):
        """Test email format validation"""
        assert validate_format("email", "alice@example.com", "email") is None
        assert validate_format("email", "bob.smith@company.co.uk", "email") is None

    def test_validate_format_email_invalid(self):
        """Test email format validation fails"""
        error = validate_format("email", "not-an-email", "email")

        assert error is not None
        assert error.column == "email"
        assert error.error_type == "format"

    def test_validate_format_phone_valid(self):
        """Test phone format validation"""
        assert validate_format("phone", "555-1234", "phone") is None
        assert validate_format("phone", "+1-555-123-4567", "phone") is None
        assert validate_format("phone", "5551234567", "phone") is None

    def test_validate_format_phone_invalid(self):
        """Test phone format validation fails"""
        error = validate_format("phone", "abc", "phone")

        assert error is not None
        assert error.column == "phone"
        assert error.error_type == "format"

    def test_validate_format_url_valid(self):
        """Test URL format validation"""
        assert validate_format("website", "https://example.com", "url") is None
        assert validate_format("website", "http://site.org/path", "url") is None

    def test_validate_format_url_invalid(self):
        """Test URL format validation fails"""
        error = validate_format("website", "not-a-url", "url")

        assert error is not None
        assert error.column == "website"
        assert error.error_type == "format"

    def test_validate_format_uuid_valid(self):
        """Test UUID format validation"""
        assert (
            validate_format("id", "550e8400-e29b-41d4-a716-446655440000", "uuid")
            is None
        )

    def test_validate_format_uuid_invalid(self):
        """Test UUID format validation fails"""
        error = validate_format("id", "not-a-uuid", "uuid")

        assert error is not None
        assert error.column == "id"
        assert error.error_type == "format"

    def test_validate_format_iso_date_valid(self):
        """Test ISO date format validation"""
        assert validate_format("date", "2024-01-15", "iso_date") is None

    def test_validate_format_iso_date_invalid(self):
        """Test ISO date format validation fails"""
        error = validate_format("date", "01/15/2024", "iso_date")

        assert error is not None
        assert error.column == "date"
        assert error.error_type == "format"

    def test_validate_format_custom_pattern_valid(self):
        """Test custom regex pattern validation"""
        assert validate_format("code", "ABC123", r"^[A-Z]{3}\d{3}$") is None

    def test_validate_format_custom_pattern_invalid(self):
        """Test custom regex pattern validation fails"""
        error = validate_format("code", "abc123", r"^[A-Z]{3}\d{3}$")

        assert error is not None
        assert error.column == "code"
        assert error.error_type == "format"

    def test_validate_format_none_value(self):
        """Test format validation with None returns None"""
        assert validate_format("field", None, "email") is None


class TestValidateRange:
    """Tests for validate_range function"""

    def test_validate_range_within_min_max(self):
        """Test range validation passes"""
        assert validate_range("age", 25, min_val=0, max_val=100) is None
        assert validate_range("age", 0, min_val=0, max_val=100) is None
        assert validate_range("age", 100, min_val=0, max_val=100) is None

    def test_validate_range_below_min(self):
        """Test range validation fails below min"""
        error = validate_range("age", -5, min_val=0, max_val=100)

        assert error is not None
        assert error.column == "age"
        assert error.error_type == "range"
        assert "0" in error.message

    def test_validate_range_above_max(self):
        """Test range validation fails above max"""
        error = validate_range("age", 150, min_val=0, max_val=100)

        assert error is not None
        assert error.column == "age"
        assert error.error_type == "range"
        assert "100" in error.message

    def test_validate_range_min_only(self):
        """Test range validation with only min"""
        assert validate_range("score", 50, min_val=0) is None

        error = validate_range("score", -10, min_val=0)
        assert error is not None

    def test_validate_range_max_only(self):
        """Test range validation with only max"""
        assert validate_range("percentage", 75, max_val=100) is None

        error = validate_range("percentage", 150, max_val=100)
        assert error is not None

    def test_validate_range_non_numeric(self):
        """Test range validation returns None for non-numeric"""
        assert validate_range("field", "text", min_val=0, max_val=100) is None

    def test_validate_range_none_value(self):
        """Test range validation with None returns None"""
        assert validate_range("field", None, min_val=0, max_val=100) is None


class TestValidateRow:
    """Tests for validate_row function"""

    def test_validate_row_all_valid(self):
        """Test row validation passes with valid data"""
        row = {"name": "Alice", "email": "alice@example.com", "age": 25}

        column_specs = {
            "name": {"required": True, "type": "string", "max_length": 100},
            "email": {"required": True, "format": "email"},
            "age": {"type": "int", "min": 0, "max": 120},
        }

        errors = validate_row(row, column_specs)

        assert errors == []

    def test_validate_row_multiple_errors(self):
        """Test row validation returns multiple errors"""
        row = {"name": "", "email": "invalid-email", "age": 150}

        column_specs = {
            "name": {"required": True},
            "email": {"format": "email"},
            "age": {"type": "int", "max": 120},
        }

        errors = validate_row(row, column_specs)

        assert len(errors) == 3
        assert any(e.column == "name" and e.error_type == "required" for e in errors)
        assert any(e.column == "email" and e.error_type == "format" for e in errors)
        assert any(e.column == "age" and e.error_type == "range" for e in errors)

    def test_validate_row_missing_column(self):
        """Test row validation with missing column"""
        row = {"name": "Alice"}

        column_specs = {"email": {"required": True}}

        errors = validate_row(row, column_specs)

        assert len(errors) == 1
        assert errors[0].column == "email"
        assert errors[0].error_type == "required"

    def test_validate_row_no_specs(self):
        """Test row validation with no specs returns no errors"""
        row = {"field": "value"}

        errors = validate_row(row, {})

        assert errors == []


class TestValidateRows:
    """Tests for validate_rows batch function"""

    def test_validate_rows_all_valid(self):
        """Test validating multiple valid rows"""
        rows = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]

        column_specs = {
            "name": {"required": True},
            "age": {"type": "int", "min": 0, "max": 120},
        }

        valid, invalid = validate_rows(rows, column_specs)

        assert len(valid) == 2
        assert len(invalid) == 0

    def test_validate_rows_some_invalid(self):
        """Test validating rows with some invalid"""
        rows = [
            {"name": "Alice", "age": 25},
            {"name": "", "age": 150},
            {"name": "Charlie", "age": 35},
        ]

        column_specs = {"name": {"required": True}, "age": {"type": "int", "max": 120}}

        valid, invalid = validate_rows(rows, column_specs)

        assert len(valid) == 2
        assert len(invalid) == 1
        assert invalid[0]["row"] == {"name": "", "age": 150}
        assert len(invalid[0]["errors"]) == 2

    def test_validate_rows_empty_list(self):
        """Test validating empty list"""
        valid, invalid = validate_rows([], {"name": {"required": True}})

        assert valid == []
        assert invalid == []

    def test_validate_rows_error_details(self):
        """Test invalid rows include error details"""
        rows = [{"email": "invalid-email"}]

        column_specs = {"email": {"required": True, "format": "email"}}

        valid, invalid = validate_rows(rows, column_specs)

        assert len(invalid) == 1
        assert "row" in invalid[0]
        assert "errors" in invalid[0]
        assert isinstance(invalid[0]["errors"], list)
        assert len(invalid[0]["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
