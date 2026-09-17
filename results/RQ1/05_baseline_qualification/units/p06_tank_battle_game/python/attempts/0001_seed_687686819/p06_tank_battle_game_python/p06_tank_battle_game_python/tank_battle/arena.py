"""Arena bounds and blocking rules."""

from typing import List
from .obstacle import Obstacle


class Arena:
    """Represents a bounded arena with obstacles."""

    def __init__(self, width: int, height: int, obstacles: List[Obstacle]) -> None:
        """
        Initialize an arena.

        Args:
            width: The width of the arena (must be positive).
            height: The height of the arena (must be positive).
            obstacles: A list of obstacles within the arena.

        Raises:
            ValueError: If width or height is not positive.
        """
        if width <= 0:
            raise ValueError("Width must be positive")
        if height <= 0:
            raise ValueError("Height must be positive")
        
        self.width = width
        self.height = height
        self.obstacles = obstacles

    def in_bounds(self, x: int, y: int) -> bool:
        """
        Check if a position is within the arena bounds.

        Args:
            x: The x-coordinate to check.
            y: The y-coordinate to check.

        Returns:
            True if the position is within bounds, False otherwise.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocked(self, x: int, y: int) -> bool:
        """
        Check if a position is blocked by arena boundaries or obstacles.

        Args:
            x: The x-coordinate to check.
            y: The y-coordinate to check.

        Returns:
            True if the position is blocked, False otherwise.
        """
        # First check if position is out of bounds
        if not self.in_bounds(x, y):
            return True
        
        # Then check if position is inside any obstacle
        for obstacle in self.obstacles:
            if obstacle.rect.contains(x, y):
                return True
        
        return False