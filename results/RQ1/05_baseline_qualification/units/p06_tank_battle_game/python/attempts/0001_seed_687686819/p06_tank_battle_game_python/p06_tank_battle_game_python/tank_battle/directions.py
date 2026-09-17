"""Direction enum and turning/delta helpers."""

from enum import Enum


class Direction(Enum):
    """Enumeration of compass directions with associated movement deltas."""

    N = (0, -1)
    E = (1, 0)
    S = (0, 1)
    W = (-1, 0)

    def delta(self) -> tuple[int, int]:
        """Get the movement delta for this direction."""
        return self.value

    def left(self) -> "Direction":
        """Get the direction 90 degrees to the left."""
        clockwise = [Direction.N, Direction.E, Direction.S, Direction.W]
        current_index = clockwise.index(self)
        return clockwise[(current_index + 1) % 4]

    def right(self) -> "Direction":
        """Get the direction 90 degrees to the right."""
        clockwise = [Direction.N, Direction.E, Direction.S, Direction.W]
        current_index = clockwise.index(self)
        return clockwise[(current_index - 1) % 4]