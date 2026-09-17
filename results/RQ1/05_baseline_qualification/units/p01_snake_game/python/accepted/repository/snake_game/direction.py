"""Direction enumeration for snake movement."""

from enum import Enum


class Direction(Enum):
    """Enumeration of cardinal directions."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    def delta(self) -> tuple[int, int]:
        """Get the delta tuple for this direction.

        Returns:
            The (dx, dy) tuple representing movement in this direction.
        """
        return self.value

    def is_opposite(self, other: "Direction") -> bool:
        """Check if this direction is the opposite of another.

        Args:
            other: Another Direction instance to compare against.

        Returns:
            True if the directions are opposite, False otherwise.
        """
        return self.value == (-other.value[0], -other.value[1])