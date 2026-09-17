"""Ball entity module for the brick breaker game.

This module defines the Ball class which represents the ball in the game,
including its position, velocity, radius, and movement logic.
"""

from typing import Any


class Ball:
    """Represents a ball in the brick breaker game.

    The ball has a position (x, y), velocity (vx, vy), and radius.
    It can be moved through time steps and bounce off surfaces.
    """

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float):
        """Initialize a ball with position, velocity, and radius.

        Args:
            x: Initial x-coordinate of the ball's center.
            y: Initial y-coordinate of the ball's center.
            vx: Initial horizontal velocity in pixels per second.
            vy: Initial vertical velocity in pixels per second.
            radius: Radius of the ball in pixels.
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """Update the ball's position based on its velocity and elapsed time.

        Args:
            dt: Time elapsed since last update in seconds.
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the horizontal velocity of the ball."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the vertical velocity of the ball."""
        self.vy = -self.vy

    def __eq__(self, other: Any) -> bool:
        """Check if two balls are equal based on their attributes."""
        if not isinstance(other, Ball):
            return False
        return (
            self.x == other.x
            and self.y == other.y
            and self.vx == other.vx
            and self.vy == other.vy
            and self.radius == other.radius
        )