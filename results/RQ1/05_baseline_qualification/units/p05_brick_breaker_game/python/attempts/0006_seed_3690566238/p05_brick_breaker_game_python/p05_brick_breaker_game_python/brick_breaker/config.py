"""Configuration module for the Brick Breaker game."""

from typing import Optional


class GameConfig:
    """Configuration class for the Brick Breaker game.

    This class holds all the configurable parameters for the game,
    such as dimensions, speeds, layout, scoring, and lives.
    """

    def __init__(
        self,
        width: int = 300,
        height: int = 400,
        lives: int = 3,
        ball_speed: float = 120.0,
        ball_radius: float = 4.0,
        paddle_width: float = 60.0,
        paddle_speed: float = 180.0,
        brick_rows: int = 3,
        brick_cols: int = 5,
        brick_width: Optional[float] = None,
        brick_height: float = 14.0,
        brick_padding: float = 2.0,
        top_margin: float = 40.0,
        points_per_brick: int = 100,
    ):
        """Initialize the game configuration with default values.

        Args:
            width: The width of the game window.
            height: The height of the game window.
            lives: The number of lives the player starts with.
            ball_speed: The speed of the ball in pixels per second.
            ball_radius: The radius of the ball.
            paddle_width: The width of the paddle.
            paddle_speed: The speed of the paddle in pixels per second.
            brick_rows: The number of rows of bricks.
            brick_cols: The number of columns of bricks.
            brick_width: The width of each brick. If None, it's calculated from
                width, brick_cols, and brick_padding.
            brick_height: The height of each brick.
            brick_padding: The spacing between bricks.
            top_margin: The vertical distance from the top of the window to
                the first row of bricks.
            points_per_brick: Points awarded for breaking a brick.
        """
        self.width = width
        self.height = height
        self.lives = lives
        self.ball_speed = ball_speed
        self.ball_radius = ball_radius
        self.paddle_width = paddle_width
        self.paddle_speed = paddle_speed
        self.brick_rows = brick_rows
        self.brick_cols = brick_cols
        self.brick_width = (
            brick_width if brick_width is not None else self._calculate_brick_width()
        )
        self.brick_height = brick_height
        self.brick_padding = brick_padding
        self.top_margin = top_margin
        self.points_per_brick = points_per_brick

    def _calculate_brick_width(self) -> float:
        """Calculate the brick width based on screen width, columns, and padding.

        Returns:
            The calculated brick width.
        """
        total_padding = self.brick_padding * (self.brick_cols - 1)
        available_width = self.width - total_padding
        return available_width / self.brick_cols