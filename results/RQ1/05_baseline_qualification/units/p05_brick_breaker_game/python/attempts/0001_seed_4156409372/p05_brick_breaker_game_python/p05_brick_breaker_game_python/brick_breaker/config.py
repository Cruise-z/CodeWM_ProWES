"""Configuration module for the brick breaker game.

This module defines the GameConfig class which holds all game parameters
and defaults. It is the single source of truth for game settings and
does not import any other project modules.
"""

from typing import Optional


class GameConfig:
    """Game configuration parameters."""

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
            width: Game window width in pixels.
            height: Game window height in pixels.
            lives: Number of lives player has.
            ball_speed: Ball speed in pixels per second.
            ball_radius: Ball radius in pixels.
            paddle_width: Paddle width in pixels.
            paddle_speed: Paddle speed in pixels per second.
            brick_rows: Number of brick rows.
            brick_cols: Number of brick columns.
            brick_width: Brick width in pixels. If None, computed from width.
            brick_height: Brick height in pixels.
            brick_padding: Pixels between bricks.
            top_margin: Distance from top to first brick row.
            points_per_brick: Points awarded for each brick destroyed.
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