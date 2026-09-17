"""Projectile entity movement and cloning."""

from typing import Dict, Any
from .directions import Direction


class Projectile:
    """Represents a projectile fired by a tank."""

    def __init__(
        self,
        pid: int,
        owner_id: str,
        x: int,
        y: int,
        direction: Direction,
        speed: int = 1
    ) -> None:
        """
        Initialize a projectile.

        Args:
            pid: Unique identifier for the projectile.
            owner_id: ID of the tank that fired this projectile.
            x: X-coordinate of the projectile's position.
            y: Y-coordinate of the projectile's position.
            direction: Direction the projectile is moving.
            speed: Movement speed of the projectile (default 1).
        """
        self.pid = pid
        self.owner_id = owner_id
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = speed

    def move(self) -> None:
        """
        Move the projectile one unit in its direction.
        """
        dx, dy = self.direction.delta()
        self.x += dx * self.speed
        self.y += dy * self.speed

    def clone(self) -> "Projectile":
        """
        Create a deep copy of this projectile.

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

    def __repr__(self) -> str:
        """Return a string representation of the projectile."""
        return f"Projectile(pid={self.pid}, owner_id={self.owner_id!r}, x={self.x}, y={self.y}, direction={self.direction.name}, speed={self.speed})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another projectile."""
        if not isinstance(other, Projectile):
            return False
        return (
            self.pid == other.pid and
            self.owner_id == other.owner_id and
            self.x == other.x and
            self.y == other.y and
            self.direction == other.direction and
            self.speed == other.speed
        )