"""Domain-specific exceptions for the video player application.

This module defines custom exception classes that are raised when
invalid operations or states are encountered within the video player
domain logic. These exceptions help provide clear error messages
and facilitate proper error handling in the application.
"""

class ValidationError(Exception):
    """Base exception class for validation errors in the video player domain.

    This exception is raised when input data or operation parameters
    do not meet the required validation criteria.
    """

class StateError(ValidationError):
    """Exception raised for invalid state transitions or operations.

    This exception is raised when an operation cannot be performed
    due to the current state of the system, such as attempting to
    play when no media is selected or when the playlist is empty.
    """

class NotFoundError(ValidationError):
    """Exception raised when a requested resource is not found.

    This exception is raised when attempting to access a playlist
    item or index that does not exist, such as an invalid index
    or a non-existent media ID.
    """