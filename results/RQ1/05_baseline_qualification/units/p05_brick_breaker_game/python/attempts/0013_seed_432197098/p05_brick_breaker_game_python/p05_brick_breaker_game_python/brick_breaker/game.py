"""Game orchestration module for the brick breaker game.

This module defines the Game class which manages the game state,
handles tick-based updates, collision detection, and game logic.
"""

from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect
import math


class Game:
    """Manages the game state and orchestration logic."""

    def __init__(self, config: GameConfig | None = None):
        """Initialize the game with a configuration.

        Args:
            config: Game configuration object. If None, uses default GameConfig.
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = 'running'
        
        # Initialize level
        self.level = make_grid_level(self.config)
        
        # Initialize paddle
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle = Paddle(paddle_x, paddle_y, self.config.paddle_width, self.config.paddle_speed)
        
        # Initialize ball
        ball_x = paddle_x
        ball_y = paddle_y - 10
        # Use a deterministic initial velocity
        ball_vx = 0.0
        ball_vy = -self.config.ball_speed
        self.ball = Ball(ball_x, ball_y, ball_vx, ball_vy, self.config.ball_radius)

    def tick(self, input_action: str) -> dict:
        """Process one game tick.

        Args:
            input_action: Player input action, one of 'left', 'right', or 'none'.

        Returns:
            A dictionary containing the current game state snapshot.

        Raises:
            ValueError: If input_action is not one of the allowed values.
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action '{input_action}'. Must be 'left', 'right', or 'none'.")
            
        # Fixed time step
        dt = 1.0 / 60.0
        
        # Apply paddle movement
        if input_action == 'left':
            self.paddle.move('left', 0, self.config.width, dt)
        elif input_action == 'right':
            self.paddle.move('right', 0, self.config.width, dt)
        elif input_action == 'none':
            self.paddle.move('none', 0, self.config.width, dt)
            
        # Update ball position
        self.ball.step(dt)
        
        # Handle collisions
        # Wall collisions
        reflect_off_walls(self.ball, self.config.width, self.config.height)
        
        # Paddle collision
        collide_ball_with_paddle(self.ball, self.paddle)
        
        # Brick collisions
        # Iterate through bricks in order and check for collisions
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
                # Handle brick hit
                remaining_durability = brick.hit()
                
                # Remove brick if destroyed
                if remaining_durability == 0:
                    # Brick is destroyed, remove it from level
                    pass  # Removal handled below
                    
                # Add points
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
                
        # Check for bottom-out (ball falls below paddle)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = 'gameover'
                
        # Update level remaining bricks count (after potential brick removal)
        bricks_remaining = self.level.remaining()
        
        # Prepare return snapshot
        snapshot = {
            'score': self.score,
            'lives': self.lives,
            'status': self.status,
            'bricks_remaining': bricks_remaining,
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
        """Reset the game state when a life is lost."""
        # Reset paddle position
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 20
        
        # Reset ball position and velocity
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed