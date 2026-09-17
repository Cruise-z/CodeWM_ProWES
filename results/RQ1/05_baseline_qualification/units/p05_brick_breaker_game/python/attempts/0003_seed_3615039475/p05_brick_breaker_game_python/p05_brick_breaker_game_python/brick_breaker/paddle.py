"""Paddle entity module for the brick breaker game.

This module defines the Paddle class which represents the player-controlled
paddle that moves horizontally to bounce the ball.
"""

from typing import Optional


class Paddle:
    """Represents a paddle in the brick breaker game.

    The paddle has position (x, y), width, and speed. It supports horizontal
    movement within specified bounds.
    """

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize a paddle with position, width, and speed.

        Args:
            x: Initial x-coordinate of the paddle center.
            y: Initial y-coordinate of the paddle center.
            width: Width of the paddle in pixels.
            speed: Movement speed in pixels per second.
        """
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed

    def move(self, direction: str, min_x: float, max_x: float, dt: float) -> None:
        """Move the paddle horizontally based on direction and time elapsed.

        Args:
            direction: Movement direction, one of 'left', 'right', or 'none'.
            min_x: Minimum x-coordinate allowed for the paddle.
            max_x: Maximum x-coordinate allowed for the paddle.
            dt: Time elapsed since last move in seconds.
        """
        # Calculate the change in x based on direction and time
        dx = 0.0
        if direction == "left":
            dx = -self.speed * dt
        elif direction == "right":
            dx = self.speed * dt
        elif direction != "none":
            raise ValueError(f"Invalid direction '{direction}', expected 'left', 'right', or 'none'")

        # Apply the movement
        self.x += dx

        # Clamp the paddle position to stay within bounds
        # The paddle's left and right edges are at x - width/2 and x + width/2 respectively
        left_edge = self.x - self.width / 2
        right_edge = self.x + self.width / 2

        if left_edge < min_x:
            # Adjust so that the left edge is at min_x
            self.x = min_x + self.width / 2
        elif right_edge > max_x:
            # Adjust so that the right edge is at max_x
            self.x = max_x - self.width / 2