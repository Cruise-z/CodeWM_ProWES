"""Configuration module for the brick breaker game.

This module defines the GameConfig class which holds all the configurable
parameters for the game such as dimensions, speeds, layout, scoring, etc.
"""

from typing import Optional


class GameConfig:
    """Configuration parameters for the brick breaker game.

    All parameters have sensible defaults and can be overridden as needed.
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
        """Initialize game configuration with default values.

        Args:
            width: Width of the game window.
            height: Height of the game window.
            lives: Number of lives the player has.
            ball_speed: Speed of the ball in pixels per second.
            ball_radius: Radius of the ball in pixels.
            paddle_width: Width of the paddle in pixels.
            paddle_speed: Speed of the paddle in pixels per second.
            brick_rows: Number of rows of bricks.
            brick_cols: Number of columns of bricks.
            brick_width: Width of each brick in pixels. If None, computed from
                width, cols, and padding.
            brick_height: Height of each brick in pixels.
            brick_padding: Space between bricks in pixels.
            top_margin: Distance from top of window to first row of bricks.
            points_per_brick: Points awarded for destroying a brick.
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
        self.brick_width = brick_width
        self.brick_height = brick_height
        self.brick_padding = brick_padding
        self.top_margin = top_margin
        self.points_per_brick = points_per_brick

        # Compute brick_width if not provided
        if self.brick_width is None:
            total_width = self.width - 2 * self.brick_padding
            self.brick_width = (
                total_width - (self.brick_cols - 1) * self.brick_padding
            ) / self.brick_cols