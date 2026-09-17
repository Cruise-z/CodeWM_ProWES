"""Domain error definitions for press release system."""

from typing import Final


class DomainError(ValueError):
    """Base exception for domain-related errors."""


class InvalidTransitionError(DomainError):
    """Raised when an invalid state transition is attempted."""