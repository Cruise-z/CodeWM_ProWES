"""Immutable rectangle geometry with validation and containment check."""

from typing import Tuple


class Rect:
    """An immutable rectangle with integer coordinates.

    Attributes:
        x: The x-coordinate of the top-left corner.
        y: The y-coordinate of the top-left corner.
        w: The width of the rectangle (must be positive).
        h: The height of the rectangle (must be positive).
    """

    def __init__(self, x: int, y: int, w: int, h: int):
        """Initialize a rectangle with given parameters.

        Args:
            x: The x-coordinate of the top-left corner.
            y: The y-coordinate of the top-left corner.
            w: The width of the rectangle (must be positive).
            h: The height of the rectangle (must be positive).

        Raises:
            ValueError: If either w or h is not positive.
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
        """Check if a point is within this rectangle (half-open interval).

        A point (px, py) is contained if:
        self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

        Args:
            px: The x-coordinate of the point.
            py: The y-coordinate of the point.

        Returns:
            True if the point is contained, False otherwise.
        """
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h