"""Task dataclass definition with validation and normalization."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import date
from .priority import Priority
from .errors import ValidationError


@dataclass
class Task:
    """A task entity with identity, attributes, and completion state."""

    id: int
    title: str
    description: Optional[str]
    priority: Priority
    due_date: Optional[date]
    tags: List[str]
    completed: bool
    completed_at: Optional[date]

    def __post_init__(self) -> None:
        """Validate and normalize task fields after initialization."""
        # Validate title
        if not self.title or not self.title.strip():
            raise ValidationError("Task title cannot be blank.")

        # Normalize tags
        normalized_tags = [
            tag.strip().lower()
            for tag in self.tags
            if tag.strip()
        ]
        self.tags = sorted(list(set(normalized_tags)))

    def mark_complete_on(self, day: date) -> None:
        """Mark the task as complete on the given day.

        If already completed, this operation is idempotent and preserves
        the original completed_at timestamp.

        Args:
            day: The date when the task was completed.
        """
        if not self.completed:
            self.completed = True
            self.completed_at = day
        # If already completed, do nothing (idempotent)

    def mark_incomplete(self) -> None:
        """Mark the task as incomplete.

        Clears the completed_at timestamp.
        """
        self.completed = False
        self.completed_at = None