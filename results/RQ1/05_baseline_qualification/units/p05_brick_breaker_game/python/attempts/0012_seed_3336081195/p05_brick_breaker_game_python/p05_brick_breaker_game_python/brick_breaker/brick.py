"""Brick entity module for the brick breaker game.

This module defines the Brick class which represents a brick in the game,
including its position, dimensions, durability, and collision handling.
"""

from typing import Any


class Brick:
    """Represents a brick in the brick breaker game.

    A brick has a position (x, y), dimensions (width, height), and durability.
    It can be hit and removed when its durability reaches zero.
    """

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize a brick with position, dimensions, and durability.

        Args:
            x: X-coordinate of the brick's top-left corner.
            y: Y-coordinate of the brick's top-left corner.
            width: Width of the brick in pixels.
            height: Height of the brick in pixels.
            durability: Number of hits required to break the brick.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.durability = durability

    def alive(self) -> bool:
        """Check if the brick is still alive (has durability > 0).

        Returns:
            True if the brick is alive, False otherwise.
        """
        return self.durability > 0

    def hit(self) -> int:
        """Apply damage to the brick by decrementing its durability.

        Returns:
            The remaining durability after the hit.
        """
        self.durability = max(0, self.durability - 1)
        return self.durability

    def __eq__(self, other: Any) -> bool:
        """Check if two bricks are equal based on their attributes."""
        if not isinstance(other, Brick):
            return False
        return (
            self.x == other.x
            and self.y == other.y
            and self.width == other.width
            and self.height == other.height
            and self.durability == other.durability
        )