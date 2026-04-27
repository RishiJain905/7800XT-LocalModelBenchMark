"""Tests for runners.validators — Task validation functions."""

from __future__ import annotations

import pytest

from runners.validators import (
    REQUIRED_FIELDS,
    ValidationError,
    validate_task,
    _validate_required_fields,
    _validate_field_types,
    _validate_field_values,
    validate_field,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_task() -> dict:
    """Return a minimal task dict that passes all validations."""
    return {
        "id": "task-01",
        "description": "A valid test task",
        "command": "echo hello",
        "expected_output": "hello",
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestRequiredFieldsConstant:
    """The REQUIRED_FIELDS frozenset defines the mandatory task keys."""

    def test_contains_expected_fields(self):
        assert REQUIRED_FIELDS == {"id", "description", "command", "expected_output"}

    def test_is_frozen(self):
        with pytest.raises(AttributeError):
            REQUIRED_FIELDS.add("new_field")


# ---------------------------------------------------------------------------
# ValidationError exception
# ---------------------------------------------------------------------------


class TestValidationError:
    """ValidationError stores message and optional field name."""

    def test_message_attribute(self):
        err = ValidationError("Something went wrong")
        assert err.message == "Something went wrong"

    def test_field_attribute(self):
        err = ValidationError("Bad value", field="id")
        assert err.field == "id"
        assert err.message == "Bad value"

    def test_no_field_defaults_to_none(self):
        err = ValidationError("General error")
        assert err.field is None

    def test_is_an_exception(self):
        with pytest.raises(ValidationError):
            raise ValidationError("test")

    def test_string_representation(self):
        err = ValidationError("Error message")
        assert str(err) == "Error message"


# ---------------------------------------------------------------------------
# _validate_required_fields
# ---------------------------------------------------------------------------


class TestValidateRequiredFields:
    """Required field validation checks for missing keys."""

    def test_all_present_does_not_raise(self):
        task = _valid_task()
        _validate_required_fields(task)  # should not raise

    @pytest.mark.parametrize(
        "missing_key", ["id", "description", "command", "expected_output"]
    )
    def test_missing_single_field_raises(self, missing_key):
        task = _valid_task()
        del task[missing_key]
        with pytest.raises(
            ValidationError, match=f"Missing required fields: .*{missing_key}"
        ):
            _validate_required_fields(task)

    def test_missing_multiple_fields(self):
        task = {"id": "task-01"}
        with pytest.raises(
            ValidationError, match="Missing required fields:"
        ) as exc_info:
            _validate_required_fields(task)
        err = exc_info.value
        assert "command" in err.message
        assert "description" in err.message
        assert "expected_output" in err.message

    def test_error_has_field_attribute(self):
        task = {"id": "task-01"}
        with pytest.raises(ValidationError) as exc_info:
            _validate_required_fields(task)
        assert exc_info.value.field == "required_fields"

    def test_extra_fields_are_ignored(self):
        task = _valid_task()
        task["extra_field"] = "extra value"
        _validate_required_fields(task)  # should not raise

    def test_empty_dict_raises(self):
        with pytest.raises(ValidationError, match="Missing required fields:"):
            _validate_required_fields({})


# ---------------------------------------------------------------------------
# _validate_field_types
# ---------------------------------------------------------------------------


class TestValidateFieldTypes:
    """Field type validation ensures values are the correct Python types."""

    def test_all_correct_types_does_not_raise(self):
        task = _valid_task()
        _validate_field_types(task)  # should not raise

    def test_id_as_integer_is_valid(self):
        task = _valid_task()
        task["id"] = 42
        _validate_field_types(task)  # should not raise

    def test_id_as_string_is_valid(self):
        task = _valid_task()
        task["id"] = "str-id"
        _validate_field_types(task)  # should not raise

    def test_id_as_list_raises(self):
        task = _valid_task()
        task["id"] = ["bad"]
        with pytest.raises(ValidationError, match="'id' must be a string or integer"):
            _validate_field_types(task)

    def test_id_as_dict_raises(self):
        task = _valid_task()
        task["id"] = {"bad": "id"}
        with pytest.raises(ValidationError, match="'id' must be a string or integer"):
            _validate_field_types(task)

    def test_id_as_float_raises(self):
        task = _valid_task()
        task["id"] = 3.14
        with pytest.raises(ValidationError, match="'id' must be a string or integer"):
            _validate_field_types(task)

    def test_id_as_none_raises(self):
        task = _valid_task()
        task["id"] = None
        with pytest.raises(ValidationError, match="'id' must be a string or integer"):
            _validate_field_types(task)

    def test_description_as_int_raises(self):
        task = _valid_task()
        task["description"] = 123
        with pytest.raises(ValidationError, match="'description' must be a string"):
            _validate_field_types(task)

    def test_description_as_list_raises(self):
        task = _valid_task()
        task["description"] = ["desc"]
        with pytest.raises(ValidationError, match="'description' must be a string"):
            _validate_field_types(task)

    def test_description_as_none_raises(self):
        task = _valid_task()
        task["description"] = None
        with pytest.raises(ValidationError, match="'description' must be a string"):
            _validate_field_types(task)

    def test_command_as_int_raises(self):
        task = _valid_task()
        task["command"] = 456
        with pytest.raises(ValidationError, match="'command' must be a string"):
            _validate_field_types(task)

    def test_command_as_dict_raises(self):
        task = _valid_task()
        task["command"] = {"cmd": "test"}
        with pytest.raises(ValidationError, match="'command' must be a string"):
            _validate_field_types(task)

    def test_expected_output_as_int_raises(self):
        task = _valid_task()
        task["expected_output"] = 789
        with pytest.raises(ValidationError, match="'expected_output' must be a string"):
            _validate_field_types(task)

    def test_expected_output_as_list_raises(self):
        task = _valid_task()
        task["expected_output"] = ["out"]
        with pytest.raises(ValidationError, match="'expected_output' must be a string"):
            _validate_field_types(task)

    def test_error_has_field_attribute(self):
        task = _valid_task()
        task["command"] = 123
        with pytest.raises(ValidationError) as exc_info:
            _validate_field_types(task)
        assert exc_info.value.field == "command"


# ---------------------------------------------------------------------------
# _validate_field_values
# ---------------------------------------------------------------------------


class TestValidateFieldValues:
    """Field value validation ensures non-empty, meaningful content."""

    def test_all_valid_values_does_not_raise(self):
        task = _valid_task()
        _validate_field_values(task)  # should not raise

    def test_empty_string_id_raises(self):
        task = _valid_task()
        task["id"] = ""
        with pytest.raises(ValidationError, match="'id' cannot be empty"):
            _validate_field_values(task)

    def test_whitespace_only_id_is_valid(self):
        task = _valid_task()
        task["id"] = "   "
        _validate_field_values(task)  # whitespace is truthy in Python, so no raise

    def test_zero_id_is_valid(self):
        task = _valid_task()
        task["id"] = 0
        validate_task(task)  # 0 is a valid integer id

    def test_empty_string_description_raises(self):
        task = _valid_task()
        task["description"] = ""
        with pytest.raises(ValidationError, match="'description' cannot be empty"):
            _validate_field_values(task)

    def test_empty_string_command_raises(self):
        task = _valid_task()
        task["command"] = ""
        with pytest.raises(ValidationError, match="'command' cannot be empty"):
            _validate_field_values(task)

    def test_empty_string_expected_output_raises(self):
        task = _valid_task()
        task["expected_output"] = ""
        with pytest.raises(ValidationError, match="'expected_output' cannot be empty"):
            _validate_field_values(task)

    def test_whitespace_only_description_is_valid(self):
        task = _valid_task()
        task["description"] = "   "
        _validate_field_values(task)  # "   " is truthy

    def test_whitespace_only_command_is_valid(self):
        task = _valid_task()
        task["command"] = "\t\n"
        _validate_field_values(task)  # "\t\n" is truthy

    def test_missing_keys_use_get_and_dont_raise(self):
        """When keys are missing, task.get() returns None, which is falsy."""
        task = {"id": "task-01"}  # Missing other fields
        with pytest.raises(ValidationError, match="'description' cannot be empty"):
            _validate_field_values(task)

    def test_error_has_field_attribute(self):
        task = _valid_task()
        task["command"] = ""
        with pytest.raises(ValidationError) as exc_info:
            _validate_field_values(task)
        assert exc_info.value.field == "command"


# ---------------------------------------------------------------------------
# validate_task (integration of all validations)
# ---------------------------------------------------------------------------


class TestValidateTask:
    """validate_task orchestrates all validation steps."""

    def test_valid_task_does_not_raise(self):
        task = _valid_task()
        validate_task(task)  # should not raise

    def test_calls_all_validation_steps(self):
        """A task missing required fields should fail in step 1."""
        task = {"id": "task-01"}
        with pytest.raises(ValidationError, match="Missing required fields:"):
            validate_task(task)

    def test_type_error_caught(self):
        task = _valid_task()
        task["description"] = 123
        with pytest.raises(ValidationError, match="'description' must be a string"):
            validate_task(task)

    def test_value_error_caught(self):
        task = _valid_task()
        task["command"] = ""
        with pytest.raises(ValidationError, match="'command' cannot be empty"):
            validate_task(task)

    def test_validation_order_required_before_type(self):
        """Missing required fields error comes before type errors."""
        task = {
            "description": 123
        }  # Missing id, command, expected_output AND wrong type
        with pytest.raises(ValidationError, match="Missing required fields:"):
            validate_task(task)

    def test_validation_order_type_before_value(self):
        """Type errors come before value errors when all required fields exist."""
        task = {
            "id": "task-01",
            "description": "desc",
            "command": "cmd",
            "expected_output": None,
        }
        with pytest.raises(ValidationError, match="'expected_output' must be a string"):
            validate_task(task)


# ---------------------------------------------------------------------------
# validate_field
# ---------------------------------------------------------------------------


class TestValidateField:
    """validate_field checks a single value for None, type, and emptiness."""

    def test_valid_string_returns_true(self):
        is_valid, msg = validate_field("name", "John")
        assert is_valid is True
        assert msg == ""

    def test_valid_int_returns_true(self):
        is_valid, msg = validate_field("age", 25)
        assert is_valid is True
        assert msg == ""

    def test_none_value_returns_false(self):
        is_valid, msg = validate_field("name", None)
        assert is_valid is False
        assert msg == "Field 'name' cannot be None"

    def test_none_with_type_returns_false(self):
        is_valid, msg = validate_field("name", None, str)
        assert is_valid is False
        assert msg == "Field 'name' cannot be None"

    def test_empty_string_returns_false(self):
        is_valid, msg = validate_field("name", "")
        assert is_valid is False
        assert msg == "Field 'name' cannot be empty"

    def test_whitespace_only_string_returns_false(self):
        is_valid, msg = validate_field("name", "   ")
        assert is_valid is False
        assert msg == "Field 'name' cannot be empty"

    def test_tab_only_string_returns_false(self):
        is_valid, msg = validate_field("name", "\t")
        assert is_valid is False
        assert msg == "Field 'name' cannot be empty"

    def test_newline_only_string_returns_false(self):
        is_valid, msg = validate_field("name", "\n")
        assert is_valid is False
        assert msg == "Field 'name' cannot be empty"

    def test_type_mismatch_int_for_str(self):
        is_valid, msg = validate_field("name", 123, str)
        assert is_valid is False
        assert msg == "Field 'name' must be of type str"

    def test_type_mismatch_str_for_int(self):
        is_valid, msg = validate_field("age", "twenty", int)
        assert is_valid is False
        assert msg == "Field 'age' must be of type int"

    def test_type_mismatch_list_for_str(self):
        is_valid, msg = validate_field("name", ["a", "b"], str)
        assert is_valid is False
        assert msg == "Field 'name' must be of type str"

    def test_correct_type_with_value_no_empty_check_for_int(self):
        is_valid, msg = validate_field("age", 0, int)
        assert is_valid is True
        assert msg == ""

    def test_correct_type_with_false_value_no_empty_check_for_bool(self):
        is_valid, msg = validate_field("active", False, bool)
        assert is_valid is True
        assert msg == ""

    def test_no_type_check_still_validates_non_empty(self):
        is_valid, msg = validate_field("name", "valid")
        assert is_valid is True
        assert msg == ""

    def test_no_type_check_catches_empty_string(self):
        is_valid, msg = validate_field("name", "")
        assert is_valid is False
        assert msg == "Field 'name' cannot be empty"

    def test_no_type_check_allows_any_non_none_non_empty(self):
        is_valid, msg = validate_field("data", ["a", "b"])
        assert is_valid is True
        assert msg == ""

    def test_no_type_check_allows_dict_value(self):
        is_valid, msg = validate_field("config", {"key": "value"})
        assert is_valid is True
        assert msg == ""

    def test_zero_int_valid_without_type(self):
        is_valid, msg = validate_field("count", 0)
        assert is_valid is True
        assert msg == ""

    def test_empty_list_valid_without_type(self):
        is_valid, msg = validate_field("items", [])
        assert is_valid is True
        assert msg == ""

    def test_empty_dict_valid_without_type(self):
        is_valid, msg = validate_field("config", {})
        assert is_valid is True
        assert msg == ""


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_task_with_very_long_strings(self):
        task = {
            "id": "x" * 10000,
            "description": "desc" * 5000,
            "command": "cmd" * 5000,
            "expected_output": "out" * 5000,
        }
        validate_task(task)  # should not raise

    def test_task_with_unicode_fields(self):
        task = {
            "id": "任务-01",
            "description": "Тестовое описание 你好 мир",
            "command": "echo '🌍'",
            "expected_output": "🌍",
        }
        validate_task(task)  # should not raise

    def test_task_with_special_characters(self):
        task = {
            "id": "<script>alert('xss')</script>",
            "description": "'; DROP TABLE tasks; --",
            "command": "cmd && rm -rf /",
            "expected_output": "\x00\x01\x02",
        }
        validate_task(task)  # should not raise (validators don't sanitize)

    def test_task_with_numeric_zero_id(self):
        task = _valid_task()
        task["id"] = 0
        validate_task(task)  # should not raise (0 is valid int id)

    def test_task_with_negative_id(self):
        task = _valid_task()
        task["id"] = -1
        validate_task(task)  # should not raise (-1 is valid int id)

    def test_task_with_boolean_fields(self):
        """Booleans are subclass of int in Python, so True/False pass type check.
        False would fail the empty-string-like check if not for the explicit
        None/"" check we added, but True passes cleanly."""
        task = _valid_task()
        task["id"] = True
        validate_task(task)  # True passes isinstance(True, int) — Python behavior

    def test_task_with_false_id(self):
        """False is a bool (subclass of int) and is not None or '', so valid."""
        task = _valid_task()
        task["id"] = False
        validate_task(task)  # False passes as it's not None and != ""

    def test_task_with_single_character_fields(self):
        task = {
            "id": "a",
            "description": "b",
            "command": "c",
            "expected_output": "d",
        }
        validate_task(task)  # should not raise

    def test_validate_field_with_zero_string(self):
        is_valid, msg = validate_field("number", "0")
        assert is_valid is True
        assert msg == ""

    def test_validate_field_with_float_type(self):
        is_valid, msg = validate_field("price", 3.14, float)
        assert is_valid is True
        assert msg == ""

    def test_validate_field_with_float_mismatch(self):
        is_valid, msg = validate_field("price", "3.14", float)
        assert is_valid is False
        assert msg == "Field 'price' must be of type float"

    def test_validate_field_with_list_type(self):
        is_valid, msg = validate_field("items", [1, 2, 3], list)
        assert is_valid is True
        assert msg == ""

    def test_validate_field_with_dict_type(self):
        is_valid, msg = validate_field("config", {"a": 1}, dict)
        assert is_valid is True
        assert msg == ""
