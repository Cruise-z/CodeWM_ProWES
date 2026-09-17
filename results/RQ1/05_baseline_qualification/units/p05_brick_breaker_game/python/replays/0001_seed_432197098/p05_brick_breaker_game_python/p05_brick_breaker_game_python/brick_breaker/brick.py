"""Brick entity for the brick breaker game.

This module defines the Brick class which represents individual bricks
in the game that can be destroyed by the ball.
"""

class Brick:
    """Represents a brick in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize a brick with position, size, and durability.

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
        """Check if the brick is still alive (not destroyed).

        Returns:
            True if the brick has durability greater than 0, False otherwise.
        """
        return self.durability > 0

    def hit(self) -> int:
        """Apply damage to the brick.

        Reduces the brick's durability by 1, with a minimum of 0.

        Returns:
            The remaining durability of the brick after being hit.
        """
        self.durability = max(0, self.durability - 1)
        return self.durability