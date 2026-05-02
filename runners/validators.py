"""Validation functions for task data."""

from typing import Dict, Any, Tuple


REQUIRED_FIELDS = frozenset(
    {
        "id",
        "description",
        "expected_output",
    }
)


class ValidationError(Exception):
    """Exception raised when task validation fails."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_task(task: Dict[str, Any]) -> None:
    """
    Validate a task dictionary.

    Args:
        task: Dictionary containing task data

    Raises:
        ValidationError: If validation fails
    """
    _validate_required_fields(task)
    _validate_field_types(task)
    _validate_field_values(task)


def _validate_required_fields(task: Dict[str, Any]) -> None:
    """Check that all required fields are present."""
    missing = REQUIRED_FIELDS - set(task.keys())
    if missing:
        raise ValidationError(
            f"Missing required fields: {', '.join(sorted(missing))}",
            field="required_fields",
        )


def _validate_field_types(task: Dict[str, Any]) -> None:
    """Validate that fields have correct types."""
    if not isinstance(task.get("id"), (str, int)):
        raise ValidationError("'id' must be a string or integer", field="id")

    if not isinstance(task.get("description"), str):
        raise ValidationError("'description' must be a string", field="description")

    if not isinstance(task.get("expected_output"), str):
        raise ValidationError(
            "'expected_output' must be a string", field="expected_output"
        )


def _validate_field_values(task: Dict[str, Any]) -> None:
    """Validate that field values meet specific requirements."""
    # Validate id is not empty (allow 0 as a valid integer id)
    id_value = task.get("id")
    if id_value is None or id_value == "":
        raise ValidationError("'id' cannot be empty", field="id")

    # Validate description is not empty
    if not task.get("description"):
        raise ValidationError("'description' cannot be empty", field="description")

    # Validate expected_output is not empty
    if not task.get("expected_output"):
        raise ValidationError(
            "'expected_output' cannot be empty", field="expected_output"
        )


def validate_field(
    field_name: str, value: Any, expected_type: type = None
) -> Tuple[bool, str]:
    """
    Validate a single field.

    Args:
        field_name: Name of the field
        value: Value to validate
        expected_type: Expected type (optional)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"Field '{field_name}' cannot be None"

    if expected_type and not isinstance(value, expected_type):
        return False, f"Field '{field_name}' must be of type {expected_type.__name__}"

    if isinstance(value, str) and not value.strip():
        return False, f"Field '{field_name}' cannot be empty"

    return True, ""
