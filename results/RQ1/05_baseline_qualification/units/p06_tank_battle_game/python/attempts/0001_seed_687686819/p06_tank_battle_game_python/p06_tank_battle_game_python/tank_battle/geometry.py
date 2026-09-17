"""Immutable rectangle geometry with validation and containment checks."""

from typing import Tuple


class Rect:
    """An immutable rectangle with integer coordinates."""

    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        """
        Initialize a rectangle.

        Args:
            x: The x-coordinate of the top-left corner.
            y: The y-coordinate of the top-left corner.
            w: The width of the rectangle (must be positive).
            h: The height of the rectangle (must be positive).

        Raises:
            ValueError: If width or height is not positive.
        """
        if w <= 0:
            raise ValueError("Width must be positive")
        if h <= 0:
            raise ValueError("Height must be positive")
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def contains(self, px: int, py: int) -> bool:
        """
        Check if a point is within the rectangle (half-open interval).

        Args:
            px: The x-coordinate of the point.
            py: The y-coordinate of the point.

        Returns:
            True if the point is within the rectangle, False otherwise.
        """
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h