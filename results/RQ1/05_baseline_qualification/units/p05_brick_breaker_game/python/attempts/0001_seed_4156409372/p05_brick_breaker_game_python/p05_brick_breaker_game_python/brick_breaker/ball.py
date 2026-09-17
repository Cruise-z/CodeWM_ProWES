"""Ball entity module for the brick breaker game.

This module defines the Ball class which represents the game ball
with its position, velocity, and movement logic.
"""

from typing import Optional


class Ball:
    """Represents a ball in the brick breaker game."""

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float):
        """Initialize a ball with position, velocity, and radius.

        Args:
            x: Initial x-coordinate of the ball center.
            y: Initial y-coordinate of the ball center.
            vx: Initial velocity in x-direction (pixels per second).
            vy: Initial velocity in y-direction (pixels per second).
            radius: Radius of the ball in pixels.
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """Update the ball's position based on its velocity and time delta.

        Args:
            dt: Time delta in seconds since last update.
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the ball's horizontal velocity."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the ball's vertical velocity."""
        self.vy = -self.vy