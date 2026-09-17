"""Paddle entity for the brick breaker game.

This module defines the Paddle class which represents the player-controlled
paddle that moves horizontally to bounce the ball.
"""

class Paddle:
    """Represents a paddle in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize a paddle with position, width, and speed.

        Args:
            x: Initial x-coordinate of the paddle center.
            y: Initial y-coordinate of the paddle center.
            width: Width of the paddle in pixels.
            speed: Paddle movement speed in pixels per second.
        """
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed

    def move(self, direction: str, min_x: float, max_x: float, dt: float) -> None:
        """Move the paddle horizontally based on direction and time delta.

        Args:
            direction: Movement direction, one of 'left', 'right', or 'none'.
            min_x: Minimum x-coordinate the paddle can reach.
            max_x: Maximum x-coordinate the paddle can reach.
            dt: Time delta in seconds.
        """
        if direction == "left":
            self.x -= self.speed * dt
        elif direction == "right":
            self.x += self.speed * dt
        elif direction != "none":
            raise ValueError(f"Invalid direction '{direction}'. Must be 'left', 'right', or 'none'.")

        # Clamp the paddle position to stay within bounds
        half_width = self.width / 2
        self.x = max(min_x + half_width, min(max_x - half_width, self.x))