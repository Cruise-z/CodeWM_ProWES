"""Game orchestration module for the brick breaker game.

This module contains the Game class which manages the overall game state,
including the ball, paddle, level, score, lives, and game logic such as
tick updates, collision handling, scoring, and state transitions.
"""

from typing import Dict, Any
from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Manages the brick breaker game state and logic.

    This class orchestrates the game by updating positions, handling
    collisions, managing score and lives, and tracking game state.
    """

    def __init__(self, config: GameConfig | None = None) -> None:
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

    def tick(self, input_action: str) -> Dict[str, Any]:
        """Process one game tick.

        Updates game state based on input action and physics simulation.

        Args:
            input_action: Player input action ('left', 'right', or 'none').

        Returns:
            Dictionary containing current game state snapshot.

        Raises:
            ValueError: If input_action is not one of 'left', 'right', or 'none'.
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action '{input_action}'. Must be 'left', 'right', or 'none'.")
        
        dt = 1.0 / 60.0  # Fixed time step
        
        # Apply paddle movement
        min_x = self.paddle.width / 2
        max_x = self.config.width - self.paddle.width / 2
        self.paddle.move(input_action, min_x, max_x, dt)
        
        # Step ball
        self.ball.step(dt)
        
        # Handle wall collisions
        reflect_off_walls(self.ball, self.config.width, self.config.height)
        
        # Handle paddle collision
        collide_ball_with_paddle(self.ball, self.paddle)
        
        # Handle brick collisions
        # Iterate bricks in order and process first collision
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
                    # Remove brick from level
                    pass  # Removal handled by checking alive() in remaining()
                
                # Add points
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Check for bottom-out (ball below screen)
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = 'gameover'
        
        # Return snapshot
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
        """Reset game state for a new life.

        Recenter paddle and reset ball above paddle with upward velocity.
        Level layout remains unchanged.
        """
        # Reset paddle position
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 20
        
        # Reset ball position
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 20
        self.ball.vx = 0.0  # No horizontal velocity initially
        self.ball.vy = -self.config.ball_speed  # Upward velocity