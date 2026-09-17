"""Game orchestration module for the brick breaker game.

This module contains the Game class which manages the game state,
orchestrates game ticks, handles collisions, scoring, and life management.
"""

from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import (
    reflect_off_walls,
    collide_ball_with_paddle,
    collide_ball_with_rect,
)


class Game:
    """Main game class that orchestrates game state and logic."""

    def __init__(self, config: GameConfig | None = None):
        """Initialize the game with optional configuration.

        Args:
            config: Game configuration. If None, uses default GameConfig().
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = "running"
        
        # Create level
        self.level = make_grid_level(self.config)
        
        # Position paddle at bottom center
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle = Paddle(
            x=paddle_x,
            y=paddle_y,
            width=self.config.paddle_width,
            speed=self.config.paddle_speed,
        )
        
        # Position ball slightly above paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 10
        # Initial velocity: upward with some horizontal component
        ball_vx = 0.0
        ball_vy = -self.config.ball_speed
        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=ball_vx,
            vy=ball_vy,
            radius=self.config.ball_radius,
        )

    def tick(self, input_action: str) -> dict:
        """Process one game tick.

        Args:
            input_action: Player input action ('left', 'right', or 'none').

        Returns:
            Dictionary containing current game state snapshot.

        Raises:
            ValueError: If input_action is not one of 'left', 'right', or 'none'.
        """
        # Validate input
        if input_action not in ("left", "right", "none"):
            raise ValueError(f"Invalid input_action '{input_action}'. Must be 'left', 'right', or 'none'.")

        # Fixed time step (60 FPS)
        dt = 1.0 / 60.0

        # Apply paddle movement
        min_x = self.config.ball_radius
        max_x = self.config.width - self.config.ball_radius
        self.paddle.move(input_action, min_x, max_x, dt)

        # Update ball position
        self.ball.step(dt)

        # Handle wall reflections
        reflect_off_walls(self.ball, self.config.width, self.config.height)

        # Check paddle collision
        collide_ball_with_paddle(self.ball, self.paddle)

        # Check brick collisions
        # Iterate through bricks in order and handle first collision per tick
        for brick in self.level.bricks:
            if not brick.alive():
                continue
                
            collision_axis = collide_ball_with_rect(
                self.ball,
                brick.x,
                brick.y,
                brick.width,
                brick.height,
            )
            
            if collision_axis is not None:
                # Handle brick hit
                durability = brick.hit()
                if durability == 0:
                    # Brick broken, remove it from level
                    # Note: We don't actually remove from list here to avoid issues during iteration,
                    # but we'll count it as removed in the remaining() method.
                    pass
                    
                # Add points for breaking the brick
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick

        # Check for bottom-out (ball falls below paddle)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = "gameover"

        # Prepare snapshot dictionary
        snapshot = {
            "score": self.score,
            "lives": self.lives,
            "status": self.status,
            "bricks_remaining": self.level.remaining(),
            "ball": {
                "x": self.ball.x,
                "y": self.ball.y,
                "vx": self.ball.vx,
                "vy": self.ball.vy,
            },
            "paddle": {
                "x": self.paddle.x,
                "y": self.paddle.y,
            },
        }
        return snapshot

    def reset_for_life_loss(self) -> None:
        """Reset game state for a new life.

        This resets the paddle position and ball position while keeping
        the level layout unchanged.
        """
        # Reset paddle position
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle.x = paddle_x
        self.paddle.y = paddle_y

        # Reset ball position
        ball_x = paddle_x
        ball_y = paddle_y - 10
        ball_vx = 0.0
        ball_vy = -self.config.ball_speed
        self.ball.x = ball_x
        self.ball.y = ball_y
        self.ball.vx = ball_vx
        self.ball.vy = ball_vy