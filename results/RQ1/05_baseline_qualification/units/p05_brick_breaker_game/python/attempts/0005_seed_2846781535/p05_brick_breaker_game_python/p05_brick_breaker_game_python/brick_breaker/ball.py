"""Ball entity implementation for the brick breaker game."""

class Ball:
    """Represents a ball in the brick breaker game with position, velocity, and radius."""

    def __init__(self, x: float, y: float, vx: float, vy: float, radius: float):
        """Initialize the ball with position, velocity, and radius.
        
        Args:
            x: Initial x position
            y: Initial y position
            vx: Initial x velocity
            vy: Initial y velocity
            radius: Ball radius
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius

    def step(self, dt: float) -> None:
        """Update the ball's position based on its velocity and time delta.
        
        Args:
            dt: Time delta for this step
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def bounce_x(self) -> None:
        """Reverse the horizontal velocity of the ball."""
        self.vx = -self.vx

    def bounce_y(self) -> None:
        """Reverse the vertical velocity of the ball."""
        self.vy = -self.vy