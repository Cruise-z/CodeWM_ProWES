"""Priority enumeration for tasks."""

from enum import Enum
from .errors import ValidationError


class Priority(Enum):
    """Enumeration of task priorities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def order_value(self) -> int:
        """Get the numeric order value of the priority.

        Returns:
            int: 0 for LOW, 1 for MEDIUM, 2 for HIGH
        """
        return self.value.index("h") if self.value == "high" else self.value.index("l") if self.value == "low" else 1

    @classmethod
    def from_value(cls, v) -> "Priority":
        """Convert a value to a Priority enum.

        Args:
            v: Either a Priority enum member or a string representation
               ('low', 'med', 'medium', 'high').

        Returns:
            Priority: The corresponding Priority enum member.

        Raises:
            ValidationError: If the value cannot be converted to a Priority.
        """
        if isinstance(v, Priority):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("low", "l"):
                return cls.LOW
            if s in ("med", "medium", "m"):
                return cls.MEDIUM
            if s in ("high", "h"):
                return cls.HIGH
        raise ValidationError(f"Invalid priority value: {v!r}")