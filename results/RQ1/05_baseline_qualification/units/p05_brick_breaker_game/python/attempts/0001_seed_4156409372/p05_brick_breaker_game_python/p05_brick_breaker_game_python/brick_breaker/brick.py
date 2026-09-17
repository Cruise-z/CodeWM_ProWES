"""Brick entity module for the brick breaker game.

This module defines the Brick class which represents individual bricks
in the game with their properties and hit mechanics.
"""

class Brick:
    """Represents a brick in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize a brick with position, dimensions, and durability.

        Args:
            x: X-coordinate of the brick's top-left corner.
            y: Y-coordinate of the brick's top-left corner.
            width: Width of the brick in pixels.
            height: Height of the brick in pixels.
            durability: Number of hits required to destroy the brick.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.durability = durability

    def alive(self) -> bool:
        """Check if the brick is still intact.

        Returns:
            True if the brick has durability greater than 0, False otherwise.
        """
        return self.durability > 0

    def hit(self) -> int:
        """Apply damage to the brick.

        Reduces the brick's durability by 1, ensuring it doesn't go below 0.

        Returns:
            The remaining durability after the hit.
        """
        self.durability = max(0, self.durability - 1)
        return self.durability