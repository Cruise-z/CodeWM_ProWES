"""Game orchestration module for the brick breaker game.

This module contains the Game class which manages the game state,
handles tick-based updates, collision detection, and game logic.
"""

from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect
from typing import Dict, Any


class Game:
    """Main game class that orchestrates the brick breaker game."""

    def __init__(self, config: GameConfig | None = None):
        """Initialize the game with a configuration.

        Args:
            config: Game configuration. If None, uses default GameConfig().
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = 'running'
        
        # Create level
        self.level = make_grid_level(self.config)
        
        # Initialize paddle at bottom center
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle = Paddle(
            x=paddle_x,
            y=paddle_y,
            width=self.config.paddle_width,
            speed=self.config.paddle_speed
        )
        
        # Initialize ball slightly above paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 10
        # Ensure deterministic initial velocity
        ball_vx = 0.0
        ball_vy = -self.config.ball_speed
        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=ball_vx,
            vy=ball_vy,
            radius=self.config.ball_radius
        )

    def tick(self, input_action: str) -> Dict[str, Any]:
        """Process one game tick.

        Args:
            input_action: Player input action ('left', 'right', or 'none')

        Returns:
            Dictionary containing game state snapshot

        Raises:
            ValueError: If input_action is not 'left', 'right', or 'none'
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action '{input_action}'. Must be 'left', 'right', or 'none'.")
        
        # Fixed time step
        dt = 1.0 / 60.0
        
        # Apply paddle movement
        min_x = self.paddle.width / 2
        max_x = self.config.width - self.paddle.width / 2
        self.paddle.move(input_action, min_x, max_x, dt)
        
        # Update ball position
        self.ball.step(dt)
        
        # Handle wall collisions
        reflect_off_walls(self.ball, self.config.width, self.config.height)
        
        # Handle paddle collision
        collide_ball_with_paddle(self.ball, self.paddle)
        
        # Handle brick collisions
        for brick in self.level.bricks:
            if not brick.alive():
                continue
                
            collision_axis = collide_ball_with_rect(
                self.ball,
                brick.x,
                brick.y,
                brick.width,
                brick.height
            )
            
            if collision_axis is not None:
                # Process brick hit
                durability = brick.hit()
                if durability == 0:
                    # Brick broken, remove from level
                    pass  # Removal happens after iteration
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Remove broken bricks from level
        self.level.bricks = [brick for brick in self.level.bricks if brick.alive()]
        
        # Check for bottom-out (ball falls below screen)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = 'gameover'
        
        # Prepare snapshot
        snapshot = {
            'score': self.score,
            'lives': self.lives,
            'status': self.status,
            'bricks_remaining': self.level.remaining(),
            'ball': {
                'x': self.ball.x,
                'y': self.ball.y,
                'vx': self.ball.vx,
                'vy': self.ball.vy
            },
            'paddle': {
                'x': self.paddle.x,
                'y': self.paddle.y
            }
        }
        
        return snapshot

    def reset_for_life_loss(self) -> None:
        """Reset game state when a life is lost."""
        # Recenter paddle
        self.paddle.x = self.config.width / 2
        
        # Reset ball above paddle with upward velocity
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed