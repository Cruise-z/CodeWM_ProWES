"""Paddle entity module for the brick breaker game.

This module defines the Paddle class which represents the player-controlled
paddle with horizontal movement and boundary clamping.
"""

from typing import Optional


class Paddle:
    """Represents a paddle in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize a paddle with position, dimensions, and speed.

        Args:
            x: Initial x-coordinate of the paddle center.
            y: Initial y-coordinate of the paddle center.
            width: Width of the paddle in pixels.
            speed: Speed of the paddle in pixels per second.
        """
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed

    def move(self, direction: str, min_x: float, max_x: float, dt: float) -> None:
        """Move the paddle horizontally based on direction and time delta.

        Args:
            direction: Movement direction, one of {'left', 'right', 'none'}.
            min_x: Minimum allowed x-coordinate for the paddle.
            max_x: Maximum allowed x-coordinate for the paddle.
            dt: Time delta in seconds since last update.
        """
        if direction == "left":
            self.x -= self.speed * dt
        elif direction == "right":
            self.x += self.speed * dt
        elif direction != "none":
            raise ValueError(f"Invalid direction: {direction}")

        # Clamp paddle position to stay within bounds
        half_width = self.width / 2
        self.x = max(min_x + half_width, min(max_x - half_width, self.x))