"""Tank entity with position, facing, health, speed."""

from typing import Dict, Any
from .directions import Direction


class Tank:
    """Represents a tank in the game with position, direction, health, and speed."""

    def __init__(
        self,
        id: str,
        name: str,
        x: int,
        y: int,
        direction: Direction,
        health: int = 3,
        speed: int = 1
    ) -> None:
        """
        Initialize a tank.

        Args:
            id: Unique identifier for the tank.
            name: Name of the tank.
            x: X-coordinate of the tank's position.
            y: Y-coordinate of the tank's position.
            direction: Direction the tank is facing.
            health: Health points of the tank (default 3).
            speed: Movement speed of the tank (default 1).
        """
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.direction = direction
        self.health = health
        self.speed = speed

    def barrel_ahead(self) -> tuple[int, int]:
        """
        Calculate the position ahead of the tank's barrel.

        Returns:
            A tuple (x, y) representing the position ahead of the tank.
        """
        dx, dy = self.direction.delta()
        return (self.x + dx, self.y + dy)

    def alive(self) -> bool:
        """
        Check if the tank is alive.

        Returns:
            True if the tank has health greater than 0, False otherwise.
        """
        return self.health > 0

    def clone(self) -> "Tank":
        """
        Create a deep copy of this tank.

        Returns:
            A new Tank instance with identical attributes.
        """
        return Tank(
            id=self.id,
            name=self.name,
            x=self.x,
            y=self.y,
            direction=self.direction,
            health=self.health,
            speed=self.speed
        )

    def __repr__(self) -> str:
        """Return a string representation of the tank."""
        return f"Tank(id={self.id!r}, name={self.name!r}, x={self.x}, y={self.y}, direction={self.direction.name}, health={self.health}, speed={self.speed})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another tank."""
        if not isinstance(other, Tank):
            return False
        return (
            self.id == other.id and
            self.name == other.name and
            self.x == other.x and
            self.y == other.y and
            self.direction == other.direction and
            self.health == other.health and
            self.speed == other.speed
        )