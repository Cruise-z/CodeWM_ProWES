"""Game orchestration module for the brick breaker game."""

from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Orchestrates the game state and updates based on player input and physics."""

    def __init__(self, config: GameConfig | None = None) -> None:
        """Initialize the game with a configuration.
        
        Args:
            config: Game configuration; if None, uses default GameConfig()
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
        """Advance the game state by one time step.
        
        Args:
            input_action: Player input action ('left', 'right', or 'none')
            
        Returns:
            Dictionary containing current game state snapshot
        """
        if input_action not in ('left', 'right', 'none'):
            raise ValueError(f"Invalid input_action '{input_action}'; must be 'left', 'right', or 'none'")
        
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
            
            if collision_axis:
                # Brick was hit
                remaining_durability = brick.hit()
                
                # Remove brick if destroyed
                if remaining_durability == 0:
                    # In a real implementation, we'd remove the brick from the list
                    # For now, we'll just mark it as dead by setting durability to 0
                    # The remaining() method already handles this
                    pass
                
                # Increase score
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Check for bottom-out (ball falls below screen)
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
        """Reset the game state when a life is lost."""
        # Reset paddle position
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 20
        
        # Reset ball position
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = 0.0  # No horizontal velocity
        self.ball.vy = -self.config.ball_speed  # Move upward again