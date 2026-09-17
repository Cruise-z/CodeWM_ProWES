"""Direction enum with turning and movement delta."""

from enum import Enum


class Direction(Enum):
    """Cardinal directions with movement deltas and turning helpers."""

    N = (0, -1)
    E = (1, 0)
    S = (0, 1)
    W = (-1, 0)

    def delta(self) -> tuple[int, int]:
        """Get the movement delta for this direction."""
        return self.value

    def left(self) -> "Direction":
        """Get the direction 90 degrees to the left."""
        directions = [Direction.N, Direction.W, Direction.S, Direction.E]
        idx = directions.index(self)
        return directions[(idx + 1) % 4]

    def right(self) -> "Direction":
        """Get the direction 90 degrees to the right."""
        directions = [Direction.N, Direction.E, Direction.S, Direction.W]
        idx = directions.index(self)
        return directions[(idx + 1) % 4]