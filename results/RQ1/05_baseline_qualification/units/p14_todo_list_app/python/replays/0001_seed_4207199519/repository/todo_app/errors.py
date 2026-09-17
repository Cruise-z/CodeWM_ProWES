"""Domain-specific exception types."""

class ValidationError(Exception):
    """Base exception for domain validation errors."""

    def __init__(self, message: str) -> None:
        """Initialize validation error with message."""
        super().__init__(message)


class NotFoundError(ValidationError):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found.") -> None:
        """Initialize not-found error with optional message."""
        super().__init__(message)