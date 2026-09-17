"""Grid and position definitions for the snake game."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Position:
    """An immutable position in the grid."""

    x: int
    y: int


class Grid:
    """A rectangular grid with width and height."""

    def __init__(self, width: int, height: int) -> None:
        """Initialize a grid with given dimensions.

        Args:
            width: The width of the grid, must be positive.
            height: The height of the grid, must be positive.

        Raises:
            ValueError: If width or height is not positive.
        """
        if width <= 0:
            raise ValueError("Width must be positive")
        if height <= 0:
            raise ValueError("Height must be positive")
        
        self._width = width
        self._height = height

    @property
    def width(self) -> int:
        """Get the width of the grid."""
        return self._width

    @property
    def height(self) -> int:
        """Get the height of the grid."""
        return self._height

    def in_bounds(self, pos: Position) -> bool:
        """Check if a position is within the grid bounds.

        Args:
            pos: The position to check.

        Returns:
            True if the position is within the grid, False otherwise.
        """
        return (0 <= pos.x < self._width and 0 <= pos.y < self._height)