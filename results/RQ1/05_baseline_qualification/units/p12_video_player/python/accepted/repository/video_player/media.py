"""Immutable media metadata entity with validation.

This module defines the Media class, which represents a single piece of media
with its metadata. The class is immutable after construction and includes
validation to ensure data integrity.
"""

from typing import Optional, Dict
from .errors import ValidationError


class Media:
    """Represents a media item with metadata.

    This class encapsulates the essential information about a media item,
    including its unique identifier, title, duration, and optional metadata.
    The object is immutable after construction.
    """

    def __init__(
        self,
        id: str,
        title: str,
        duration_seconds: float,
        metadata: Optional[Dict] = None
    ):
        """Initialize a new Media object.

        Args:
            id: Unique identifier for the media item. Must be a non-empty string.
            title: Title of the media item. Must be a non-empty string.
            duration_seconds: Duration of the media in seconds. Must be a positive float.
            metadata: Optional dictionary containing additional metadata.
                      If None, an empty dict is used internally.

        Raises:
            ValidationError: If any of the validation checks fail.
        """
        # Validate id
        if not isinstance(id, str):
            raise ValidationError("Media ID must be a string")
        if not id:
            raise ValidationError("Media ID cannot be empty")

        # Validate title
        if not isinstance(title, str):
            raise ValidationError("Media title must be a string")
        if not title:
            raise ValidationError("Media title cannot be empty")

        # Validate duration
        if not isinstance(duration_seconds, (int, float)):
            raise ValidationError("Duration must be a number")
        if duration_seconds <= 0:
            raise ValidationError("Duration must be positive")

        # Store validated values
        self._id = id
        self._title = title
        self._duration_seconds = float(duration_seconds)
        self._metadata = dict(metadata) if metadata is not None else {}

    @property
    def id(self) -> str:
        """Get the unique identifier of this media item."""
        return self._id

    @property
    def title(self) -> str:
        """Get the title of this media item."""
        return self._title

    @property
    def duration_seconds(self) -> float:
        """Get the duration of this media item in seconds."""
        return self._duration_seconds

    @property
    def metadata(self) -> Dict:
        """Get a shallow copy of the metadata dictionary."""
        return dict(self._metadata)

    def __repr__(self) -> str:
        """Return a string representation of this Media object."""
        return f"Media(id='{self._id}', title='{self._title}', duration_seconds={self._duration_seconds})"

    def __eq__(self, other) -> bool:
        """Check equality with another object."""
        if not isinstance(other, Media):
            return False
        return (
            self._id == other._id and
            self._title == other._title and
            self._duration_seconds == other._duration_seconds and
            self._metadata == other._metadata
        )