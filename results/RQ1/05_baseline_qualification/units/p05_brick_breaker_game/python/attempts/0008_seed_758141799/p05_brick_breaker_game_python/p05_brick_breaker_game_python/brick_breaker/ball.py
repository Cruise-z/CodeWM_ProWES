"""Ball entity for the brick breaker game."""

class Ball:
    """Represents a ball in the game with position, velocity, and radius."""

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float):
        """
        Initialize the ball with position, velocity, and radius.

        Args:
            x: Initial x coordinate.
            y: Initial y coordinate.
            vx: Initial velocity in x direction.
            vy: Initial velocity in y direction.
            radius: Radius of the ball.
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """
        Update the ball's position based on its velocity and time delta.

        Args:
            dt: Time delta in seconds.
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the horizontal velocity."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the vertical velocity."""
        self.vy = -self.vy