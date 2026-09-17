"""Ball entity for the Brick Breaker game."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import GameConfig


class Ball:
    """Represents a ball in the Brick Breaker game.

    The ball has position, velocity, and radius. It can step through time
    and bounce off walls.
    """

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        radius: float,
    ):
        """Initialize the ball with position, velocity, and radius.

        Args:
            x: Initial x-coordinate of the ball.
            y: Initial y-coordinate of the ball.
            vx: Initial velocity in x-direction.
            vy: Initial velocity in y-direction.
            radius: Radius of the ball.
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """Update the ball's position based on its velocity and time delta.

        Args:
            dt: Time delta in seconds.
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the ball's horizontal velocity."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the ball's vertical velocity."""
        self.vy = -self.vy