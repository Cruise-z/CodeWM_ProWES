"""
Brick entity module for the brick breaker game.

This module defines the Brick class which represents a brick in the game,
including its position, dimensions, durability, and hit mechanics.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import GameConfig


class Brick:
    """Represents a brick in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """
        Initialize a brick with position, dimensions, and durability.

        Args:
            x: X-coordinate of the brick's top-left corner
            y: Y-coordinate of the brick's top-left corner
            width: Width of the brick
            height: Height of the brick
            durability: Number of hits required to break the brick (default: 1)
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.durability = durability

    def alive(self) -> bool:
        """
        Check if the brick is still alive (not broken).

        Returns:
            True if the brick is alive, False otherwise
        """
        return self.durability > 0

    def hit(self) -> int:
        """
        Apply damage to the brick by decrementing its durability.

        Returns:
            The remaining durability after the hit
        """
        self.durability = max(0, self.durability - 1)
        return self.durability