"""Brick entity module for the brick breaker game.

This module defines the Brick class which represents individual bricks
in the game that can be broken by the ball.
"""

from typing import Optional


class Brick:
    """Represents a brick in the brick breaker game.

    Each brick has a position, dimensions, and durability. Bricks can be hit
    by the ball, which reduces their durability. When durability reaches zero,
    the brick is considered destroyed.
    """

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize a brick with position, dimensions, and durability.

        Args:
            x: X-coordinate of the brick's top-left corner.
            y: Y-coordinate of the brick's top-left corner.
            width: Width of the brick in pixels.
            height: Height of the brick in pixels.
            durability: Number of hits required to destroy the brick. Default is 1.
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
        """Apply damage to the brick by reducing its durability.

        Returns:
            The remaining durability after the hit.
        """
        self.durability = max(0, self.durability - 1)
        return self.durability