"""Brick entity for the brick breaker game."""

class Brick:
    """Represents a brick in the game with position, dimensions, and durability."""

    def __init__(self, x: float, y: float, width: float, height: float, durability: int = 1):
        """Initialize the brick with position, dimensions, and durability."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.durability = durability

    def alive(self) -> bool:
        """
        Check if the brick is still alive (has durability > 0).
        
        Returns:
            True if the brick is alive, False otherwise
        """
        return self.durability > 0

    def hit(self) -> int:
        """
        Apply damage to the brick by decrementing durability.
        
        Returns:
            The remaining durability after the hit
        """
        self.durability = max(0, self.durability - 1)
        return self.durability