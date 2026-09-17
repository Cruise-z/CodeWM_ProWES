"""Paddle entity implementation for the brick breaker game.

This module defines the Paddle class which represents the player's paddle,
including its position, width, speed, and movement logic.
"""

class Paddle:
    """Represents a paddle in the brick breaker game."""

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize a paddle with position, width, and speed.

        Args:
            x: Initial x-coordinate of the paddle center.
            y: Initial y-coordinate of the paddle center.
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
            direction: Movement direction ('left', 'right', or 'none').
            min_x: Minimum x-coordinate the paddle can reach.
            max_x: Maximum x-coordinate the paddle can reach.
            dt: Time delta in seconds.
        """
        # Calculate the amount to move based on direction and time
        if direction == 'left':
            delta_x = -self.speed * dt
        elif direction == 'right':
            delta_x = self.speed * dt
        elif direction == 'none':
            delta_x = 0.0
        else:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'left', 'right', or 'none'.")

        # Update the paddle's x position
        self.x += delta_x

        # Clamp the paddle within the allowed horizontal bounds
        # The paddle's left edge is at x - width/2, right edge at x + width/2
        left_edge = self.x - self.width / 2
        right_edge = self.x + self.width / 2

        if left_edge < min_x:
            # Adjust so that the left edge aligns with min_x
            self.x = min_x + self.width / 2
        elif right_edge > max_x:
            # Adjust so that the right edge aligns with max_x
            self.x = max_x - self.width / 2