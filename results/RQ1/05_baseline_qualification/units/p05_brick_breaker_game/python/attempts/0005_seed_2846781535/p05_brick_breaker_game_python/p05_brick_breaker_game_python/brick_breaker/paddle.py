"""Paddle entity implementation for the brick breaker game."""

class Paddle:
    """Represents a paddle in the brick breaker game with position, width, and speed."""

    def __init__(self, x: float, y: float, width: float, speed: float):
        """Initialize the paddle with position, width, and speed.
        
        Args:
            x: Initial x position
            y: Initial y position
            width: Paddle width
            speed: Paddle movement speed
        """
        self.x = x
        self.y = y
        self.width = width
        self.speed = speed

    def move(self, direction: str, min_x: float, max_x: float, dt: float) -> None:
        """Move the paddle horizontally based on direction and time delta.
        
        Args:
            direction: Movement direction ('left', 'right', or 'none')
            min_x: Minimum x position allowed
            max_x: Maximum x position allowed
            dt: Time delta for this movement
        """
        if direction == 'left':
            self.x -= self.speed * dt
        elif direction == 'right':
            self.x += self.speed * dt
        elif direction != 'none':
            raise ValueError(f"Invalid direction '{direction}'; must be 'left', 'right', or 'none'")
        
        # Clamp the paddle position within bounds
        half_width = self.width / 2
        self.x = max(min_x + half_width, min(max_x - half_width, self.x))