"""Obstacle wrapper over Rect."""

from .geometry import Rect


class Obstacle:
    """An obstacle that occupies a rectangular area.

    Attributes:
        rect: The Rect representing the obstacle's area.
    """

    def __init__(self, rect: Rect):
        """Initialize an obstacle with the given rectangle.

        Args:
            rect: The Rect representing the obstacle's area.
        """
        self.rect = rect