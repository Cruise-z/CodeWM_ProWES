"""Obstacle wrapper over Rect."""

from .geometry import Rect


class Obstacle:
    """An obstacle that encapsulates a Rect."""

    def __init__(self, rect: Rect) -> None:
        """
        Initialize an obstacle with a rectangle.

        Args:
            rect: The rectangle defining the obstacle's area.
        """
        self.rect = rect