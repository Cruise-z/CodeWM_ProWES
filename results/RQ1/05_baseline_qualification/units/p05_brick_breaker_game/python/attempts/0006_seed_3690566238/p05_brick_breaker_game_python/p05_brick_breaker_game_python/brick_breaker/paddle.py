"""Paddle entity for the Brick Breaker game."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import GameConfig


class Paddle:
    """Represents a paddle in the Brick Breaker game.

    The paddle has position, width, and speed. It can move horizontally
    within specified bounds.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        speed: float,
    ):
        """Initialize the paddle with position, width, and speed.

        Args:
            x: Initial x-coordinate of the paddle.
            y: Initial y-coordinate of the paddle.
            width: Width of the paddle.
            speed: Speed of the paddle in pixels per second.
        """
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed

    def move(self, direction: str, min_x: float, max_x: float, dt: float) -> None:
        """Move the paddle horizontally based on direction and time delta.

        Args:
            direction: Movement direction, one of 'left', 'right', or 'none'.
            min_x: Minimum x-coordinate allowed for the paddle.
            max_x: Maximum x-coordinate allowed for the paddle.
            dt: Time delta in seconds.
        """
        if direction == "left":
            self.x -= self.speed * dt
        elif direction == "right":
            self.x += self.speed * dt
        elif direction != "none":
            raise ValueError(f"Invalid direction: {direction}")

        # Clamp the paddle position to stay within bounds
        half_width = self.width / 2
        self.x = max(min_x + half_width, min(max_x - half_width, self.x))