"""Custom exception definitions for the CRUD system."""

from typing import NoReturn


class ValidationError(Exception):
    """Raised when a validation check fails."""


class DuplicateNameError(Exception):
    """Raised when attempting to create an item with a duplicate name."""


class NotFoundError(Exception):
    """Raised when an item is not found."""


class PaginationError(Exception):
    """Raised when a pagination operation fails."""