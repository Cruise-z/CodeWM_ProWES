"""Game orchestration module for the Brick Breaker game."""

from typing import Dict, Any
from .config import GameConfig
from .level import make_grid_level, Level
from .ball import Ball
from .paddle import Paddle
from .collision import reflect_off_walls, collide_ball_with_paddle, collide_ball_with_rect


class Game:
    """Orchestrates the game state and updates based on player input."""

    def __init__(self, config: GameConfig | None = None) -> None:
        """Initialize the game with a configuration.

        Args:
            config: Game configuration. Uses default if None.
        """
        self.config = config or GameConfig()
        self.score = 0
        self.lives = self.config.lives
        self.status = "running"
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
        # Use a consistent initial vx based on config
        ball_vx = self.config.ball_speed * 0.3
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
            input_action: Player input action ('left', 'right', or 'none').

        Returns:
            A dictionary containing the game state snapshot.
        """
        if input_action not in {"left", "right", "none"}:
            raise ValueError(f"Invalid input_action: {input_action}")
        
        # Fixed time step
        dt = 1.0 / 60.0
        
        # Apply paddle movement
        min_x = self.paddle.width / 2
        max_x = self.config.width - self.paddle.width / 2
        self.paddle.move(input_action, min_x, max_x, dt)
        
        # Step ball
        self.ball.step(dt)
        
        # Reflect off walls
        reflect_off_walls(self.ball, self.config.width, self.config.height)
        
        # Check collision with paddle
        collide_ball_with_paddle(self.ball, self.paddle)
        
        # Check collision with bricks
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
                    # Remove brick from level if destroyed
                    self.level.bricks.remove(brick)
                
                # Add score
                self.score += self.config.points_per_brick
                break  # Only process first collision per tick
        
        # Check for bottom-out
        if self.ball.y - self.ball.radius > self.config.height:
            self.lives -= 1
            if self.lives > 0:
                self.reset_for_life_loss()
            else:
                self.status = "gameover"
        
        # Prepare snapshot
        snapshot = {
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
        
        return snapshot

    def reset_for_life_loss(self) -> None:
        """Reset the ball and paddle position after losing a life."""
        # Recenter paddle
        self.paddle.x = self.config.width / 2
        self.paddle.y = self.config.height - 20
        
        # Reset ball position
        self.ball.x = self.paddle.x
        self.ball.y = self.paddle.y - 10
        self.ball.vx = self.config.ball_speed * 0.3
        self.ball.vy = -self.config.ball_speed