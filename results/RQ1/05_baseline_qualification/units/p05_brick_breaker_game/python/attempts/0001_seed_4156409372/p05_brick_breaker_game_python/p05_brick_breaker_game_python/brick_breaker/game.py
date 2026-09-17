"""Game orchestration module for the brick breaker game.

This module contains the Game class which manages the game state,
orchestrates game ticks, handles collisions, and updates scores and lives.
"""

from typing import Dict, Optional
from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Main game class that manages game state and orchestration."""

    def __init__(self, config: Optional[GameConfig] = None):
        """Initialize the game with a configuration.

        Args:
            config: GameConfig object. If None, a default config is used.
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = 'running'
        
        # Create level
        self.level = make_grid_level(self.config)
        
        # Position paddle at bottom center
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 50
        self.paddle = Paddle(
            x=paddle_x,
            y=paddle_y,
            width=self.config.paddle_width,
            speed=self.config.paddle_speed
        )
        
        # Position ball slightly above paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 20
        ball_vx = 0.0  # Start with no horizontal velocity
        ball_vy = -self.config.ball_speed  # Move upward initially
        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=ball_vx,
            vy=ball_vy,
            radius=self.config.ball_radius
        )

    def tick(self, input_action: str) -> Dict:
        """Process one game tick.

        Args:
            input_action: One of {'left', 'right', 'none'} indicating paddle movement.

        Returns:
            Dictionary containing current game state snapshot.

        Raises:
            ValueError: If input_action is not one of the valid options.
        """
        if input_action not in {'left', 'right', 'none'}:
            raise ValueError(f"Invalid input action: {input_action}")
            
        # Fixed time step (60 FPS)
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
        
        # Check collisions with bricks
        bricks_to_remove = []
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
                remaining_durability = brick.hit()
                if remaining_durability == 0:
                    bricks_to_remove.append(brick)
                
                # Add points
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Remove destroyed bricks
        for brick in bricks_to_remove:
            self.level.bricks.remove(brick)
        
        # Check for bottom-out (ball falls below screen)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = 'gameover'
        
        # Return snapshot of current state
        return {
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

    def reset_for_life_loss(self) -> None:
        """Reset game state when a life is lost."""
        # Reset paddle position
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 50
        
        # Reset ball position above paddle
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 20
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed