"""Brick entity for the brick breaker game.

This module defines the Brick class which represents a brick in the game,
including its position, dimensions, durability, and collision handling.
"""

class Brick:
    """Represents a brick in the brick breaker game.

    A brick has a position (x, y), dimensions (width, height), and durability.
    It can be hit by the ball and removed when its durability reaches zero.
    """

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize a new brick.

        Args:
            x: X-coordinate of the brick's top-left corner.
            y: Y-coordinate of the brick's top-left corner.
            width: Width of the brick in pixels.
            height: Height of the brick in pixels.
            durability: Number of hits required to destroy the brick. Defaults to 1.
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.durability = durability

    def alive(self) -> bool:
        """Check if the brick is still alive (has durability greater than 0).

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