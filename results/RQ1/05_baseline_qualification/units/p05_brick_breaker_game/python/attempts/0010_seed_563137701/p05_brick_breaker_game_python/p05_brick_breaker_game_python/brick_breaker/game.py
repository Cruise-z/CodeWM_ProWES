"""Game orchestration module for the brick breaker game.

This module contains the Game class which manages the game state,
handles tick-based updates, collision detection, scoring, and game flow.
"""

from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Manages the game state and orchestration for the brick breaker game."""

    def __init__(self, config: GameConfig | None = None):
        """Initialize the game with a configuration.

        Args:
            config: Game configuration. If None, a default GameConfig is used.
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = 'running'
        
        # Create level
        self.level = make_grid_level(self.config)
        
        # Position paddle at bottom center
        paddle_x = self.config.width / 2
        paddle_y = self.config.height - 20
        self.paddle = Paddle(
            x=paddle_x,
            y=paddle_y,
            width=self.config.paddle_width,
            speed=self.config.paddle_speed
        )
        
        # Position ball slightly above paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 10
        ball_vx = 0.0  # Start with no horizontal velocity
        ball_vy = -self.config.ball_speed  # Move upward initially
        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=ball_vx,
            vy=ball_vy,
            radius=self.config.ball_radius
        )

    def tick(self, input_action: str) -> dict:
        """Process a single game tick.

        Args:
            input_action: Direction to move the paddle ('left', 'right', or 'none').

        Returns:
            A dictionary containing the current game state snapshot.

        Raises:
            ValueError: If input_action is not 'left', 'right', or 'none'.
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action: {input_action}")
            
        # Fixed time step for deterministic behavior
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
                # Handle brick hit
                remaining_durability = brick.hit()
                if remaining_durability == 0:
                    # Brick broken, remove it from level
                    # Note: In a real implementation, we might want to remove it from the list
                    # For now, we'll just let the alive() check handle it in remaining()
                    pass
                # Add points for breaking a brick
                self.score += self.config.points_per_brick
                # Only process the first collision per tick
                break
        
        # Check for bottom-out (ball falls below screen)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = 'gameover'
        
        # Prepare and return snapshot
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
        """Reset the game state when a life is lost."""
        # Recenter paddle
        self.paddle.x = self.config.width / 2
        
        # Reset ball above paddle with upward velocity
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed