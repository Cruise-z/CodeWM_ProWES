"""Validation rules for the CRUD system."""

from .errors import ValidationError


def validate_name(name: str) -> None:
    """Validate that a name is not empty.

    Args:
        name: The name to validate.

    Raises:
        ValidationError: If the name is empty.
    """
    if not name:
        raise ValidationError("Name cannot be empty")