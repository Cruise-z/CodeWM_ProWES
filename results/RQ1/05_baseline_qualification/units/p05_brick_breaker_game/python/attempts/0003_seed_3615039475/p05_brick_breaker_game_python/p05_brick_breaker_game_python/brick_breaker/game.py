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
    """Main game class that orchestrates the brick breaker gameplay.

    This class manages the game state including the ball, paddle, level,
    score, lives, and game status. It handles game ticks, collision detection,
    and game state transitions.
    """

    def __init__(self, config: Optional[GameConfig] = None):
        """Initialize the game with optional configuration.

        Args:
            config: Game configuration. If None, uses default GameConfig().
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = 'running'
        
        # Create the level with bricks
        self.level = make_grid_level(self.config)
        
        # Position the paddle at the bottom center
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle = Paddle(
            x=paddle_x,
            y=paddle_y,
            width=self.config.paddle_width,
            speed=self.config.paddle_speed
        )
        
        # Position the ball slightly above the paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 20
        # Set initial velocity: moving upward with some horizontal component
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
        """Process a single game tick.

        Args:
            input_action: Player input action ('left', 'right', or 'none').

        Returns:
            Dictionary containing the current game state snapshot.

        Raises:
            ValueError: If input_action is not 'left', 'right', or 'none'.
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action '{input_action}', expected 'left', 'right', or 'none'")
        
        # Define fixed time step
        dt = 1.0 / 60.0  # 60 FPS
        
        # Apply paddle movement
        min_x = self.paddle.width / 2
        max_x = self.config.width - self.paddle.width / 2
        self.paddle.move(input_action, min_x, max_x, dt)
        
        # Step the ball
        self.ball.step(dt)
        
        # Handle wall collisions
        reflect_off_walls(self.ball, self.config.width, self.config.height)
        
        # Handle paddle collision
        collide_ball_with_paddle(self.ball, self.paddle)
        
        # Handle brick collisions
        # Iterate through bricks in order and check for collision
        for brick in self.level.bricks:
            if not brick.alive():
                continue
                
            # Check collision with this brick
            collision_axis = collide_ball_with_rect(
                self.ball,
                brick.x,
                brick.y,
                brick.width,
                brick.height
            )
            
            if collision_axis is not None:
                # Brick was hit
                remaining_durability = brick.hit()
                
                # If brick is destroyed, add points
                if remaining_durability == 0:
                    self.score += self.config.points_per_brick
                
                # Break after first collision in this tick
                break
        
        # Check for bottom-out (ball goes below screen)
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
        """Reset the game state when a life is lost.

        This resets the paddle position and ball position while keeping
        the level layout intact.
        """
        # Reset paddle position
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 20
        
        # Reset ball position above paddle with upward velocity
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 20
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed