"""Tank entity with position, facing, health, and speed."""

from .directions import Direction


class Tank:
    """A tank entity with position, direction, health, and speed.

    Attributes:
        id: Unique identifier for the tank.
        name: Human-readable name for the tank.
        x: X-coordinate of the tank's position.
        y: Y-coordinate of the tank's position.
        direction: Current facing direction of the tank.
        health: Current health points of the tank.
        speed: Movement speed of the tank.
    """

    def __init__(self, id: str, name: str, x: int, y: int, direction: Direction,
                 health: int = 3, speed: int = 1):
        """Initialize a tank with the given parameters.

        Args:
            id: Unique identifier for the tank.
            name: Human-readable name for the tank.
            x: X-coordinate of the tank's position.
            y: Y-coordinate of the tank's position.
            direction: Current facing direction of the tank.
            health: Initial health points of the tank (default: 3).
            speed: Movement speed of the tank (default: 1).
        """
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.direction = direction
        self.health = health
        self.speed = speed

    def barrel_ahead(self) -> tuple[int, int]:
        """Calculate the position directly ahead of the tank's barrel.

        Returns:
            A tuple (x, y) representing the position one unit ahead.
        """
        dx, dy = self.direction.delta()
        return self.x + dx, self.y + dy

    def alive(self) -> bool:
        """Check if the tank is still alive.

        Returns:
            True if the tank has health greater than 0, False otherwise.
        """
        return self.health > 0

    def clone(self) -> "Tank":
        """Create a deep copy of this tank.

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