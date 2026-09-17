"""Paddle entity for the brick breaker game.

This module defines the Paddle class which represents the paddle in the game,
including its position, width, speed, and movement logic.
"""

class Paddle:
    """Represents a paddle in the brick breaker game.

    The paddle has a position (x, y), width, and speed.
    It can be moved horizontally within given bounds.
    """

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize a new paddle.

        Args:
            x: Initial x-coordinate of the paddle's center.
            y: Initial y-coordinate of the paddle's center.
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
            direction: Movement direction, one of 'left', 'right', or 'none'.
            min_x: Minimum x-coordinate allowed for the paddle.
            max_x: Maximum x-coordinate allowed for the paddle.
            dt: Time delta in seconds.
        """
        # Calculate the change in x based on direction and speed
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

        # Clamp the paddle's position to stay within bounds
        # The paddle's edges are at (x - width/2) and (x + width/2)
        left_edge = self.x - self.width / 2
        right_edge = self.x + self.width / 2

        # Adjust if the paddle goes too far to the left
        if left_edge < min_x:
            self.x = min_x + self.width / 2

        # Adjust if the paddle goes too far to the right
        if right_edge > max_x:
            self.x = max_x - self.width / 2