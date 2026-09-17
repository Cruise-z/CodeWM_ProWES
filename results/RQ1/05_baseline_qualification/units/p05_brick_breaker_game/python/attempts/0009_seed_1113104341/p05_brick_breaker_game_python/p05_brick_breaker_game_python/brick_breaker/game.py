"""Game orchestration module for the brick breaker game."""

from typing import Dict, List
from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Main game class that orchestrates game state and updates."""

    def __init__(self, config: GameConfig | None = None):
        """Initialize the game with a configuration."""
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
            speed=self.config.paddle_speed
        )
        
        # Position ball slightly above paddle with upward velocity
        ball_x = paddle_x
        ball_y = paddle_y - 10
        ball_vx = 0.0
        ball_vy = -self.config.ball_speed
        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=ball_vx,
            vy=ball_vy,
            radius=self.config.ball_radius
        )

    def tick(self, input_action: str) -> Dict:
        """
        Process one game tick.
        
        Args:
            input_action: Player input action ('left', 'right', or 'none')
            
        Returns:
            A dictionary snapshot of the game state
            
        Raises:
            ValueError: If input_action is not valid
        """
        if input_action not in {"left", "right", "none"}:
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
        
        # Check brick collisions
        bricks_to_remove: List[int] = []
        for i, brick in enumerate(self.level.bricks):
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
                # Apply brick hit
                remaining_durability = brick.hit()
                if remaining_durability == 0:
                    bricks_to_remove.append(i)
                
                # Add points
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Remove hit bricks
        for i in reversed(bricks_to_remove):
            del self.level.bricks[i]
        
        # Check for bottom-out
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = "gameover"
        
        # Return snapshot
        return {
            "score": self.score,
            "lives": self.lives,
            "status": self.status,
            "bricks_remaining": self.level.remaining(),
            "ball": {
                "x": self.ball.x,
                "y": self.ball.y,
                "vx": self.ball.vx,
                "vy": self.ball.vy
            },
            "paddle": {
                "x": self.paddle.x,
                "y": self.paddle.y
            }
        }

    def reset_for_life_loss(self) -> None:
        """Reset the game state for a new life."""
        # Recenter paddle
        self.paddle.x = self.config.width / 2
        
        # Reset ball above paddle with upward velocity
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = 0.0
        self.ball.vy = -self.config.ball_speed