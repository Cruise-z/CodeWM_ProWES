"""Projectile entity movement and cloning."""

from .directions import Direction


class Projectile:
    """A projectile entity with position, direction, and speed.

    Attributes:
        pid: Unique identifier for the projectile.
        owner_id: Identifier of the tank that fired this projectile.
        x: X-coordinate of the projectile's position.
        y: Y-coordinate of the projectile's position.
        direction: Current traveling direction of the projectile.
        speed: Movement speed of the projectile.
    """

    def __init__(self, pid: int, owner_id: str, x: int, y: int, direction: Direction,
                 speed: int = 1):
        """Initialize a projectile with the given parameters.

        Args:
            pid: Unique identifier for the projectile.
            owner_id: Identifier of the tank that fired this projectile.
            x: X-coordinate of the projectile's position.
            y: Y-coordinate of the projectile's position.
            direction: Current traveling direction of the projectile.
            speed: Movement speed of the projectile (default: 1).
        """
        self.pid = pid
        self.owner_id = owner_id
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = speed

    def move(self) -> None:
        """Move the projectile one unit in its current direction."""
        dx, dy = self.direction.delta()
        self.x += dx * self.speed
        self.y += dy * self.speed

    def clone(self) -> "Projectile":
        """Create a deep copy of this projectile.

        Returns:
            A new Projectile instance with identical attributes.
        """
        return Projectile(
            pid=self.pid,
            owner_id=self.owner_id,
            x=self.x,
            y=self.y,
            direction=self.direction,
            speed=self.speed
        )