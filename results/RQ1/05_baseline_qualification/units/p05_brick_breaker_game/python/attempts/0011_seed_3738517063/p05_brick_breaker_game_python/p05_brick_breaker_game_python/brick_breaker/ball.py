"""Ball entity module for the brick breaker game.

This module defines the Ball class which represents the ball in the game,
including its position, velocity, and movement logic.
"""

class Ball:
    """Represents a ball in the brick breaker game."""

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float):
        """Initialize a ball with position, velocity, and radius.

        Args:
            x: Initial x-coordinate of the ball
            y: Initial y-coordinate of the ball
            vx: Initial velocity in x-direction (pixels per second)
            vy: Initial velocity in y-direction (pixels per second)
            radius: Radius of the ball in pixels
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """Update the ball's position based on its velocity and time delta.

        Args:
            dt: Time delta in seconds
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the ball's x-velocity."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the ball's y-velocity."""
        self.vy = -self.vy